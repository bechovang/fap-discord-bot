"""
Background scheduler for attendance checks, daily snapshots, and session keepalive.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot.notifier import send_to_all_guilds
from scraper.attendance_parser import AttendanceParser
from scraper.auth import FAPAuth
from scraper.exam_parser import ExamParser
from scraper.grade_parser import GradeParser
from scraper.parser import FAPParser, ScheduleItem

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path("data/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _parse_time(time_str: str) -> Tuple[int, int]:
    hour, minute = time_str.split(":")
    return int(hour), int(minute)


def _minutes_since_midnight(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _item_time_window(item: ScheduleItem) -> Tuple[int, int]:
    start_h, start_m = _parse_time(item.start_time)
    end_h, end_m = _parse_time(item.end_time)
    start_mins = start_h * 60 + start_m
    end_mins = end_h * 60 + end_m
    if end_mins < start_mins:
        end_mins += 24 * 60
    return start_mins, end_mins


def _is_in_attendance_window(item: ScheduleItem, now: datetime) -> bool:
    now_mins = _minutes_since_midnight(now)
    start_mins, end_mins = _item_time_window(item)
    if now_mins < start_mins and end_mins >= 24 * 60:
        now_mins += 24 * 60
    return start_mins <= now_mins <= end_mins + 30


def _minutes_until_item_end(item: ScheduleItem, now: datetime) -> int:
    now_mins = _minutes_since_midnight(now)
    start_mins, end_mins = _item_time_window(item)
    if now_mins < start_mins and end_mins >= 24 * 60:
        now_mins += 24 * 60
    return end_mins - now_mins


class FAPScheduler:
    def __init__(self, bot: discord.Client, auth: FAPAuth):
        self.bot = bot
        self.auth = auth
        self.scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
        self.schedule_parser = FAPParser()
        self.attendance_parser = AttendanceParser()
        self.grade_parser = GradeParser()
        self.exam_parser = ExamParser()

        self._notified_slots: Dict[str, str] = {}
        self._last_check_date = ""
        self._today_schedule: list[ScheduleItem] = []
        self._schedule_fetch_date = ""

    async def _send_scheduler_report(self, title: str, description: str, color: discord.Color):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        await send_to_all_guilds(self.bot, embed)

    def start(self):
        self.scheduler.add_job(
            self._check_attendance,
            IntervalTrigger(minutes=15, jitter=60),
            id="attendance_check",
            name="Attendance Check",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._daily_check,
            CronTrigger(hour=22, minute=7, jitter=120),
            id="daily_check",
            name="Daily Check",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._session_keepalive,
            IntervalTrigger(minutes=15, jitter=60),
            id="session_keepalive",
            name="Session Keepalive",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scheduler started with 3 jobs: attendance(15m), daily(22:07), keepalive(15m)")
        asyncio.create_task(self._run_startup_daily_check())

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    async def _run_startup_daily_check(self):
        await asyncio.sleep(5)
        try:
            await self._daily_check()
        except Exception as exc:
            logger.error(f"Startup daily check failed: {exc}")

    async def _get_today_schedule(self) -> list[ScheduleItem]:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self._schedule_fetch_date == today_str and self._today_schedule:
            return self._today_schedule

        html = await self.auth.fetch_schedule()
        if not html:
            return []

        items = self.schedule_parser.parse_schedule(html)
        today_items = self.schedule_parser.get_today_schedule(items)
        self._today_schedule = today_items
        self._schedule_fetch_date = today_str
        logger.info(f"Fetched today's schedule: {len(today_items)} classes")
        return today_items

    async def _check_attendance(self):
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            if today_str != self._last_check_date:
                self._notified_slots.clear()
                self._last_check_date = today_str
                self._today_schedule = []
                self._schedule_fetch_date = ""

            schedule = await self._get_today_schedule()
            if not schedule:
                return

            current_classes = [item for item in schedule if _is_in_attendance_window(item, now)]
            if not current_classes:
                return

            student_id = os.getenv("FAP_STUDENT_ID", "")
            campus = int(os.getenv("FAP_CAMPUS", "4"))
            if not student_id:
                logger.warning("FAP_STUDENT_ID not set, skipping attendance check")
                return

            any_update = False

            for cls in current_classes:
                notify_key = f"{today_str}_{cls.slot}_{cls.subject_code}"
                previously_notified = self._notified_slots.get(notify_key)
                mins_remaining = _minutes_until_item_end(cls, now)

                html = await self.auth.fetch_attendance(
                    student_id=student_id,
                    campus=campus,
                )
                if not html:
                    continue

                attendance_items = self.attendance_parser.parse_attendance(html)
                today_attendance = None
                for item in attendance_items:
                    if item.slot == cls.slot and today_str.replace("-", "/") in item.date:
                        today_attendance = item
                        break

                if not today_attendance:
                    continue

                status = today_attendance.attendance_status

                if status in ("present", "absent") and previously_notified != status:
                    emoji = "✅" if status == "present" else "❌"
                    embed = discord.Embed(
                        title=f"{emoji} Attendance Update - {cls.subject_code}",
                        color=discord.Color.green() if status == "present" else discord.Color.red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.add_field(name="Status", value=status.upper(), inline=True)
                    embed.add_field(
                        name="Slot",
                        value=f"Slot {cls.slot} ({cls.start_time} - {cls.end_time})",
                        inline=True,
                    )
                    embed.add_field(name="Room", value=cls.room or "N/A", inline=True)

                    await send_to_all_guilds(self.bot, embed)
                    self._notified_slots[notify_key] = status
                    any_update = True
                    logger.info(f"Attendance notified: {cls.subject_code} slot {cls.slot} = {status}")

                elif status == "future" and 0 < mins_remaining <= 15:
                    warning_key = f"{notify_key}_warning"
                    if previously_notified != "warning" and self._notified_slots.get(warning_key) != "warned":
                        embed = discord.Embed(
                            title=f"⚠️ Attendance Warning - {cls.subject_code}",
                            description=f"Slot {cls.slot} ends in ~{mins_remaining} minutes but attendance has not been marked.",
                            color=discord.Color.orange(),
                            timestamp=discord.utils.utcnow(),
                        )
                        embed.add_field(name="Time Left", value=f"~{mins_remaining} minutes", inline=True)
                        embed.add_field(
                            name="Slot",
                            value=f"Slot {cls.slot} ({cls.start_time} - {cls.end_time})",
                            inline=True,
                        )
                        embed.add_field(name="Room", value=cls.room or "N/A", inline=True)

                        await send_to_all_guilds(self.bot, embed)
                        self._notified_slots[notify_key] = "warning"
                        self._notified_slots[warning_key] = "warned"
                        any_update = True
                        logger.info(f"Attendance warning: {cls.subject_code} slot {cls.slot}, {mins_remaining} min left")

            if not any_update:
                subjects = ", ".join(cls.subject_code for cls in current_classes)
                await self._send_scheduler_report(
                    "ℹ️ Attendance Check",
                    f"Checked active attendance window for {subjects}. No attendance change was detected.",
                    discord.Color.blurple(),
                )

        except Exception as exc:
            logger.error(f"Attendance check failed: {exc}")
            await self._send_scheduler_report(
                "❌ Attendance Check Failed",
                f"Attendance check crashed: `{exc}`",
                discord.Color.red(),
            )

    async def _daily_check(self):
        try:
            logger.info("Starting daily check...")

            snapshot_file = SNAPSHOT_DIR / "weekly_snapshot.json"
            prev_data = {}
            if snapshot_file.exists():
                with open(snapshot_file, "r", encoding="utf-8") as file:
                    prev_data = json.load(file)

            new_data = {}
            changes = []

            student_id = os.getenv("FAP_STUDENT_ID", "")

            if student_id:
                html = await self.auth.fetch_grades(student_id=student_id)
                if html:
                    terms = self.grade_parser.extract_terms(html)
                    if terms:
                        current_term = next((term for term in terms if term.get("is_current")), terms[-1])
                        grade_html = await self.auth.fetch_grades(
                            student_id=student_id,
                            term=current_term.get("name", ""),
                        )
                        if grade_html:
                            grades = self.grade_parser.parse_grades(grade_html)
                            new_data["grades"] = [
                                {
                                    "code": grade.subject_code,
                                    "name": grade.subject_name,
                                    "total": grade.total,
                                    "status": grade.status,
                                }
                                for grade in grades
                            ]

                            prev_grades = {grade["code"]: grade for grade in prev_data.get("grades", [])}
                            for grade in new_data["grades"]:
                                prev = prev_grades.get(grade["code"])
                                if not prev:
                                    changes.append(f"🆕 New subject: **{grade['code']}** - {grade['name']}")
                                elif prev["total"] != grade["total"] and grade["total"]:
                                    changes.append(
                                        f"📝 Grade updated: **{grade['code']}** -> {grade['total']} (was {prev['total'] or 'N/A'})"
                                    )
                                elif prev["status"] != grade["status"] and grade["status"]:
                                    changes.append(f"📋 Status changed: **{grade['code']}** -> {grade['status']}")

            html = await self.auth.fetch_schedule()
            if html:
                items = self.schedule_parser.parse_schedule(html)
                self._today_schedule = self.schedule_parser.get_today_schedule(items)
                self._schedule_fetch_date = datetime.now().strftime("%Y-%m-%d")
                new_data["schedule"] = [
                    {
                        "code": item.subject_code,
                        "day": item.day,
                        "date": item.date,
                        "slot": item.slot,
                        "room": item.room,
                    }
                    for item in items
                ]

                prev_sched_map = {
                    f"{item['code']}_{item['day']}_{item['slot']}": item
                    for item in prev_data.get("schedule", [])
                }
                for item in new_data["schedule"]:
                    key = f"{item['code']}_{item['day']}_{item['slot']}"
                    if key not in prev_sched_map:
                        changes.append(f"📅 New class: **{item['code']}** on {item['day']} Slot {item['slot']} at {item['room']}")

            html = await self.auth.fetch_exam_schedule()
            if html:
                exams = self.exam_parser.parse_exam_schedule(html)
                new_data["exams"] = [
                    {
                        "subject": exam.subject_code,
                        "date": exam.date,
                        "time": exam.time,
                        "room": exam.room,
                        "exam_type": exam.exam_type,
                    }
                    for exam in exams
                ]

                prev_exams = {
                    f"{exam['subject']}_{exam['date']}": exam
                    for exam in prev_data.get("exams", [])
                }
                for exam in new_data["exams"]:
                    key = f"{exam['subject']}_{exam['date']}"
                    if key not in prev_exams:
                        changes.append(f"📝 New exam: **{exam['subject']}** on {exam['date']} {exam['time']}")
                    else:
                        for field in ("time", "room", "exam_type"):
                            if exam[field] != prev_exams[key].get(field) and exam[field]:
                                changes.append(
                                    f"Exam changed: **{exam['subject']}** {field}: {exam[field]} (was {prev_exams[key].get(field, 'N/A')})"
                                )

            with open(snapshot_file, "w", encoding="utf-8") as file:
                json.dump(new_data, file, indent=2, ensure_ascii=False)

            if changes:
                embed = discord.Embed(
                    title="📋 Daily Update",
                    description=f"Found **{len(changes)}** change(s):",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow(),
                )
                change_text = "\n".join(changes[:20])
                if len(change_text) > 1024:
                    change_text = change_text[:1020] + "..."
                embed.add_field(name="Changes", value=change_text, inline=False)

                await send_to_all_guilds(self.bot, embed)
                logger.info(f"Daily check: {len(changes)} changes notified")
            else:
                logger.info("Daily check: no changes detected")
                await self._send_scheduler_report(
                    "ℹ️ Daily Check",
                    "Daily check completed. No schedule, grade, or exam changes were detected.",
                    discord.Color.blurple(),
                )

        except Exception as exc:
            logger.error(f"Daily check failed: {exc}")
            await self._send_scheduler_report(
                "❌ Daily Check Failed",
                f"Daily check crashed: `{exc}`",
                discord.Color.red(),
            )

    async def _session_keepalive(self):
        try:
            session = await self.auth.get_session(force_refresh=False, fast_check=False)
            if session:
                logger.debug("Session keepalive: session is valid")
            else:
                logger.warning("Session keepalive: session check failed and refresh did not recover it")
        except Exception as exc:
            logger.error(f"Session keepalive failed: {exc}")
            await self._send_scheduler_report(
                "❌ Session Keepalive Failed",
                f"Session keepalive crashed: `{exc}`",
                discord.Color.red(),
            )

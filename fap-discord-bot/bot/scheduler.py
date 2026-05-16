"""
Background Scheduler for FAP Discord Bot
Handles automatic attendance checks, weekly reports, and session keepalive
"""
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import discord

from scraper.auth import FAPAuth
from scraper.parser import FAPParser, ScheduleItem
from scraper.attendance_parser import AttendanceParser, AttendanceItem
from scraper.grade_parser import GradeParser
from scraper.exam_parser import ExamParser
from bot.notifier import send_to_all_guilds, get_channel_id, _load_channels

logger = logging.getLogger(__name__)

SLOT_TIMES = {
    1: ("7:00", "9:15"),
    2: ("9:30", "11:45"),
    3: ("12:30", "14:45"),
    4: ("15:00", "17:15"),
    5: ("17:30", "19:45"),
    6: ("19:45", "22:00"),
    7: ("22:00", "00:00"),
    8: ("00:00", "7:00"),
}

SNAPSHOT_DIR = Path("data/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _parse_time(time_str: str) -> Tuple[int, int]:
    h, m = time_str.split(":")
    return int(h), int(m)


def _get_current_slot() -> Optional[int]:
    now = datetime.now()
    now_mins = now.hour * 60 + now.minute

    for slot_num, (start_str, end_str) in SLOT_TIMES.items():
        sh, sm = _parse_time(start_str)
        eh, em = _parse_time(end_str)
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em

        if slot_num == 7:
            if now_mins >= start_mins or now_mins < end_mins:
                return slot_num
        elif slot_num == 8:
            if now_mins >= start_mins or now_mins < end_mins:
                return slot_num
        else:
            if start_mins <= now_mins < end_mins:
                return slot_num

    return None


def _minutes_until_slot_end(slot_num: int) -> Optional[int]:
    if slot_num not in SLOT_TIMES:
        return None
    _, end_str = SLOT_TIMES[slot_num]
    eh, em = _parse_time(end_str)
    now = datetime.now()
    end_mins = eh * 60 + em
    now_mins = now.hour * 60 + now.minute

    remaining = end_mins - now_mins
    if remaining < 0 and slot_num >= 7:
        remaining += 24 * 60
    return remaining


class FAPScheduler:
    def __init__(self, bot: discord.Client, auth: FAPAuth):
        self.bot = bot
        self.auth = auth
        self.scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
        self.schedule_parser = FAPParser()
        self.attendance_parser = AttendanceParser()
        self.grade_parser = GradeParser()
        self.exam_parser = ExamParser()

        # Track which slots we've already notified about today
        # key: f"{date}_{slot}_{subject}" → value: status notified
        self._notified_slots: Dict[str, str] = {}
        self._last_check_date: str = ""

        # Track today's schedule cache
        self._today_schedule: list = []
        self._schedule_fetch_date: str = ""

    async def _send_scheduler_report(self, title: str, description: str, color: discord.Color):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        await send_to_all_guilds(self.bot, embed)

    def start(self):
        # Attendance check every 15 minutes during day
        self.scheduler.add_job(
            self._check_attendance,
            IntervalTrigger(minutes=15, jitter=60),
            id="attendance_check",
            name="Attendance Check",
            replace_existing=True,
        )

        # Daily check every day at 22:00
        self.scheduler.add_job(
            self._weekly_check,
            CronTrigger(hour=22, minute=7, jitter=120),
            id="daily_check",
            name="Daily Check",
            replace_existing=True,
        )

        # Session keepalive every 15 minutes so transient proxy recovery
        # can trigger a re-login quickly without waiting for user commands.
        self.scheduler.add_job(
            self._session_keepalive,
            IntervalTrigger(minutes=15, jitter=60),
            id="session_keepalive",
            name="Session Keepalive",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scheduler started with 3 jobs: attendance(15m), weekly(sun 22:00), keepalive(15m)")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    async def _get_today_schedule(self) -> list:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self._schedule_fetch_date == today_str and self._today_schedule:
            return self._today_schedule

        html = await self.auth.fetch_schedule()
        if html:
            items = self.schedule_parser.parse_schedule(html)
            today_items = self.schedule_parser.get_today_schedule(items)
            self._today_schedule = today_items
            self._schedule_fetch_date = today_str
            logger.info(f"Fetched today's schedule: {len(today_items)} classes")
            return today_items
        return []

    async def _check_attendance(self):
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # Reset notified slots on new day
            if today_str != self._last_check_date:
                self._notified_slots.clear()
                self._last_check_date = today_str
                self._today_schedule = []
                self._schedule_fetch_date = ""

            current_slot = _get_current_slot()
            if not current_slot:
                await self._send_scheduler_report(
                    "ℹ️ Attendance Check",
                    "No active class slot right now. Attendance check completed with no changes.",
                    discord.Color.blurple(),
                )
                return

            schedule = await self._get_today_schedule()
            if not schedule:
                await self._send_scheduler_report(
                    "⚠️ Attendance Check",
                    "Could not load today's schedule, or there are no classes today.",
                    discord.Color.orange(),
                )
                return

            # Filter schedule items for current slot
            current_classes = [s for s in schedule if s.slot == current_slot]
            if not current_classes:
                await self._send_scheduler_report(
                    "ℹ️ Attendance Check",
                    f"Checked slot {current_slot}. No class is scheduled in this slot.",
                    discord.Color.blurple(),
                )
                return

            student_id = os.getenv("FAP_STUDENT_ID", "")
            campus = int(os.getenv("FAP_CAMPUS", "4"))
            if not student_id:
                logger.warning("FAP_STUDENT_ID not set, skipping attendance check")
                await self._send_scheduler_report(
                    "⚠️ Attendance Check",
                    "Skipped attendance check because `FAP_STUDENT_ID` is not configured.",
                    discord.Color.orange(),
                )
                return

            mins_remaining = _minutes_until_slot_end(current_slot)
            any_update = False

            for cls in current_classes:
                notify_key = f"{today_str}_{current_slot}_{cls.subject_code}"
                previously_notified = self._notified_slots.get(notify_key)

                # Fetch attendance for this course
                html = await self.auth.fetch_attendance(
                    student_id=student_id,
                    campus=campus,
                )
                if not html:
                    continue

                # Find the attendance record for today's slot
                items = self.attendance_parser.parse_attendance(html)
                today_attendance = None
                for item in items:
                    if item.slot == current_slot and today_str.replace("-", "/") in item.date:
                        today_attendance = item
                        break

                if not today_attendance:
                    continue

                status = today_attendance.attendance_status

                # Case 1: Teacher has marked attendance (present or absent)
                if status in ("present", "absent") and previously_notified != status:
                    emoji = "✅" if status == "present" else "❌"
                    embed = discord.Embed(
                        title=f"{emoji} Attendance Update - {cls.subject_code}",
                        color=discord.Color.green() if status == "present" else discord.Color.red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.add_field(name="Status", value=status.upper(), inline=True)
                    embed.add_field(name="Slot", value=f"Slot {current_slot} ({cls.start_time} - {cls.end_time})", inline=True)
                    embed.add_field(name="Room", value=cls.room or "N/A", inline=True)

                    await send_to_all_guilds(self.bot, embed)
                    self._notified_slots[notify_key] = status
                    any_update = True
                    logger.info(f"Attendance notified: {cls.subject_code} slot {current_slot} = {status}")

                # Case 2: 15 minutes before class ends, still not marked
                elif status == "future" and mins_remaining is not None and 0 < mins_remaining <= 15:
                    warning_key = f"{notify_key}_warning"
                    if previously_notified != "warning" and self._notified_slots.get(warning_key) != "warned":
                        embed = discord.Embed(
                            title=f"⚠️ Attendance Warning - {cls.subject_code}",
                            description=f"Slot {current_slot} ends in ~{mins_remaining} minutes but attendance hasn't been marked!",
                            color=discord.Color.orange(),
                            timestamp=discord.utils.utcnow(),
                        )
                        embed.add_field(name="Time Left", value=f"~{mins_remaining} minutes", inline=True)
                        embed.add_field(name="Slot", value=f"Slot {current_slot} ({cls.start_time} - {cls.end_time})", inline=True)
                        embed.add_field(name="Room", value=cls.room or "N/A", inline=True)

                        await send_to_all_guilds(self.bot, embed)
                        self._notified_slots[notify_key] = "warning"
                        self._notified_slots[warning_key] = "warned"
                        any_update = True
                        logger.info(f"Attendance warning: {cls.subject_code} slot {current_slot}, {mins_remaining} min left")

            if not any_update:
                subjects = ", ".join(cls.subject_code for cls in current_classes)
                await self._send_scheduler_report(
                    "ℹ️ Attendance Check",
                    f"Checked slot {current_slot} for {subjects}. No attendance change was detected.",
                    discord.Color.blurple(),
                )

        except Exception as e:
            logger.error(f"Attendance check failed: {e}")
            await self._send_scheduler_report(
                "❌ Attendance Check Failed",
                f"Attendance check crashed: `{e}`",
                discord.Color.red(),
            )

    async def _weekly_check(self):
        try:
            logger.info("Starting weekly check...")

            # Load previous snapshot
            snapshot_file = SNAPSHOT_DIR / "weekly_snapshot.json"
            prev_data = {}
            if snapshot_file.exists():
                with open(snapshot_file, "r", encoding="utf-8") as f:
                    prev_data = json.load(f)

            new_data = {}
            changes = []

            student_id = os.getenv("FAP_STUDENT_ID", "")
            campus = int(os.getenv("FAP_CAMPUS", "4"))

            # Check grades
            if student_id:
                html = await self.auth.fetch_grades(student_id=student_id)
                if html:
                    terms = self.grade_parser.extract_terms(html)
                    if terms:
                        current_term = next((t for t in terms if t.get("is_current")), terms[-1] if terms else None)
                        if current_term:
                            grade_html = await self.auth.fetch_grades(
                                student_id=student_id,
                                term=current_term.get("name", ""),
                            )
                            if grade_html:
                                grades = self.grade_parser.parse_grades(grade_html)
                                new_data["grades"] = [
                                    {
                                        "code": g.subject_code,
                                        "name": g.subject_name,
                                        "total": g.total,
                                        "status": g.status,
                                    }
                                    for g in grades
                                ]

                                prev_grades = {g["code"]: g for g in prev_data.get("grades", [])}
                                for g in new_data["grades"]:
                                    prev = prev_grades.get(g["code"])
                                    if not prev:
                                        changes.append(f"🆕 New subject: **{g['code']}** - {g['name']}")
                                    elif prev["total"] != g["total"] and g["total"]:
                                        changes.append(f"📝 Grade updated: **{g['code']}** → {g['total']} (was {prev['total'] or 'N/A'})")
                                    elif prev["status"] != g["status"] and g["status"]:
                                        changes.append(f"📋 Status changed: **{g['code']}** → {g['status']}")

            # Check schedule (next week)
            html = await self.auth.fetch_schedule()
            if html:
                items = self.schedule_parser.parse_schedule(html)
                new_data["schedule"] = [
                    {
                        "code": s.subject_code,
                        "day": s.day,
                        "date": s.date,
                        "slot": s.slot,
                        "room": s.room,
                    }
                    for s in items
                ]

                prev_sched_map = {
                    f"{s['code']}_{s['day']}_{s['slot']}": s
                    for s in prev_data.get("schedule", [])
                }
                for s in new_data["schedule"]:
                    key = f"{s['code']}_{s['day']}_{s['slot']}"
                    if key not in prev_sched_map:
                        changes.append(f"📅 New class: **{s['code']}** on {s['day']} Slot {s['slot']} at {s['room']}")

            # Check exam schedule
            html = await self.auth.fetch_exam_schedule()
            if html:
                exams = self.exam_parser.parse_exam_schedule(html)
                new_data["exams"] = [
                    {
                        "subject": e.subject_code,
                        "date": e.date,
                        "time": e.time,
                        "room": e.room,
                        "exam_type": e.exam_type,
                    }
                    for e in exams
                ]

                prev_exams = {
                    f"{e['subject']}_{e['date']}": e
                    for e in prev_data.get("exams", [])
                }
                for e in new_data["exams"]:
                    key = f"{e['subject']}_{e['date']}"
                    if key not in prev_exams:
                        changes.append(f"📝 New exam: **{e['subject']}** on {e['date']} {e['time']}")
                    else:
                        for field in ("time", "room", "exam_type"):
                            if e[field] != prev_exams[key].get(field) and e[field]:
                                changes.append(f"Exam changed: **{e['subject']}** {field}: {e[field]} (was {prev_exams[key].get(field, 'N/A')})")

            # Save snapshot
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)

            # Send notification if there are changes
            if changes:
                embed = discord.Embed(
                    title="📋 Weekly Update",
                    description=f"Found **{len(changes)}** change(s) this week:",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow(),
                )

                # Split changes into chunks if too many
                change_text = "\n".join(changes[:20])
                if len(change_text) > 1024:
                    change_text = change_text[:1020] + "..."
                embed.add_field(name="Changes", value=change_text, inline=False)

                await send_to_all_guilds(self.bot, embed)
                logger.info(f"Weekly check: {len(changes)} changes notified")
            else:
                logger.info("Weekly check: no changes detected")
                await self._send_scheduler_report(
                    "ℹ️ Daily Check",
                    "Daily check completed. No schedule, grade, or exam changes were detected.",
                    discord.Color.blurple(),
                )

        except Exception as e:
            logger.error(f"Weekly check failed: {e}")
            await self._send_scheduler_report(
                "❌ Daily Check Failed",
                f"Daily check crashed: `{e}`",
                discord.Color.red(),
            )

    async def _session_keepalive(self):
        try:
            session = await self.auth.get_session(force_refresh=False, fast_check=False)
            if session:
                logger.debug("Session keepalive: session is valid")
            else:
                logger.warning("Session keepalive: session check failed and refresh did not recover it")
        except Exception as e:
            logger.error(f"Session keepalive failed: {e}")
            await self._send_scheduler_report(
                "❌ Session Keepalive Failed",
                f"Session keepalive crashed: `{e}`",
                discord.Color.red(),
            )

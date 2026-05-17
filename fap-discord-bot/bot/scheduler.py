"""
Background scheduler for attendance checks and daily snapshots.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot.notifier import send_to_all_guilds
from bot.html_report import render_daily_report
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

        self.scheduler.start()
        logger.info("Scheduler started with 2 jobs: attendance(15m), daily(22:07)")
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
        logger.info("Starting daily check...")

        snapshot_file = SNAPSHOT_DIR / "weekly_snapshot.json"
        prev_data = {}
        if snapshot_file.exists():
            try:
                with open(snapshot_file, "r", encoding="utf-8") as file:
                    prev_data = json.load(file)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load previous snapshot, starting fresh")

        new_data = {}
        changes = []
        errors = []
        student_id = os.getenv("FAP_STUDENT_ID", "")
        new_data["student_id"] = student_id

        # --- Grades ---
        try:
            if student_id:
                html = await self.auth.fetch_grades(student_id=student_id)
                if html:
                    terms = self.grade_parser.extract_terms(html)
                    current_term = next((t for t in terms if t.get("is_current")), terms[-1] if terms else None)
                    courses = self.grade_parser.extract_courses(html)

                    if courses and current_term:
                        all_grades = []
                        for course in courses:
                            if course.get("course_id"):
                                course_html = await self.auth.fetch_grades(
                                    student_id=student_id,
                                    course=course["course_id"],
                                )
                                if course_html:
                                    expected_code = course["code"] if course["code"] else None
                                    course_grades = self.grade_parser.parse_grades(course_html, expected_subject_code=expected_code)
                                    for g in course_grades:
                                        if not g.subject_code:
                                            g.subject_code = course["code"]
                                        if not g.subject_name or g.subject_name == g.subject_code:
                                            g.subject_name = course["name"].split("(")[0].strip()
                                    all_grades.extend(course_grades)

                        new_data["grades"] = [
                            {
                                "code": g.subject_code,
                                "name": g.subject_name,
                                "credits": g.credits,
                                "midterm": g.mid_term,
                                "final": g.final,
                                "total": g.total,
                                "status": g.status,
                            }
                            for g in all_grades
                        ]

                        gpa = self.grade_parser.calculate_gpa(all_grades, {current_term["name"]: all_grades} if current_term else None)
                        if gpa:
                            new_data["gpa_summary"] = {
                                "term_gpa": round(gpa.term_gpa or 0, 2),
                                "cumulative_gpa": round(gpa.cumulative_gpa, 2),
                                "total_credits": gpa.total_credits,
                                "earned_credits": gpa.earned_credits,
                                "subjects_passed": gpa.subjects_passed,
                                "subjects_failed": gpa.subjects_failed,
                            }

                        prev_grades = {g["code"]: g for g in prev_data.get("grades", [])}
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
        except Exception as exc:
            logger.error(f"Daily check grades failed: {exc}")
            errors.append(f"Grades: {exc}")

        # --- Schedule ---
        try:
            html = await self.auth.fetch_schedule()
            if html:
                items = self.schedule_parser.parse_schedule(html)
                self._today_schedule = self.schedule_parser.get_today_schedule(items)
                self._schedule_fetch_date = datetime.now().strftime("%Y-%m-%d")
                new_data["schedule"] = [
                    {
                        "code": item.subject_code,
                        "name": item.subject_name,
                        "day": item.day,
                        "date": item.date,
                        "slot": item.slot,
                        "room": item.room,
                        "start_time": item.start_time,
                        "end_time": item.end_time,
                        "instructor": item.instructor,
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
        except Exception as exc:
            logger.error(f"Daily check schedule failed: {exc}")
            errors.append(f"Schedule: {exc}")

        # --- Exams ---
        try:
            html = await self.auth.fetch_exam_schedule()
            if html:
                exams = self.exam_parser.parse_exam_schedule(html)
                new_data["exams"] = [
                    {
                        "subject": exam.subject_code,
                        "subject_name": exam.subject_name,
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
        except Exception as exc:
            logger.error(f"Daily check exams failed: {exc}")
            errors.append(f"Exams: {exc}")

        # --- Attendance ---
        try:
            campus = int(os.getenv("FAP_CAMPUS", "4"))
            html = await self.auth.fetch_attendance(student_id=student_id, campus=campus)
            if html:
                att_parser = AttendanceParser()
                courses = att_parser.extract_courses(html)

                if courses:
                    all_att = []
                    for course in courses:
                        if course.get("is_current"):
                            items = att_parser.parse_attendance(html)
                            for item in items:
                                item.subject_code = course["code"]
                                item.subject_name = course["name"]
                            all_att.extend(items)
                        elif course.get("course_id"):
                            course_html = await self.auth.fetch_attendance(
                                student_id=student_id,
                                campus=campus,
                                course=course["course_id"],
                            )
                            if course_html:
                                items = att_parser.parse_attendance(course_html)
                                for item in items:
                                    item.subject_code = course["code"]
                                    item.subject_name = course["name"]
                                all_att.extend(items)

                    new_data["attendance"] = [
                        {
                            "code": a.subject_code,
                            "name": a.subject_name,
                            "date": a.date,
                            "slot": a.slot,
                            "room": a.room,
                            "status": a.attendance_status,
                        }
                        for a in all_att
                    ]
        except Exception as exc:
            logger.error(f"Daily check attendance failed: {exc}")
            errors.append(f"Attendance: {exc}")

        # --- Preserve old data for sections that failed to fetch ---
        stale_sections = []
        for key in ("grades", "gpa_summary", "schedule", "exams", "attendance"):
            if key not in new_data and key in prev_data:
                new_data[key] = prev_data[key]
                stale_sections.append(key)

        if stale_sections:
            logger.warning(f"Using stale data for: {', '.join(stale_sections)}")

        # Track last successful fetch time per section
        last_fetch = prev_data.get("_last_fetch", {})
        now_iso = datetime.now().isoformat(timespec="minutes")
        for key in ("grades", "schedule", "exams", "attendance"):
            if key in new_data and key not in stale_sections:
                last_fetch[key] = now_iso
        new_data["_last_fetch"] = last_fetch
        new_data["_stale"] = stale_sections

        # --- Save snapshot ---
        try:
            with open(snapshot_file, "w", encoding="utf-8") as file:
                json.dump(new_data, file, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Daily check snapshot save failed: {exc}")
            errors.append(f"Snapshot save: {exc}")

        # --- Render HTML dashboard ---
        try:
            report_dir = Path("data")
            report_dir.mkdir(parents=True, exist_ok=True)
            html = render_daily_report(new_data)
            (report_dir / "daily_report.html").write_text(html, encoding="utf-8")
            logger.info("Daily report HTML rendered")
        except Exception as exc:
            logger.error(f"Daily report HTML render failed: {exc}")

        # --- Report ---
        dashboard_url = os.getenv("DASHBOARD_URL", "")
        embed = None

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
            if errors:
                embed.add_field(name="Errors", value="\n".join(errors[:5]), inline=False)
            await send_to_all_guilds(self.bot, embed)
            logger.info(f"Daily check: {len(changes)} changes notified")
        elif errors:
            await self._send_scheduler_report(
                "⚠️ Daily Check Partial Failure",
                "Daily check completed with errors:\n" + "\n".join(errors[:5]),
                discord.Color.orange(),
            )
        else:
            logger.info("Daily check: no changes detected")
            await self._send_scheduler_report(
                "ℹ️ Daily Check",
                "Daily check completed. No schedule, grade, or exam changes were detected.",
                discord.Color.blurple(),
            )

        if dashboard_url:
            dash_embed = discord.Embed(
                description=f"📊 [Xem dashboard]({dashboard_url})",
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow(),
            )
            await send_to_all_guilds(self.bot, dash_embed)

    def schedule_session_recovery(self, delay_minutes: int):
        """Schedule a one-off session recovery attempt after backoff cooldown."""
        job_id = "session_recovery"
        existing = self.scheduler.get_job(job_id)
        if existing:
            logger.info("Session recovery already scheduled, skipping")
            return

        self.scheduler.add_job(
            self._session_recovery,
            trigger=DateTrigger(run_date=datetime.now() + timedelta(minutes=delay_minutes)),
            id=job_id,
            name="Session Recovery",
            replace_existing=True,
        )
        logger.info(f"Session recovery scheduled in ~{delay_minutes} minutes")

    async def _session_recovery(self):
        """One-off attempt to recover the FAP session after backoff."""
        try:
            session = await self.auth.get_session(force_refresh=True, fast_check=False)
            if session:
                await self._send_scheduler_report(
                    "✅ Session Recovered",
                    "FAP session đã khôi phục thành công. Bạn có thể dùng lệnh bình thường lại.",
                    discord.Color.green(),
                )
            else:
                failures = self.auth._consecutive_refresh_failures
                remaining = self.auth.get_backoff_remaining_minutes()
                logger.warning(
                    f"Session recovery failed (failures: {failures}, next retry in ~{remaining}m)"
                )
                if remaining > 0:
                    self.schedule_session_recovery(remaining)
        except Exception as exc:
            logger.error(f"Session recovery failed: {exc}")

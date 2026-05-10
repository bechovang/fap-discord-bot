"""
Discord Bot Commands - Pending Checks
Commands for viewing pending items (grades waiting, applications, attendance, etc.)
"""
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View
from typing import Optional, List
import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.auth import FAPAuth
from scraper.exam_parser import ExamParser
from scraper.grade_parser import GradeParser
from scraper.application_parser import ApplicationParser
from scraper.attendance_parser import AttendanceParser
from scraper.parser import FAPParser

logger = logging.getLogger(__name__)


class PendingChecksCommands(commands.Cog, name="pending"):
    """Pending checks viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth: Optional[FAPAuth] = None
        self.exam_parser = ExamParser()
        self.grade_parser = GradeParser()
        self.app_parser = ApplicationParser()
        self.attendance_parser = AttendanceParser()
        self.schedule_parser = FAPParser()
        self.student_id = os.getenv('FAP_STUDENT_ID', '')
        self.campus = int(os.getenv('FAP_CAMPUS', '4'))

    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        pass

    async def _get_auth(self) -> FAPAuth:
        """Get or create auth instance"""
        if self.auth is None:
            from dotenv import load_dotenv
            load_dotenv()

            self.auth = FAPAuth(
                username=os.getenv('FAP_USERNAME', ''),
                password=os.getenv('FAP_PASSWORD', ''),
                headless=os.getenv('HEADLESS', 'true').lower() == 'true',
                user_agent=os.getenv('USER_AGENT')
            )
        return self.auth

    def _parse_exam_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse exam date and time into datetime object"""
        try:
            day, month, year = map(int, date_str.split('/'))
            import re
            time_match = re.search(r'(\d+)h', time_str)
            if time_match:
                hour = int(time_match.group(1))
                return datetime(year, month, day, hour)
            else:
                return datetime(year, month, day)
        except (ValueError, AttributeError):
            return None

    @app_commands.command(name="checks", description="View all pending checks (grades, applications, attendance, etc.)")
    @app_commands.describe(
        show_all="Show all items including completed ones (default: only pending)"
    )
    async def pending_checks(self, interaction: discord.Interaction, show_all: bool = False):
        """Show comprehensive summary of all pending items"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()

            # Create main embed
            embed = discord.Embed(
                title="⏳ Pending Checks Dashboard",
                description="Items being monitored for updates",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            # 1. Check for grades waiting
            waiting_for_grades = await self._check_waiting_grades(auth)
            if waiting_for_grades:
                grade_lines = []
                for item in waiting_for_grades[:5]:
                    days = item['days_since']
                    emoji = "🟢" if days <= 3 else "🟡" if days <= 7 else "🟠" if days <= 14 else "🔴"
                    grade_lines.append(f"{emoji} **{item['subject_code']}** - {item['days_since']} days")
                if len(waiting_for_grades) > 5:
                    grade_lines.append(f"_...and {len(waiting_for_grades) - 5} more_")
                embed.add_field(
                    name=f"📊 Waiting for Grades ({len(waiting_for_grades)})",
                    value="\n".join(grade_lines),
                    inline=False
                )
            elif show_all:
                embed.add_field(
                    name="📊 Waiting for Grades",
                    value="✅ No pending grades - all exams graded!",
                    inline=False
                )

            # 2. Check for pending applications
            pending_apps = await self._check_pending_applications(auth)
            if pending_apps:
                app_lines = []
                for app in pending_apps[:5]:
                    # Truncate purpose
                    purpose = app['purpose'][:40] + "..." if len(app['purpose']) > 40 else app['purpose']
                    app_lines.append(f"⏳ **{app['type']}**\n   📝 {purpose}\n   📅 {app['created']}")
                if len(pending_apps) > 5:
                    app_lines.append(f"_...and {len(pending_apps) - 5} more_")
                embed.add_field(
                    name=f"📋 Pending Applications ({len(pending_apps)})",
                    value="\n".join(app_lines),
                    inline=False
                )
            elif show_all:
                embed.add_field(
                    name="📋 Pending Applications",
                    value="✅ No pending applications",
                    inline=False
                )

            # 3. Check for attendance not marked today
            unmarked_attendance = await self._check_unmarked_attendance(auth)
            if unmarked_attendance:
                attend_lines = []
                for item in unmarked_attendance[:5]:
                    slot_info = f"Slot {item['slot']}" if item['slot'] else ""
                    attend_lines.append(f"⏳ **{item['subject_code']}**\n   📅 {item['date']} | {slot_info}")
                if len(unmarked_attendance) > 5:
                    attend_lines.append(f"_...and {len(unmarked_attendance) - 5} more_")
                embed.add_field(
                    name=f"📋 Attendance Not Marked ({len(unmarked_attendance)})",
                    value="\n".join(attend_lines),
                    inline=False
                )
            elif show_all:
                embed.add_field(
                    name="📋 Attendance Not Marked",
                    value="✅ All attendance recorded!",
                    inline=False
                )

            # 4. Check for upcoming exams
            upcoming_exams = await self._check_upcoming_exams(auth)
            if upcoming_exams:
                exam_lines = []
                for item in upcoming_exams[:5]:
                    days = item['days_until']
                    urgency = "🚨" if days == 0 else "⚠️" if days == 1 else "📌" if days <= 3 else "📝"
                    exam_lines.append(f"{urgency} **{item['subject_code']}** - {item['exam_date']}")
                if len(upcoming_exams) > 5:
                    exam_lines.append(f"_...and {len(upcoming_exams) - 5} more_")
                embed.add_field(
                    name=f"📅 Upcoming Exams ({len(upcoming_exams)})",
                    value="\n".join(exam_lines),
                    inline=False
                )

            # Add summary
            total_pending = len(waiting_for_grades) + len(pending_apps) + len(unmarked_attendance)
            if total_pending == 0:
                embed.description = "✅ **All caught up!** No pending items found."
                embed.color = discord.Color.green()
            else:
                embed.description = f"⏳ **{total_pending} item(s) pending** - requiring attention"

            # Add monitoring info
            embed.add_field(
                name="ℹ️ Auto-Monitoring",
                value=(
                    "• Grades: Every 2h (after exam)\n"
                    "• Applications: Every 30min (if pending)\n"
                    "• Attendance: Every 10min (during class)"
                ),
                inline=False
            )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in pending_checks: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {str(e)}")

    async def _check_waiting_grades(self, auth: FAPAuth) -> List[dict]:
        """Find subjects with passed exams but no grade yet"""
        try:
            exam_html = await auth.fetch_exam_schedule()
            if not exam_html:
                return []

            exams = self.exam_parser.parse_exam_schedule(exam_html)
            if not exams:
                return []

            grade_html = await auth.fetch_grades(student_id=self.student_id)
            graded_subjects = set()
            if grade_html:
                grades = self.grade_parser.parse_grades(grade_html)
                graded_subjects = {
                    g.subject_code for g in grades
                    if g.total and g.total > 0
                }

            waiting = []
            now = datetime.now()

            for exam in exams:
                if exam.subject_code in graded_subjects:
                    continue

                exam_datetime = self._parse_exam_datetime(exam.date, exam.time)
                if not exam_datetime:
                    continue

                if exam_datetime < now:
                    days_since = (now - exam_datetime).days
                    waiting.append({
                        'subject_code': exam.subject_code,
                        'subject_name': exam.subject_name,
                        'exam_date': exam.date,
                        'exam_time': exam.time,
                        'exam_datetime': exam_datetime,
                        'days_since': days_since
                    })

            waiting.sort(key=lambda x: x['days_since'], reverse=True)
            return waiting

        except Exception as e:
            logger.error(f"Error checking waiting grades: {e}")
            return []

    async def _check_pending_applications(self, auth: FAPAuth) -> List[dict]:
        """Find pending applications"""
        try:
            # For now, we need to use the application page
            # Note: fetch_application method might need to be added to FAPAuth
            # For now, we'll return empty list gracefully

            # TODO: Implement fetch_application in FAPAuth
            # app_html = await auth.fetch_application()
            # applications = self.app_parser.parse_applications(app_html)
            # return self.app_parser.get_pending_applications(applications)

            logger.warning("Application fetching not yet implemented in FAPAuth")
            return []

        except Exception as e:
            logger.error(f"Error checking pending applications: {e}")
            return []

    async def _check_unmarked_attendance(self, auth: FAPAuth) -> List[dict]:
        """Find attendance records not yet marked (status = '-')"""
        try:
            # Get today's schedule to find current classes
            schedule_html = await auth.fetch_schedule()
            if not schedule_html:
                return []

            schedule_items = self.schedule_parser.parse_schedule(schedule_html)
            today_items = self.schedule_parser.get_today_schedule(schedule_items)

            unmarked = []
            now = datetime.now()

            for item in today_items:
                # Check if this class is in the past or currently happening
                try:
                    # Parse slot time to check if class has started
                    slot_times = self.schedule_parser.SLOT_TIMES.get(item.slot, ("", ""))
                    if not slot_times[0]:
                        continue

                    # Parse start time
                    start_hour, start_min = map(int, slot_times[0].split(':'))
                    class_start = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

                    # Only check if class has already started
                    if now < class_start:
                        continue

                    # Check attendance status
                    if item.status in ('-', '', None):
                        unmarked.append({
                            'subject_code': item.subject_code,
                            'subject_name': item.subject_name,
                            'date': item.date,
                            'slot': item.slot,
                            'start_time': item.start_time,
                            'end_time': item.end_time
                        })

                except (ValueError, AttributeError):
                    continue

            return unmarked

        except Exception as e:
            logger.error(f"Error checking unmarked attendance: {e}")
            return []

    async def _check_upcoming_exams(self, auth: FAPAuth) -> List[dict]:
        """Find upcoming exams within next 7 days"""
        try:
            exam_html = await auth.fetch_exam_schedule()
            if not exam_html:
                return []

            exams = self.exam_parser.parse_exam_schedule(exam_html)
            if not exams:
                return []

            upcoming = []
            now = datetime.now()

            for exam in exams:
                exam_datetime = self._parse_exam_datetime(exam.date, exam.time)
                if not exam_datetime:
                    continue

                time_until = exam_datetime - now
                if timedelta(0) < time_until <= timedelta(days=7):
                    upcoming.append({
                        'subject_code': exam.subject_code,
                        'subject_name': exam.subject_name,
                        'exam_date': exam.date,
                        'exam_time': exam.time,
                        'exam_datetime': exam_datetime,
                        'days_until': time_until.days
                    })

            upcoming.sort(key=lambda x: x['exam_datetime'])
            return upcoming

        except Exception as e:
            logger.error(f"Error checking upcoming exams: {e}")
            return []

    @app_commands.command(name="grades", description="View subjects waiting for grades (exams passed, no grade yet)")
    async def pending_grades(self, interaction: discord.Interaction):
        """Show subjects with passed exams but no grade yet"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()

            waiting = await self._check_waiting_grades(auth)

            if not waiting:
                embed = discord.Embed(
                    title="✅ No Pending Grades",
                    description="All exams have been graded!",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"⏳ Waiting for Grades ({len(waiting)} subjects)",
                description="Exams passed, waiting for grades to be posted",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            for item in waiting[:10]:
                days = item['days_since']
                if days <= 3:
                    status_emoji = "🟢"
                    status_text = "Recently"
                elif days <= 7:
                    status_emoji = "🟡"
                    status_text = "Few days"
                elif days <= 14:
                    status_emoji = "🟠"
                    status_text = "Over a week"
                else:
                    status_emoji = "🔴"
                    status_text = "Long time"

                value = (
                    f"📝 {item['subject_name']}\n"
                    f"📅 Exam: {item['exam_date']} at {item['exam_time']}\n"
                    f"⏱️ {status_emoji} {days} days ago ({status_text})"
                )

                embed.add_field(
                    name=item['subject_code'],
                    value=value,
                    inline=False
                )

            if len(waiting) > 10:
                embed.add_field(
                    name="",
                    value=f"_...and {len(waiting) - 10} more_",
                    inline=False
                )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in pending_grades: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="exams", description="View upcoming exams in next 7 days")
    async def pending_exams(self, interaction: discord.Interaction):
        """Show upcoming exams within next 7 days"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()

            upcoming = await self._check_upcoming_exams(auth)

            if not upcoming:
                embed = discord.Embed(
                    title="📅 No Upcoming Exams",
                    description="No exams scheduled in the next 7 days",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"📅 Upcoming Exams ({len(upcoming)})",
                description="Exams in the next 7 days",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            for item in upcoming:
                days = item['days_until']
                if days == 0:
                    urgency = "🚨 TODAY!"
                elif days == 1:
                    urgency = "⚠️ Tomorrow"
                elif days <= 3:
                    urgency = "📌 Soon"
                else:
                    urgency = "📝 Upcoming"

                value = (
                    f"📚 {item['subject_name']}\n"
                    f"📅 {item['exam_date']}\n"
                    f"🕐 {item['exam_time']}\n"
                    f"⏳ {urgency} ({days} day{'s' if days != 1 else ''})"
                )

                embed.add_field(
                    name=item['subject_code'],
                    value=value,
                    inline=False
                )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in pending_exams: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="attendance", description="View today's unmarked attendance")
    async def pending_attendance(self, interaction: discord.Interaction):
        """Show attendance records not yet marked for today"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()

            unmarked = await self._check_unmarked_attendance(auth)

            if not unmarked:
                embed = discord.Embed(
                    title="✅ All Attendance Recorded",
                    description="All today's classes have attendance marked!",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"⏳ Unmarked Attendance ({len(unmarked)} classes)",
                description="Classes today with attendance not yet recorded",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )

            now = datetime.now()

            for item in unmarked[:10]:
                # Calculate urgency based on class end time
                try:
                    slot_times = self.schedule_parser.SLOT_TIMES.get(item['slot'], ("", ""))
                    if slot_times[1]:
                        end_hour, end_min = map(int, slot_times[1].split(':'))
                        class_end = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
                        time_left = class_end - now

                        if time_left.total_seconds() <= 0:
                            urgency = "🔴 Class ended!"
                        elif time_left.total_seconds() <= 900:  # 15 minutes
                            urgency = "🟠 Ending soon!"
                        elif time_left.total_seconds() <= 1800:  # 30 minutes
                            urgency = "🟡 Less than 30 min"
                        else:
                            urgency = "🟢 Ongoing"
                    else:
                        urgency = "⏳ Ongoing"
                except:
                    urgency = "⏳ Unknown"

                value = (
                    f"📚 {item.get('subject_name', item['subject_code'])}\n"
                    f"📅 {item['date']} | Slot {item['slot']}\n"
                    f"🕐 {item.get('start_time', '')} - {item.get('end_time', '')}\n"
                    f"⚠️ {urgency}"
                )

                embed.add_field(
                    name=item['subject_code'],
                    value=value,
                    inline=False
                )

            if len(unmarked) > 10:
                embed.add_field(
                    name="",
                    value=f"_...and {len(unmarked) - 10} more_",
                    inline=False
                )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in pending_attendance: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(PendingChecksCommands(bot))
    logger.info("Pending checks commands loaded")

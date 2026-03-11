"""
Discord Bot Commands - Attendance
Commands for viewing FAP attendance
"""
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View, Button
from typing import Optional, List
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.auth import FAPAuth
from scraper.attendance_parser import AttendanceParser, AttendanceSummary

logger = logging.getLogger(__name__)


class AttendanceView(View):
    """Interactive view for attendance navigation"""

    def __init__(self, parser: AttendanceParser, auth: FAPAuth, student_id: str, campus: int):
        super().__init__(timeout=None)
        self.parser = parser
        self.auth = auth
        self.student_id = student_id
        self.campus = campus
        self.current_term_id = None
        self.current_course_id = None
        self.terms: List[dict] = []
        self.courses: List[dict] = []

    async def refresh_menus(self):
        """Refresh dropdown menus with new data"""
        # Clear old select menus
        self.clear_items()

        # Add term selector
        if self.terms:
            term_options = [
                discord.SelectOption(
                    label=term['name'][:25],  # Discord 25 char limit
                    value=str(term['id']),
                    description="Current term" if term['is_current'] else ""
                )
                for term in self.terms[:25]
            ]
            self.add_item(TermSelect(term_options, self))

        # Add course selector
        if self.courses:
            course_options = [
                discord.SelectOption(
                    label=f"{course['code']} - {course['name'][:20]}",
                    value=str(course['course_id'])
                )
                for course in self.courses[:25]
            ]
            self.add_item(CourseSelect(course_options, self))

        # Add refresh button
        self.add_item(RefreshButton(self))


class TermSelect(Select):
    """Term selection dropdown"""

    def __init__(self, options: List[discord.SelectOption], view: AttendanceView):
        super().__init__(
            placeholder="Select a term...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        """Handle term selection"""
        term_id = self.values[0]
        self.view.current_term_id = term_id

        await interaction.response.defer(thinking=True)

        # Fetch courses for this term
        html = await self.view.auth.fetch_attendance(
            student_id=self.view.student_id,
            campus=self.view.campus,
            term=int(term_id) if term_id.isdigit() else None
        )

        if html:
            self.view.courses = self.view.parser.extract_courses(html)
            await self.view.refresh_menus()
            await interaction.followup.edit_message(
                message=interaction.message.id,
                view=self.view
            )
            await interaction.followup.send(f"✅ Loaded {len(self.view.courses)} courses for selected term")
        else:
            await interaction.followup.send("❌ Failed to load courses")


class CourseSelect(Select):
    """Course selection dropdown"""

    def __init__(self, options: List[discord.SelectOption], view: AttendanceView):
        super().__init__(
            placeholder="Select a course...",
            min_values=1,
            max_values=1,
            options=options,
            row=1
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        """Handle course selection"""
        course_id = self.values[0]
        self.view.current_course_id = course_id

        await interaction.response.defer(thinking=True)

        # Fetch attendance for this course
        html = await self.view.auth.fetch_attendance(
            student_id=self.view.student_id,
            campus=self.view.campus,
            term=int(self.view.current_term_id) if self.view.current_term_id and self.view.current_term_id.isdigit() else None,
            course=int(course_id)
        )

        if html:
            items = self.view.parser.parse_attendance(html)
            summary = self.view.parser.calculate_summary(items)
            message = self.view.parser.format_for_discord(items, summary, "Attendance Report")

            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)
        else:
            await interaction.followup.send("❌ Failed to load attendance data")


class RefreshButton(Button):
    """Refresh button"""

    def __init__(self, view: AttendanceView):
        super().__init__(
            label="Refresh",
            style=discord.ButtonStyle.secondary,
            row=2
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        """Handle refresh"""
        await interaction.response.defer(thinking=True)

        # Re-fetch terms
        html = await self.view.auth.fetch_attendance(
            student_id=self.view.student_id,
            campus=self.view.campus
        )

        if html:
            self.view.terms = self.view.parser.extract_terms(html)
            self.view.courses = []
            await self.view.refresh_menus()
            await interaction.followup.edit_message(
                message=interaction.message.id,
                view=self.view
            )
            await interaction.followup.send("✅ Refreshed term list")
        else:
            await interaction.followup.send("❌ Failed to refresh")


class AttendanceCommands(commands.GroupCog, name="attendance"):
    """Attendance viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth: Optional[FAPAuth] = None
        self.parser = AttendanceParser()
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

    @app_commands.command(name="view", description="View attendance history")
    @app_commands.describe(
        term="Term ID (e.g., 60 for Spring2026)",
        course="Course ID (e.g., 57599)"
    )
    async def attendance_view(
        self,
        interaction: discord.Interaction,
        term: Optional[int] = None,
        course: Optional[int] = None
    ):
        """View attendance with interactive menu"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()

            # Fetch attendance page
            html = await auth.fetch_attendance(
                student_id=self.student_id,
                campus=self.campus,
                term=term,
                course=course
            )

            if not html:
                await interaction.followup.send("❌ Failed to fetch attendance. Please try again later.")
                return

            # If term and course specified, show direct results
            if term and course:
                items = self.parser.parse_attendance(html)
                summary = self.parser.calculate_summary(items)
                message = self.parser.format_for_discord(items, summary, "Attendance Report")

                if len(message) > 1900:
                    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                    await interaction.followup.send(chunks[0])
                    for chunk in chunks[1:]:
                        await interaction.followup.send(chunk)
                else:
                    await interaction.followup.send(message)
                return

            # Otherwise, show interactive menu
            terms = self.parser.extract_terms(html)

            if not terms:
                await interaction.followup.send("❌ No terms found.")
                return

            view = AttendanceView(self.parser, auth, self.student_id, self.campus)
            view.terms = terms
            view.courses = self.parser.extract_courses(html) if term else []
            await view.refresh_menus()

            await interaction.followup.send(
                "📊 **Attendance Viewer**\nSelect a term to view attendance:",
                view=view
            )

        except Exception as e:
            logger.error(f"Error in attendance_view: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="this-term", description="Quick view attendance for current term")
    async def attendance_this_term(self, interaction: discord.Interaction):
        """Show attendance summary for most recent term - Dashboard View grouped by subject"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()

            # Fetch default page - shows newest term + first course
            html = await auth.fetch_attendance(
                student_id=self.student_id,
                campus=self.campus
            )

            if not html:
                await interaction.followup.send("❌ Failed to fetch attendance. Please try again later.")
                return

            # Extract courses from the default page
            courses = self.parser.extract_courses(html)
            if not courses:
                await interaction.followup.send("❌ No courses found.")
                return

            # Get term name from the page - find the current term (marked with <b>)
            terms = self.parser.extract_terms(html)
            current_term = next((t for t in terms if t.get('is_current')), None)
            term_name = current_term['name'] if current_term else (terms[-1]['name'] if terms else "Current Term")

            # Aggregate attendance across all courses
            all_items = []

            # First course (Elementary Japanese) - already shown in default page
            for course in courses:
                if course['is_current']:
                    # Current course - parse from the HTML we already have
                    items = self.parser.parse_attendance(html)
                    # Add course info to items
                    for item in items:
                        item.subject_code = course['code']
                        item.subject_name = course['name']
                    all_items.extend(items)
                    logger.info(f"Parsed {len(items)} attendance records for current course: {course['name']}")
                elif course['course_id']:
                    # Fetch detailed attendance for this course
                    course_html = await auth.fetch_attendance(
                        student_id=self.student_id,
                        campus=self.campus,
                        course=course['course_id']
                    )
                    if course_html:
                        items = self.parser.parse_attendance(course_html)
                        # Add course info to items
                        for item in items:
                            item.subject_code = course['code']
                            item.subject_name = course['name']
                        all_items.extend(items)
                        logger.info(f"Parsed {len(items)} attendance records for: {course['name']}")

            if not all_items:
                await interaction.followup.send(f"❌ No attendance records found for {term_name}")
                return

            # Group by subject code
            from collections import defaultdict
            subject_stats = defaultdict(lambda: {'present': 0, 'absent': 0, 'future': 0, 'items': []})

            for item in all_items:
                key = item.subject_code or "Unknown"
                subject_stats[key]['items'].append(item)
                if item.attendance_status == 'present':
                    subject_stats[key]['present'] += 1
                elif item.attendance_status == 'absent':
                    subject_stats[key]['absent'] += 1
                else:
                    subject_stats[key]['future'] += 1

            # Calculate overall stats
            total_present = sum(s['present'] for s in subject_stats.values())
            total_absent = sum(s['absent'] for s in subject_stats.values())
            total_future = sum(s['future'] for s in subject_stats.values())
            total_eligible = total_present + total_absent
            overall_percent = (total_present / total_eligible * 100) if total_eligible > 0 else 0

            # Create Dashboard Embed
            embed = discord.Embed(
                title=f"📊 Attendance Dashboard - {term_name}",
                description=f"📈 **Overall:** {total_present}/{total_eligible} ({overall_percent:.1f}%) | ❌ {total_absent} Absent | ⏳ {total_future} Future",
                color=discord.Color.green() if overall_percent >= 80 else discord.Color.yellow() if overall_percent >= 60 else discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )

            # Add each subject as a field
            # Sort by absence count (most absent first - most concerning)
            sorted_subjects = sorted(
                subject_stats.items(),
                key=lambda x: x[1]['absent'],
                reverse=True
            )

            for subject_code, stats in sorted_subjects:
                eligible = stats['present'] + stats['absent']
                percent = (stats['present'] / eligible * 100) if eligible > 0 else 0
                absent = stats['absent']

                # Determine status based on absence count (20% rule = fail)
                if absent == 0:
                    status_emoji = "🟢"
                    status_text = "An toàn"
                elif absent == 1:
                    status_emoji = "🟢"
                    status_text = "An toàn"
                elif absent <= 3:
                    status_emoji = "🟡"
                    status_text = "Chú ý"
                elif absent == 4:
                    status_emoji = "🟠"
                    status_text = "Nguy hiểm!"
                else:  # >= 5
                    status_emoji = "🔴"
                    status_text = "RỚT MÔN!"

                # Check if failed (>20% absent)
                total = stats['present'] + stats['absent'] + stats['future']
                if total > 0 and absent / total > 0.2:
                    status_emoji = "💀"
                    status_text = "RỚT MÔN (>20%)"

                # Build field value
                field_value = f"{status_emoji} **{percent:.1f}%** | Có mặt: {stats['present']} | ❌ Vắng: {absent}"

                if absent == 0:
                    field_value += " ✨ Perfect!"
                elif absent == 1:
                    field_value += f" ({status_text})"
                elif absent >= 2:
                    field_value += f"\n⚠️ **{status_text}**"
                    if absent >= 4:
                        field_value += " Cần liên hệ GV ngay!"

                if stats['future'] > 0:
                    field_value += f"\n⏳ Còn {stats['future']} buổi"

                # Calculate absences remaining until fail (20% threshold)
                if total > 0:
                    max_absent = int(total * 0.2)  # 20% of total sessions
                    remaining_can_miss = max_absent - absent
                    if remaining_can_miss > 0:
                        field_value += f"\n📌 Chỉ được vắng thêm {remaining_can_miss} buổi nữa"
                    elif remaining_can_miss == 0:
                        field_value += f"\n📌 Đã đạt giới hạn vắng (20%)"

                # Get subject name from first item
                subject_name = stats['items'][0].subject_name if stats['items'] else subject_code
                # Shorten name if too long
                display_name = f"{subject_code} - {subject_name}" if subject_name != subject_code else subject_code
                if len(display_name) > 50:
                    display_name = display_name[:47] + "..."

                embed.add_field(
                    name=display_name,
                    value=field_value,
                    inline=False
                )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in attendance_this_term: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(AttendanceCommands(bot))
    logger.info("Attendance commands loaded")

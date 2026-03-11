"""
Discord Bot Commands - Grades
Commands for viewing FAP grades and GPA
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
from scraper.grade_parser import GradeParser, GPASummary

logger = logging.getLogger(__name__)


class GradeView(View):
    """Interactive view for grade navigation"""

    def __init__(self, parser: GradeParser, auth: FAPAuth, student_id: str):
        super().__init__(timeout=None)
        self.parser = parser
        self.auth = auth
        self.student_id = student_id
        self.current_term_name = None
        self.current_course_id = None
        self.terms: List[dict] = []
        self.courses: List[dict] = []
        self.all_terms_grades: dict = {}  # Cache grades for cumulative GPA

    async def refresh_menus(self):
        """Refresh dropdown menus with new data"""
        self.clear_items()

        # Add term selector
        if self.terms:
            term_options = [
                discord.SelectOption(
                    label=term['name'][:25],
                    value=str(term['name']),
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

        # Add GPA button
        self.add_item(GPAButton(self))

        # Add refresh button
        self.add_item(RefreshButton(self))


class TermSelect(Select):
    """Term selection dropdown"""

    def __init__(self, options: List[discord.SelectOption], view: GradeView):
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
        term_name = self.values[0]
        self.view.current_term_name = term_name

        await interaction.response.defer(thinking=True)

        # Fetch courses for this term
        html = await self.view.auth.fetch_grades(
            student_id=self.view.student_id,
            term=term_name
        )

        if html:
            self.view.courses = self.view.parser.extract_courses(html)
            await self.view.refresh_menus()
            await interaction.followup.edit_message(
                message=interaction.message.id,
                view=self.view
            )
            await interaction.followup.send(f"✅ Loaded {len(self.view.courses)} courses for {term_name}")
        else:
            await interaction.followup.send("❌ Failed to load courses")


class CourseSelect(Select):
    """Course selection dropdown"""

    def __init__(self, options: List[discord.SelectOption], view: GradeView):
        super().__init__(
            placeholder="Select a course (or leave empty for all)...",
            min_values=0,
            max_values=1,
            options=options,
            row=1
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        """Handle course selection"""
        if not self.values:
            # Show all courses for term
            await self._show_all_courses(interaction)
        else:
            course_id = self.values[0]
            await self._show_single_course(interaction, course_id)

    async def _show_all_courses(self, interaction: discord.Interaction):
        """Show all grades for current term"""
        await interaction.response.defer(thinking=True)

        html = await self.view.auth.fetch_grades(
            student_id=self.view.student_id,
            term=self.view.current_term_name
        )

        if html:
            grades = self.view.parser.parse_grades(html)

            # Cache for cumulative GPA
            self.view.all_terms_grades[self.view.current_term_name] = grades

            # Calculate GPA
            gpa_summary = self.view.parser.calculate_gpa(
                grades,
                self.view.all_terms_grades
            )
            gpa_summary.term = self.view.current_term_name

            message = self.view.parser.format_for_discord(grades, gpa_summary, f"Grades - {self.view.current_term_name}")

            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)
        else:
            await interaction.followup.send("❌ Failed to load grade data")

    async def _show_single_course(self, interaction: discord.Interaction, course_id: str):
        """Show grades for single course"""
        await interaction.response.defer(thinking=True)

        html = await self.view.auth.fetch_grades(
            student_id=self.view.student_id,
            term=self.view.current_term_name,
            course=int(course_id)
        )

        if html:
            grades = self.view.parser.parse_grades(html)

            if grades:
                grade = grades[0]
                lines = [
                    f"📊 **{grade.subject_code} - {grade.subject_name}**",
                    "",
                    f"📈 **Mid-term:** {grade.mid_term}/10",
                    f"📈 **Final:** {grade.final}/10",
                    f"📈 **Total:** {grade.total}/10",
                    f"📊 **4.0 Scale:** {grade.grade_4scale}",
                    f"✅ **Status:** {grade.status}",
                    f"📚 **Credits:** {grade.credits}",
                ]
                await interaction.followup.send("\n".join(lines))
            else:
                await interaction.followup.send("❌ No grade data found for this course")
        else:
            await interaction.followup.send("❌ Failed to load grade data")


class GPAButton(Button):
    """Calculate cumulative GPA button"""

    def __init__(self, view: GradeView):
        super().__init__(
            label="Calculate Cumulative GPA",
            style=discord.ButtonStyle.primary,
            row=2
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        """Calculate and show cumulative GPA across all recent terms"""
        await interaction.response.defer(thinking=True)

        # Fetch grades for all recent terms
        all_grades = {}
        for term in self.view.terms:
            term_name = term['name']
            html = await self.view.auth.fetch_grades(
                student_id=self.view.student_id,
                term=term_name
            )
            if html:
                grades = self.view.parser.parse_grades(html)
                if grades:
                    all_grades[term_name] = grades

        if not all_grades:
            await interaction.followup.send("❌ No grade data found")
            return

        # Calculate cumulative GPA
        all_grades_flat = []
        for term_grades in all_grades.values():
            all_grades_flat.extend(term_grades)

        gpa_summary = self.view.parser.calculate_gpa(all_grades_flat, all_grades)

        lines = [
            "📊 **Cumulative GPA Summary**",
            "",
            f"🎯 **Cumulative GPA:** {gpa_summary.cumulative_gpa:.2f} / 4.0",
            f"📚 **Total Credits:** {gpa_summary.total_credits}",
            f"✅ **Earned Credits:** {gpa_summary.earned_credits}",
            f"📖 **Subjects Passed:** {gpa_summary.subjects_passed}",
            f"❌ **Subjects Failed:** {gpa_summary.subjects_failed}",
        ]

        if gpa_summary.excluded_subjects:
            lines.append(f"⚠️ **Excluded from GPA:** {', '.join(set(gpa_summary.excluded_subjects))}")

        lines.append("")
        lines.append("**Breakdown by Term:**")

        for term_name, term_gpa in sorted(gpa_summary.by_term.items(), reverse=True):
            lines.append(
                f"• **{term_name}:** {term_gpa.term_gpa:.2f} | "
                f"Passed: {term_gpa.subjects_passed}/{term_gpa.subjects_passed + term_gpa.subjects_failed}"
            )

        message = "\n".join(lines)
        await interaction.followup.send(message[:1900])  # Discord limit


class RefreshButton(Button):
    """Refresh button"""

    def __init__(self, view: GradeView):
        super().__init__(
            label="Refresh",
            style=discord.ButtonStyle.secondary,
            row=3
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        """Handle refresh"""
        await interaction.response.defer(thinking=True)

        # Re-fetch terms
        html = await self.view.auth.fetch_grades(
            student_id=self.view.student_id
        )

        if html:
            self.view.terms = self.view.parser.extract_terms(html)
            self.view.courses = []
            self.view.all_terms_grades = {}
            await self.view.refresh_menus()
            await interaction.followup.edit_message(
                message=interaction.message.id,
                view=self.view
            )
            await interaction.followup.send("✅ Refreshed term list")
        else:
            await interaction.followup.send("❌ Failed to refresh")


class GradeCommands(commands.GroupCog, name="grade"):
    """Grade viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth: Optional[FAPAuth] = None
        self.parser = GradeParser()
        self.student_id = os.getenv('FAP_STUDENT_ID', '')

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

    @app_commands.command(name="view", description="View grades with interactive menu")
    @app_commands.describe(
        term="Term name (e.g., Spring2026, Fall2025)",
        course="Course ID (e.g., 55959)"
    )
    async def grade_view(
        self,
        interaction: discord.Interaction,
        term: Optional[str] = None,
        course: Optional[int] = None
    ):
        """View grades with interactive menu"""
        # Respond immediately to avoid timeout
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logger.warning("Interaction expired before defer could complete")
            return
        except discord.HTTPException:
            logger.warning("Interaction already acknowledged")
            return

        try:
            auth = await self._get_auth()

            # Fetch grade page
            html = await auth.fetch_grades(
                student_id=self.student_id,
                term=term,
                course=course
            )

            if not html:
                await interaction.followup.send("❌ Failed to fetch grades. Please try again later.", ephemeral=True)
                return

            # If term and course specified, show direct results
            if term and course:
                grades = self.parser.parse_grades(html)
                if grades:
                    grade = grades[0]
                    lines = [
                        f"📊 **{grade.subject_code} - {grade.subject_name}**",
                        "",
                        f"📈 **Mid-term:** {grade.mid_term}/10",
                        f"📈 **Final:** {grade.final}/10",
                        f"📈 **Total:** {grade.total}/10",
                        f"📊 **4.0 Scale:** {grade.grade_4scale}",
                        f"✅ **Status:** {grade.status}",
                        f"📚 **Credits:** {grade.credits}",
                    ]
                    await interaction.followup.send("\n".join(lines), ephemeral=True)
                else:
                    await interaction.followup.send("❌ No grade data found", ephemeral=True)
                return

            # If only term specified, show all grades for term
            if term:
                grades = self.parser.parse_grades(html)
                gpa_summary = self.parser.calculate_gpa(grades, {term: grades})
                gpa_summary.term = term
                message = self.parser.format_for_discord(grades, gpa_summary, f"Grades - {term}")

                if len(message) > 1900:
                    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                    await interaction.followup.send(chunks[0], ephemeral=True)
                    for chunk in chunks[1:]:
                        await interaction.followup.send(chunk, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)
                return

            # Otherwise, show interactive menu
            terms = self.parser.extract_terms(html)

            if not terms:
                await interaction.followup.send("❌ No terms found.", ephemeral=True)
                return

            view = GradeView(self.parser, auth, self.student_id)
            view.terms = terms
            view.courses = self.parser.extract_courses(html) if term else []
            await view.refresh_menus()

            await interaction.followup.send(
                "📊 **Grade Viewer**\nSelect a term to view grades:",
                view=view
            )

        except discord.NotFound:
            logger.warning("Interaction expired before response could be sent")
        except Exception as e:
            logger.error(f"Error in grade_view: {e}")
            try:
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
            except discord.NotFound:
                logger.warning("Interaction expired when trying to send error message")

    @app_commands.command(name="this-term", description="Quick view grades for current term")
    async def grade_this_term(self, interaction: discord.Interaction):
        """Show grades summary for most recent term - Dashboard View grouped by subject"""
        # Respond immediately to avoid timeout
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            # Interaction already expired - nothing we can do
            logger.warning("Interaction expired before defer could complete")
            return
        except discord.HTTPException as e:
            # Interaction already acknowledged somehow
            logger.warning(f"Interaction already acknowledged: {e}")
            return

        try:
            auth = await self._get_auth()

            # Fetch default page - shows newest term (Fall2025) + course list
            html = await auth.fetch_grades(
                student_id=self.student_id
            )

            if not html:
                await interaction.followup.send("❌ Failed to fetch grades. Please try again later.", ephemeral=True)
                return

            logger.info(f"Base page HTML length: {len(html)} chars")

            # Extract courses from the default page
            courses = self.parser.extract_courses(html)
            logger.info(f"Extracted {len(courses)} courses from base page")

            if not courses:
                await interaction.followup.send("❌ No courses found.", ephemeral=True)
                return

            # Get term name from the page - get last term (most recent)
            terms = self.parser.extract_terms(html)
            term_name = terms[-1]['name'] if terms else "Current Term"

            logger.info(f"Processing term: {term_name} with {len(courses)} courses")

            # Fetch grades for EACH course (all courses need to be clicked individually)
            all_grades = []

            for i, course in enumerate(courses):
                logger.info(f"[{i+1}/{len(courses)}] Fetching grades for {course['code']}: {course.get('course_id')}")
                if course['course_id']:
                    # Fetch detailed grades for this course
                    course_html = await auth.fetch_grades(
                        student_id=self.student_id,
                        course=course['course_id']
                    )
                    if course_html:
                        logger.info(f"  Course HTML length: {len(course_html)} chars")
                        course_grades = self.parser.parse_grades(course_html)
                        logger.info(f"  Parsed {len(course_grades)} grade records")
                        # Add course code/name to grades (in case it's not in the parsed data)
                        for grade in course_grades:
                            if not grade.subject_code:
                                grade.subject_code = course['code']
                            if not grade.subject_name or grade.subject_name == grade.subject_code:
                                grade.subject_name = course['name'].split('(')[0].strip()
                        all_grades.extend(course_grades)
                    else:
                        logger.warning(f"  No HTML returned for course {course['code']}")
                else:
                    logger.warning(f"  Skipping course {course['code']} - no course_id")

            logger.info(f"Total grades collected: {len(all_grades)}")

            if not all_grades:
                await interaction.followup.send(f"❌ No grades found for {term_name}", ephemeral=True)
                return

            # Calculate GPA
            gpa_summary = self.parser.calculate_gpa(all_grades, {term_name: all_grades})
            gpa_summary.term = term_name

            # Create Dashboard Embed
            embed_color = discord.Color.green() if gpa_summary.cumulative_gpa >= 3.5 else discord.Color.yellow() if gpa_summary.cumulative_gpa >= 3.0 else discord.Color.orange() if gpa_summary.cumulative_gpa >= 2.0 else discord.Color.red()

            embed = discord.Embed(
                title=f"📊 Grade Dashboard - {term_name}",
                description=f"🎯 **Term GPA:** {gpa_summary.term_gpa:.2f}/4.0 | 📚 Credits: {gpa_summary.earned_credits}/{gpa_summary.total_credits} | ✅ Passed: {gpa_summary.subjects_passed} | ❌ Failed: {gpa_summary.subjects_failed}",
                color=embed_color,
                timestamp=discord.utils.utcnow()
            )

            # Group grades by subject code
            from collections import defaultdict
            subject_grades = defaultdict(list)
            for grade in all_grades:
                subject_grades[grade.subject_code].append(grade)

            # Sort subjects by total grade (lowest first)
            sorted_subjects = sorted(
                subject_grades.items(),
                key=lambda x: x[1][0].total if x[1] else 0
            )

            for subject_code, grades in sorted_subjects:
                grade = grades[0]  # Take first grade record

                # Determine status emoji and color
                if grade.total >= 8.5:
                    status_emoji = "🟢"
                    grade_letter = "A"
                elif grade.total >= 7.0:
                    status_emoji = "🟡"
                    grade_letter = "B"
                elif grade.total >= 5.5:
                    status_emoji = "🟠"
                    grade_letter = "C"
                elif grade.total >= 4.0:
                    status_emoji = "🔴"
                    grade_letter = "D"
                elif grade.total > 0:
                    status_emoji = "⚫"
                    grade_letter = "F"
                else:
                    status_emoji = "⏳"
                    grade_letter = "N/A"

                # Build field value
                field_value = f"{status_emoji} **Total:** {grade.total}/10 ({grade_letter}) | 4.0 Scale: {grade.grade_4scale}\n"
                field_value += f"📖 Mid-term: {grade.mid_term} | 📝 Final: {grade.final}\n"
                field_value += f"📚 Credits: {grade.credits} | ✅ Status: {grade.status}"

                # Get subject name - shorten if needed
                display_name = f"{subject_code} - {grade.subject_name}" if grade.subject_name and grade.subject_name != subject_code else subject_code
                if len(display_name) > 50:
                    # Try to extract just the meaningful part
                    if '(' in display_name:
                        display_name = display_name[:display_name.index('(')].strip()
                    else:
                        display_name = display_name[:47] + "..."

                embed.add_field(
                    name=display_name,
                    value=field_value,
                    inline=False
                )

            # Add excluded subjects info if any
            if gpa_summary.excluded_subjects:
                embed.add_field(
                    name="⚠️ Excluded from GPA",
                    value=', '.join(set(gpa_summary.excluded_subjects)),
                    inline=False
                )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.NotFound:
            # Interaction expired - can't respond
            logger.warning("Interaction expired before response could be sent")
        except discord.NotFound:
            # Interaction expired - can't respond
            logger.warning("Interaction expired before response could be sent")
        except Exception as e:
            logger.error(f"Error in grade_this_term: {e}")
            try:
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
            except discord.NotFound:
                logger.warning("Interaction expired when trying to send error message")

    @app_commands.command(name="gpa", description="Calculate cumulative GPA across all terms")
    async def grade_gpa(self, interaction: discord.Interaction):
        """Calculate cumulative GPA across all recent terms"""
        # Respond immediately to avoid timeout
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logger.warning("Interaction expired before defer could complete")
            return
        except discord.HTTPException:
            logger.warning("Interaction already acknowledged")
            return

        try:
            auth = await self._get_auth()

            # Fetch base page to get terms
            html = await auth.fetch_grades(
                student_id=self.student_id
            )

            if not html:
                await interaction.followup.send("❌ Failed to fetch grades. Please try again later.", ephemeral=True)
                return

            logger.info(f"Base page HTML length: {len(html)} chars")

            terms = self.parser.extract_terms(html)
            logger.info(f"Extracted {len(terms)} terms")

            if not terms:
                await interaction.followup.send("❌ No terms found.", ephemeral=True)
                return

            # Fetch grades for all terms - use course-based fetch like grade_this_term
            all_grades = {}
            for i, term in enumerate(terms):
                term_name = term['name']
                logger.info(f"[{i+1}/{len(terms)}] Processing term: {term_name}")

                # Fetch by term to get the course list for this term
                html = await auth.fetch_grades(
                    student_id=self.student_id,
                    term=term_name
                )

                if not html:
                    logger.warning(f"  No HTML returned for term {term_name}")
                    continue

                # Extract courses from this term's page
                courses = self.parser.extract_courses(html)
                logger.info(f"  Found {len(courses)} courses in {term_name}")

                if not courses:
                    logger.warning(f"  No courses found for {term_name}")
                    continue

                # Fetch each course individually to get detailed grades
                term_grades = []
                for j, course in enumerate(courses):
                    if course['course_id']:
                        logger.info(f"    [{j+1}/{len(courses)}] Fetching {course['code']}")
                        course_html = await auth.fetch_grades(
                            student_id=self.student_id,
                            course=course['course_id']
                        )
                        if course_html:
                            course_grades = self.parser.parse_grades(course_html)
                            # Add course info to grades
                            for grade in course_grades:
                                if not grade.subject_code:
                                    grade.subject_code = course['code']
                                if not grade.subject_name or grade.subject_name == grade.subject_code:
                                    grade.subject_name = course['name'].split('(')[0].strip()
                            term_grades.extend(course_grades)
                            logger.info(f"      Parsed {len(course_grades)} grades")
                        else:
                            logger.warning(f"      No HTML for {course['code']}")
                    else:
                        logger.warning(f"    Skipping {course['code']} - no course_id")

                if term_grades:
                    all_grades[term_name] = term_grades
                    logger.info(f"  Total grades for {term_name}: {len(term_grades)}")

            if not all_grades:
                await interaction.followup.send("❌ No grade data found", ephemeral=True)
                return

            logger.info(f"Total terms with grades: {len(all_grades)}")

            # Calculate cumulative GPA
            all_grades_flat = []
            for term_grades in all_grades.values():
                all_grades_flat.extend(term_grades)

            logger.info(f"Total grade records: {len(all_grades_flat)}")

            gpa_summary = self.parser.calculate_gpa(all_grades_flat, all_grades)

            lines = [
                "📊 **Cumulative GPA Summary**",
                "",
                f"🎯 **Cumulative GPA:** {gpa_summary.cumulative_gpa:.2f} / 4.0",
                f"📚 **Total Credits:** {gpa_summary.total_credits}",
                f"✅ **Earned Credits:** {gpa_summary.earned_credits}",
                f"📖 **Subjects Passed:** {gpa_summary.subjects_passed}",
                f"❌ **Subjects Failed:** {gpa_summary.subjects_failed}",
            ]

            if gpa_summary.excluded_subjects:
                lines.append(f"⚠️ **Excluded from GPA:** {', '.join(set(gpa_summary.excluded_subjects))}")

            lines.append("")
            lines.append("**Breakdown by Term:**")

            for term_name, term_gpa in sorted(gpa_summary.by_term.items(), reverse=True):
                lines.append(
                    f"• **{term_name}:** {term_gpa.term_gpa:.2f} | "
                    f"Passed: {term_gpa.subjects_passed}/{term_gpa.subjects_passed + term_gpa.subjects_failed}"
                )

            # Grade breakdown
            if gpa_summary.grade_breakdown:
                lines.append("")
                lines.append("**Grade Distribution:**")
                for grade_range, count in sorted(gpa_summary.grade_breakdown.items()):
                    lines.append(f"• {grade_range}: {count}")

            message = "\n".join(lines)

            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0], ephemeral=True)
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)

        except discord.NotFound:
            logger.warning("Interaction expired before response could be sent")
        except Exception as e:
            logger.error(f"Error in grade_gpa: {e}")
            try:
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
            except discord.NotFound:
                logger.warning("Interaction expired when trying to send error message")


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(GradeCommands(bot))
    logger.info("Grade commands loaded")

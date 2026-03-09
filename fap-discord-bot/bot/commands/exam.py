"""
Discord Bot Commands - Exam
Commands for viewing exam schedule
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.auth import FAPAuth
from scraper.exam_parser import ExamParser
from typing import Optional


class ExamCommands(commands.GroupCog, name="exam"):
    """Exam schedule viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.parser = ExamParser()
        self.auth: Optional[FAPAuth] = None

    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.auth:
            await self.auth.close()

    async def _get_auth(self) -> FAPAuth:
        """Get or create auth instance"""
        if self.auth is None:
            from dotenv import load_dotenv
            import os
            load_dotenv()

            self.auth = FAPAuth(
                username=os.getenv('FAP_USERNAME', ''),
                password=os.getenv('FAP_PASSWORD', ''),
                headless=os.getenv('HEADLESS', 'true').lower() == 'true',
                user_agent=os.getenv('USER_AGENT')
            )
        return self.auth

    @app_commands.command(name="schedule", description="View exam schedule")
    async def exam_schedule(self, interaction: discord.Interaction):
        """Show exam schedule"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()
            html = await auth.fetch_exam_schedule()

            if not html:
                await interaction.followup.send("Failed to fetch exam schedule. Please try again.")
                return

            # Parse exams
            exams = self.parser.parse_exam_schedule(html)

            if not exams:
                await interaction.followup.send("No exams found.")
                return

            # Format and send
            lines = [f"📚 **Exam Schedule**\n"]
            lines.append(f"Found {len(exams)} exam(s)\n")

            for exam in exams:
                lines.append(f"**{exam.no}. {exam.subject_code} - {exam.subject_name}**")
                lines.append(f"📅 {exam.date} | 🕐 {exam.time}")
                lines.append(f"📍 Room {exam.room} | 📝 {exam.exam_type}")
                lines.append("")

            message = "\n".join(lines)

            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)

        except Exception as e:
            logging.error(f"Error in exam_schedule: {e}")
            await interaction.followup.send(f"Error: {str(e)}")

    @app_commands.command(name="upcoming", description="View upcoming exams (next 7 days)")
    async def exam_upcoming(self, interaction: discord.Interaction):
        """Show upcoming exams"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()
            html = await auth.fetch_exam_schedule()

            if not html:
                await interaction.followup.send("Failed to fetch exam schedule.")
                return

            exams = self.parser.parse_exam_schedule(html)
            upcoming = self.parser.get_upcoming_exams(exams, days=7)

            if not upcoming:
                await interaction.followup.send("No upcoming exams in the next 7 days.")
                return

            lines = [f"📚 **Upcoming Exams (Next 7 Days)**\n"]
            lines.append(f"Found {len(upcoming)} exam(s)\n")

            for exam in upcoming:
                lines.append(f"**{exam.subject_code} - {exam.subject_name}**")
                lines.append(f"📅 {exam.date} | 🕐 {exam.time}")
                lines.append(f"📍 Room {exam.room}")
                lines.append("")

            message = "\n".join(lines)

            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)

        except Exception as e:
            logging.error(f"Error in exam_upcoming: {e}")
            await interaction.followup.send(f"Error: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(ExamCommands(bot))
    logging.info("Exam commands loaded")

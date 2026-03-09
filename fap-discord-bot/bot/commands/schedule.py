"""
Discord Bot Commands - Schedule
Commands for viewing FAP schedule
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.auth import FAPAuth
from scraper.parser import FAPParser

logger = logging.getLogger(__name__)


class ScheduleCommands(commands.GroupCog, name="schedule"):
    """Schedule viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth: Optional[FAPAuth] = None
        self.parser = FAPParser()

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

    @app_commands.command(name="today", description="View today's schedule")
    async def schedule_today(self, interaction: discord.Interaction):
        """Show schedule for today"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()
            html = await auth.fetch_schedule()

            if not html:
                await interaction.followup.send("❌ Failed to fetch schedule. Please try again later.")
                return

            items = self.parser.parse_schedule(html)
            today_items = self.parser.get_today_schedule(items)

            message = self.parser.format_for_discord(today_items, "Today's Schedule")

            # Split if too long
            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)

        except Exception as e:
            logger.error(f"Error in schedule_today: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="week", description="View this week's schedule")
    @app_commands.describe(
        week="Week number (1-52), leave empty for current week",
        year="Year, leave empty for current year"
    )
    async def schedule_week(
        self,
        interaction: discord.Interaction,
        week: Optional[int] = None,
        year: Optional[int] = None
    ):
        """Show schedule for a specific week"""
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()
            html = await auth.fetch_schedule(week=week, year=year)

            if not html:
                await interaction.followup.send("❌ Failed to fetch schedule. Please try again later.")
                return

            items = self.parser.parse_schedule(html)

            week_str = f"Week {week}" if week else "This Week"
            year_str = f" {year}" if year else ""
            title = f"{week_str}{year_str} Schedule"

            message = self.parser.format_for_discord(items, title)

            # Split if too long
            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)

        except Exception as e:
            logger.error(f"Error in schedule_week: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(ScheduleCommands(bot))
    logger.info("Schedule commands loaded")

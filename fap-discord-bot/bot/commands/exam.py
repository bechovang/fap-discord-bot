"""
Discord Bot Commands - Exam
Commands for viewing exam schedule
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

logger = logging.getLogger(__name__)


class ExamCommands(commands.GroupCog, name="exam"):
    """Exam schedule viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
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
                user_agent=os.getenv('USER_AGENT'),
                auto_refresh=os.getenv('AUTO_REFRESH', 'true').lower() == 'true'
            )
        return self.auth

    @app_commands.command(name="schedule", description="View exam schedule")
    async def exam_schedule(self, interaction: discord.Interaction):
        """Show exam schedule"""
        await interaction.response.defer(thinking=True)

        try:
            # Note: FAP doesn't have a dedicated exam schedule page
            # This command is a placeholder for future implementation
            # Exam schedules may be available through different means

            embed = discord.Embed(
                title="📚 Exam Schedule",
                description="FAP doesn't have a dedicated exam schedule page.",
                color=discord.Color.orange()
            )

            embed.add_field(
                name="🔗 Alternative",
                value="Check your exam schedule at:\n"
                      "• FAP Portal → Academics → Exams\n"
                      "• Student Portal → Exam Schedule",
                inline=False
            )

            embed.add_field(
                name="💡 Tip",
                value="Use `/schedule week` to check your regular class schedule.\n"
                      "Exam dates are usually included in the weekly schedule.",
                inline=False
            )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in exam_schedule: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="help", description="Get help with exam commands")
    async def exam_help(self, interaction: discord.Interaction):
        """Show exam command help"""
        embed = discord.Embed(
            title="📚 Exam Commands Help",
            description="Available commands for exam schedule",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="/exam schedule",
            value="View exam schedule information",
            inline=False
        )

        embed.add_field(
            name="📌 Note",
            value="FAP exam schedules are typically included in your weekly class schedule. "
                  "Use `/schedule week` to see all your scheduled activities including exams.",
            inline=False
        )

        embed.set_footer(text="FAP Discord Bot")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(ExamCommands(bot))
    logger.info("Exam commands loaded")

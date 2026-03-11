"""
Discord Bot Commands - Status
Commands for checking bot status
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class StatusCommands(commands.Cog):
    """Status and health check commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now()
        self.auth_instance = None

    def set_auth(self, auth):
        """Set auth instance for status checking"""
        self.auth_instance = auth

    @app_commands.command(name="status", description="Check bot status")
    async def get_status(self, interaction: discord.Interaction):
        """Show bot health and status"""
        try:
            # Calculate uptime
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)

            # Get FAP username from env
            load_dotenv()
            fap_user = os.getenv('FAP_USERNAME', 'Not configured')

            # Session status
            session_status = "✅ Ready (auto-refresh enabled)"
            if not self.auth_instance:
                session_status = "⚠️ Auth not initialized"
            elif not self.auth_instance.username:
                session_status = "⚠️ FAP credentials not configured"

            embed = discord.Embed(
                title="🤖 FAP Bot Status",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )

            embed.add_field(name="🟢 Status", value="Online", inline=True)
            embed.add_field(name="⏱️ Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
            embed.add_field(name="👤 FAP User", value=f"`{fap_user}`", inline=True)
            embed.add_field(name="🔐 Session", value=session_status, inline=True)
            embed.add_field(name="📊 Servers", value=str(len(self.bot.guilds)), inline=True)
            embed.add_field(name="👥 Users", value=str(sum(g.member_count for g in self.bot.guilds)), inline=True)

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}")

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_command(self, interaction: discord.Interaction):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)
        color = discord.Color.green() if latency < 200 else discord.Color.yellow() if latency < 500 else discord.Color.red()

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{latency}ms**",
            color=color
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(StatusCommands(bot))
    logger.info("Status commands loaded")

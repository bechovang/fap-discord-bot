"""
Discord Bot Commands - Status
Commands for checking bot status
"""
import logging
import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class StatusCommands(commands.Cog):
    """Status and health check commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now()
        self.auth_instance = None

    def set_auth(self, auth):
        """Set auth instance for status checking."""
        self.auth_instance = auth

    @app_commands.command(name="status", description="Check bot status")
    async def get_status(self, interaction: discord.Interaction):
        """Show bot health and status."""
        try:
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)

            load_dotenv()
            fap_user = os.getenv("FAP_USERNAME", "Not configured")

            session_status = "OK"
            session_detail = "No recent auth diagnostic"
            embed_color = discord.Color.green()

            if not self.auth_instance:
                session_status = "Auth not initialized"
                session_detail = "Bot auth instance is not attached"
                embed_color = discord.Color.yellow()
            elif not self.auth_instance.username:
                session_status = "Credentials missing"
                session_detail = "Set FAP_USERNAME and FAP_PASSWORD in the server environment"
                embed_color = discord.Color.yellow()
            else:
                snapshot = self.auth_instance.get_diagnostic_snapshot()
                diag = snapshot["last_diagnostic"]

                if diag["status"] == "error":
                    session_status = "Attention required"
                    embed_color = discord.Color.red()
                elif diag["status"] == "warning":
                    session_status = "Degraded"
                    embed_color = discord.Color.yellow()

                cookies_text = "missing"
                if snapshot["cookies_exist"]:
                    age = snapshot["cookie_age_minutes"]
                    cookies_text = f"present ({age}m old)" if age is not None else "present"

                session_detail = (
                    f"{diag['operation']} / {diag['code']}\n"
                    f"Cookies: {cookies_text} | Auto-refresh: {snapshot['auto_refresh']} | "
                    f"Headless: {snapshot['headless']}"
                )

            embed = discord.Embed(
                title="FAP Bot Status",
                color=embed_color,
                timestamp=datetime.now(),
            )

            embed.add_field(name="Status", value="Online", inline=True)
            embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
            embed.add_field(name="FAP User", value=f"`{fap_user}`", inline=True)
            embed.add_field(name="Session", value=session_status, inline=True)
            embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
            embed.add_field(name="Users", value=str(sum(g.member_count for g in self.bot.guilds)), inline=True)
            embed.add_field(name="Session Detail", value=session_detail[:1024], inline=False)

            # Scheduler info
            scheduler = getattr(self.bot, 'scheduler', None)
            if scheduler and scheduler.scheduler.running:
                now = datetime.now()
                jobs_info = []
                for job in scheduler.scheduler.get_jobs():
                    next_run = job.next_run_time
                    if next_run:
                        delta = next_run.replace(tzinfo=None) - now
                        total_sec = max(0, int(delta.total_seconds()))
                        h, r = divmod(total_sec, 3600)
                        m, s = divmod(r, 60)
                        eta = f"{h}h {m}m" if h > 0 else f"{m}m {s}s"
                    else:
                        eta = "paused"
                    jobs_info.append(f"**{job.name}** — next: {eta}")

                sched_text = "\n".join(jobs_info) if jobs_info else "No jobs"
                embed.add_field(name="Scheduler", value=sched_text, inline=False)
            else:
                embed.add_field(name="Scheduler", value="Not running", inline=False)

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await interaction.response.send_message(f"Error: {str(e)}")

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_command(self, interaction: discord.Interaction):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        color = (
            discord.Color.green()
            if latency < 200
            else discord.Color.yellow()
            if latency < 500
            else discord.Color.red()
        )

        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: **{latency}ms**",
            color=color,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Run daily check now and update dashboard")
    async def daily_command(self, interaction: discord.Interaction):
        """Manually trigger the daily check."""
        await interaction.response.send_message("Running daily check...", ephemeral=True)

        scheduler = getattr(self.bot, 'scheduler', None)
        if not scheduler:
            await interaction.edit_original_response(content="Scheduler not available.")
            return

        try:
            await scheduler._daily_check()
            dashboard_url = os.getenv("DASHBOARD_URL", "")
            msg = "Daily check completed."
            if dashboard_url:
                msg += f"\n📊 Dashboard: {dashboard_url}"
            await interaction.edit_original_response(content=msg)
        except Exception as e:
            logger.error(f"Manual daily check failed: {e}")
            await interaction.edit_original_response(content=f"Daily check failed: {e}")


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(StatusCommands(bot))
    logger.info("Status commands loaded")

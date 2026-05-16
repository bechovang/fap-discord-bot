"""
Discord Bot Commands - Config
Configuration commands for the bot
"""
import discord
from discord import app_commands
from discord.ext import commands
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.notifier import set_channel, get_channel_id, remove_channel
from runtime_config import (
    clear_proxy_url,
    format_proxy_summary,
    get_proxy_url,
    set_proxy_url,
)

logger = logging.getLogger(__name__)


class ConfigCommands(commands.GroupCog, name="config"):
    """Bot configuration commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="channel", description="Set notification channel for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_channel(self, interaction: discord.Interaction):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used in a text channel.", ephemeral=True)
            return

        set_channel(interaction.guild_id, channel.id)

        embed = discord.Embed(
            title="Notification Channel Set",
            description=f"All notifications will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Server", value=interaction.guild.name, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Channel set to #{channel.name} in guild {interaction.guild.name}")

    @app_commands.command(name="status", description="Check current notification settings")
    async def config_status(self, interaction: discord.Interaction):
        channel_id = get_channel_id(interaction.guild_id)
        proxy_url = get_proxy_url() or os.getenv("PROXY_URL")

        embed = discord.Embed(
            title="Bot Configuration",
            color=discord.Color.blue()
        )

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed.add_field(name="Notification Channel", value=channel.mention, inline=True)
            else:
                embed.add_field(name="Notification Channel", value=f"Channel ID {channel_id} (not found)", inline=True)
        else:
            embed.add_field(name="Notification Channel", value="Not configured. Use `/config channel`", inline=False)

        embed.add_field(name="Proxy", value=format_proxy_summary(proxy_url), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unset", description="Remove notification channel for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_unset(self, interaction: discord.Interaction):
        remove_channel(interaction.guild_id)
        await interaction.response.send_message("Notification channel removed.", ephemeral=True)

    @app_commands.command(name="proxy", description="Set runtime proxy for FAP login")
    @app_commands.describe(
        host="Proxy host or IP",
        port="Proxy port",
        username="Proxy username",
        password="Proxy password",
        proxy_type="Provider type label. Use HTTPS if they say HTTPS.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_proxy(
        self,
        interaction: discord.Interaction,
        host: str,
        port: int,
        username: str,
        password: str,
        proxy_type: str = "HTTPS",
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Provider labels like HTTPS still use http:// for the proxy connection.
        proxy_url = f"http://{username}:{password}@{host}:{port}"
        set_proxy_url(proxy_url)

        auth = getattr(self.bot, "auth", None)
        refresh_ok = None
        if auth:
            try:
                await auth.close()
                refresh_ok = await auth.get_session(force_refresh=True, fast_check=False)
            except Exception as exc:
                logger.error(f"Proxy refresh failed after config update: {exc}")
                refresh_ok = False

        embed = discord.Embed(
            title="Runtime Proxy Updated",
            color=discord.Color.green() if refresh_ok is not False else discord.Color.orange(),
        )
        embed.add_field(name="Proxy", value=format_proxy_summary(proxy_url), inline=False)
        embed.add_field(name="Provider Type", value=proxy_type, inline=True)
        embed.add_field(name="Stored As", value="http://", inline=True)

        if refresh_ok is None:
            embed.add_field(name="Session Test", value="Skipped", inline=False)
        elif refresh_ok:
            embed.add_field(name="Session Test", value="Refresh/login succeeded", inline=False)
        else:
            embed.add_field(name="Session Test", value="Refresh/login failed. Check /status and logs.", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"Runtime proxy updated by {interaction.user} in guild {interaction.guild_id}: {host}:{port}")

    @app_commands.command(name="proxy-clear", description="Clear runtime proxy override and fall back to env")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_proxy_clear(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        clear_proxy_url()

        auth = getattr(self.bot, "auth", None)
        if auth:
            await auth.close()

        embed = discord.Embed(
            title="Runtime Proxy Cleared",
            description="Bot will use `PROXY_URL` from the environment on the next session refresh.",
            color=discord.Color.gold(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"Runtime proxy cleared by {interaction.user} in guild {interaction.guild_id}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCommands(bot))
    logger.info("Config commands loaded")

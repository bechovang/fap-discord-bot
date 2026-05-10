"""
Discord Bot Commands - Config
Configuration commands for the bot
"""
import discord
from discord import app_commands
from discord.ext import commands
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.notifier import set_channel, get_channel_id, remove_channel

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

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unset", description="Remove notification channel for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_unset(self, interaction: discord.Interaction):
        remove_channel(interaction.guild_id)
        await interaction.response.send_message("Notification channel removed.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCommands(bot))
    logger.info("Config commands loaded")

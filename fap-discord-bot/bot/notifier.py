"""
Notification helper for sending messages to configured Discord channels
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict
import discord

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("data/channels.json")


def _load_channels() -> Dict[str, int]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Failed to load channels.json, starting fresh")
    return {}


def _save_channels(channels: Dict[str, int]):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=2)


def set_channel(guild_id: int, channel_id: int):
    channels = _load_channels()
    channels[str(guild_id)] = channel_id
    _save_channels(channels)
    logger.info(f"Set notification channel for guild {guild_id}: {channel_id}")


def remove_channel(guild_id: int):
    channels = _load_channels()
    channels.pop(str(guild_id), None)
    _save_channels(channels)


def get_channel_id(guild_id: int) -> Optional[int]:
    channels = _load_channels()
    return channels.get(str(guild_id))


async def send_notification(bot: discord.Client, guild_id: int, embed: discord.Embed) -> bool:
    channel_id = get_channel_id(guild_id)
    if not channel_id:
        logger.debug(f"No channel configured for guild {guild_id}")
        return False

    channel = bot.get_channel(channel_id)
    if not channel:
        logger.warning(f"Channel {channel_id} not found in guild {guild_id}")
        return False

    try:
        await channel.send(embed=embed)
        return True
    except discord.Forbidden:
        logger.error(f"No permission to send in channel {channel_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False


async def send_to_all_guilds(bot: discord.Client, embed: discord.Embed):
    channels = _load_channels()
    for guild_id_str, channel_id in channels.items():
        guild_id = int(guild_id_str)
        await send_notification(bot, guild_id, embed)

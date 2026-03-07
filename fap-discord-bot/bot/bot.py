"""
FAP Discord Bot - Main Entry Point
"""
import discord
from discord.ext import commands
import logging
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.auth import FAPAuth
from bot.commands.schedule import setup as setup_schedule
from bot.commands.status import setup as setup_status, StatusCommands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class FAPBot(commands.Bot):
    """FAP Discord Bot"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            activity=discord.Activity(type=discord.ActivityType.watching, name="your schedule")
        )

        # Auth instance will be created when needed
        self.status_cog: StatusCommands = None

    async def setup_hook(self):
        """Initialize bot components"""
        load_dotenv()

        # Check environment variables
        token = os.getenv('DISCORD_TOKEN')
        if not token or token == 'your_discord_bot_token_here':
            logger.error("DISCORD_TOKEN not configured in .env file!")
            raise ValueError("Missing DISCORD_TOKEN")

        fap_user = os.getenv('FAP_USERNAME')
        fap_pass = os.getenv('FAP_PASSWORD')

        if not fap_user or not fap_pass:
            logger.warning("FAP credentials not configured - some features may not work")

        # Initialize FAP Auth
        self.auth = FAPAuth(
            username=fap_user or '',
            password=fap_pass or '',
            headless=os.getenv('HEADLESS', 'true').lower() == 'true',
            user_agent=os.getenv('USER_AGENT'),
            data_dir='data'
        )

        # Load cogs
        await setup_schedule(self)
        await setup_status(self)

        # Set auth reference in status cog
        self.status_cog = self.get_cog('StatusCommands')
        if self.status_cog:
            self.status_cog.set_auth(self.auth)

        logger.info("Bot setup complete")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

        # Test FAP connection
        if self.auth:
            try:
                page = await self.auth.get_session()
                if page:
                    logger.info("✅ FAP authentication successful")
                else:
                    logger.warning("⚠️ FAP authentication failed - check credentials")
            except Exception as e:
                logger.error(f"❌ FAP connection error: {e}")

    async def on_guild_join(self, guild):
        """Called when bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        else:
            logger.error(f"Command error: {error}")
            await ctx.send(f"❌ An error occurred: {error}")

    async def close(self):
        """Cleanup on shutdown"""
        logger.info("Shutting down...")
        if self.auth:
            await self.auth.close()
        await super().close()


def main():
    """Main entry point"""
    load_dotenv()

    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        return

    bot = FAPBot()

    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        asyncio.run(bot.close())


if __name__ == "__main__":
    main()

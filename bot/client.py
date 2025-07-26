"""Main bot client class."""

import discord
from discord.ext import commands
import asyncio

from utils.logger import setup_logger
from bot.error_handler import setup_error_handler
from services.scheduler import start_scheduler  # ✅ Needed only here

logger = setup_logger("bot_client")

class RowBot(commands.Bot):
    """Custom bot class for the RoW Discord bot."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        intents.guild_reactions = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None  # We'll create a custom help command
        )

        self.scheduler = None  # Optional, only if you use it internally

    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")

        # Setup error handling
        setup_error_handler(self)

        # Load all cogs
        await self._load_cogs()

        # Start custom scheduler
        start_scheduler(self)  # ✅ Correctly triggers scheduler setup

        logger.info("Bot setup complete!")

    async def _load_cogs(self):
        """Load all cogs in the correct order."""
        cog_order = [
            # User cogs first (dependencies for others)
            "cogs.user.profile",

            # Core event management
            "cogs.events.manager",
            "cogs.events.alerts", 
            "cogs.events.results",

            # Admin functionality
            "cogs.admin.actions",
            "cogs.admin.attendance", 
            "cogs.admin.exporter",

            # Interactions
            "cogs.interactions.buttons",
            "cogs.interactions.dropdowns",

            # General user commands
            "cogs.user.commands"
        ]

        for cog in cog_order:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load {cog}: {e}")

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"✅ {self.user} is online!")
        logger.info(f"📊 Serving {len(self.guilds)} guild(s)")

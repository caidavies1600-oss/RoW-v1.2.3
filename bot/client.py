"""Main bot client class."""

import discord
from discord.ext import commands
import asyncio
import sys
import os

from utils.logger import setup_logger
from bot.error_handler import setup_error_handler
from services.scheduler import start_scheduler
from utils.data_manager import DataManager

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

        self.startup_completed = False

    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("🔄 Setting up bot...")

        try:
            # CRITICAL: Run data validation and migration first
            logger.info("🔍 Running critical startup checks...")
            DataManager.run_critical_startup_checks()

            # Setup error handling
            setup_error_handler(self)
            logger.info("✅ Error handling configured")

            # Load all cogs
            await self._load_cogs()

            # Validate bot setup after cogs are loaded
            setup_valid = await self._validate_bot_setup()
            if not setup_valid:
                logger.warning("⚠️ Bot setup validation found issues - check logs above")

            # Start custom scheduler
            start_scheduler(self)
            logger.info("✅ Scheduler started")

            logger.info("✅ Bot setup complete!")

        except Exception as e:
            logger.exception(f"❌ Critical error during bot setup: {e}")
            raise

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

            # Interactions (choose ONE - either buttons OR signup_view)
            "cogs.interactions.buttons",
            # "cogs.events.signup_view",  # Comment out to avoid conflicts

            # General user commands
            "cogs.user.commands"
        ]

        loaded_cogs = []
        failed_cogs = []

        for cog in cog_order:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded {cog}")
                loaded_cogs.append(cog)
            except Exception as e:
                logger.error(f"❌ Failed to load {cog}: {e}")
                failed_cogs.append((cog, str(e)))

        logger.info(f"📊 Cog loading summary: {len(loaded_cogs)} loaded, {len(failed_cogs)} failed")

        if failed_cogs:
            logger.warning("⚠️ Failed cogs:")
            for cog, error in failed_cogs:
                logger.warning(f"  - {cog}: {error}")

        return loaded_cogs, failed_cogs

    async def _validate_bot_setup(self):
        """Validate bot configuration and environment setup."""
        issues = []
        warnings = []

        try:
            # Check required environment variables
            from config.settings import BOT_TOKEN
            if not BOT_TOKEN:
                issues.append("BOT_TOKEN not set in environment")

            # Check channel access
            from config.constants import ALERT_CHANNEL_IDS
            accessible_channels = []
            for channel_id in ALERT_CHANNEL_IDS:
                channel = self.get_channel(channel_id)
                if channel:
                    # Test if we can send messages
                    try:
                        # Don't actually send, just check permissions
                        permissions = channel.permissions_for(channel.guild.me)
                        if permissions.send_messages and permissions.embed_links:
                            accessible_channels.append(f"{channel.guild.name}#{channel.name}")
                        else:
                            warnings.append(f"Limited permissions in channel: {channel.name}")
                    except Exception as e:
                        warnings.append(f"Permission check failed for {channel.name}: {e}")
                else:
                    issues.append(f"Cannot access channel ID: {channel_id}")

            # Check required cogs
            required_cogs = ["EventManager", "Profile"]
            critical_missing = []
            for cog_name in required_cogs:
                if not self.get_cog(cog_name):
                    critical_missing.append(cog_name)

            if critical_missing:
                issues.append(f"Critical cogs not loaded: {', '.join(critical_missing)}")

            # Check optional but important cogs
            optional_cogs = ["Results", "AdminActions", "ButtonCog"]
            missing_optional = []
            for cog_name in optional_cogs:
                if not self.get_cog(cog_name):
                    missing_optional.append(cog_name)

            if missing_optional:
                warnings.append(f"Optional cogs not loaded: {', '.join(missing_optional)}")

            # Final data integrity check
            data_issues = DataManager.validate_data_integrity()
            if data_issues:
                for issue in data_issues:
                    warnings.append(f"Data integrity: {issue}")

            # Report validation results
            if issues:
                logger.error("❌ Critical bot setup issues found:")
                for issue in issues:
                    logger.error(f"  - {issue}")

            if warnings:
                logger.warning("⚠️ Bot setup warnings:")
                for warning in warnings:
                    logger.warning(f"  - {warning}")

            if not issues and not warnings:
                logger.info("✅ Bot setup validation passed completely")
            elif not issues:
                logger.info("✅ Bot setup validation passed (with warnings)")

            if accessible_channels:
                logger.info(f"✅ Can access channels: {', '.join(accessible_channels)}")

            return len(issues) == 0

        except Exception as e:
            logger.exception(f"❌ Error during bot setup validation: {e}")
            return False

    async def on_ready(self):
        """Called when the bot is ready."""
        if not self.startup_completed:
            logger.info(f"✅ {self.user} is online!")
            logger.info(f"📊 Serving {len(self.guilds)} guild(s)")

            # Final health check
            await self._final_health_check()

            self.startup_completed = True
        else:
            logger.info(f"🔄 {self.user} reconnected")

    async def _final_health_check(self):
        """Final health check after bot is fully ready."""
        try:
            logger.info("🔍 Running final health check...")

            # Test basic functionality
            health_status = {
                "guilds": len(self.guilds),
                "channels_accessible": 0,
                "cogs_loaded": len(self.cogs),
                "commands_available": len(self.commands)
            }

            # Count accessible channels
            from config.constants import ALERT_CHANNEL_IDS
            for channel_id in ALERT_CHANNEL_IDS:
                if self.get_channel(channel_id):
                    health_status["channels_accessible"] += 1

            logger.info("📊 Final Health Status:")
            for key, value in health_status.items():
                logger.info(f"  - {key}: {value}")

            # Test critical cogs
            event_manager = self.get_cog("EventManager")
            if event_manager:
                logger.info("✅ EventManager cog is functional")
            else:
                logger.error("❌ EventManager cog not available")

            profile_cog = self.get_cog("Profile")
            if profile_cog:
                logger.info("✅ Profile cog is functional")
            else:
                logger.error("❌ Profile cog not available")

            logger.info("✅ Final health check completed")

        except Exception as e:
            logger.exception(f"❌ Error during final health check: {e}")

    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("🛑 Shutting down bot...")

        try:
            # Stop scheduler tasks
            from services.scheduler import stop_scheduler
            stop_scheduler()
            logger.info("✅ Scheduler stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping scheduler: {e}")

        try:
            # Create final backup
            backup_dir = DataManager.backup_data_files()
            if backup_dir:
                logger.info(f"✅ Final backup created: {backup_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Error creating final backup: {e}")

        await super().close()
        logger.info("✅ Bot shutdown complete")
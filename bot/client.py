"""Main bot client class."""

import os
import sys
import asyncio
import discord
from discord.ext import commands

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
            logger.info("🔍 Running critical startup checks...")
            DataManager.run_critical_startup_checks()

            setup_error_handler(self)
            logger.info("✅ Error handling configured")

            await self._load_cogs()

            setup_valid = await self._validate_bot_setup()
            if not setup_valid:
                logger.warning("⚠️ Bot setup validation found issues - check logs above")

            start_scheduler(self)
            logger.info("✅ Scheduler started")

            logger.info("✅ Bot setup complete!")

        except Exception as e:
            logger.exception(f"❌ Critical error during bot setup: {e}")
            raise

    async def _load_cogs(self):
        """Load all cogs in the correct order."""
        cog_order = [
            "cogs.user.profile",
            "cogs.events.manager",
            "cogs.events.alerts",
            "cogs.events.results",
            "cogs.admin.actions",
            "cogs.admin.attendance",
            "cogs.admin.exporter",
            "cogs.admin.owner_actions",
            "cogs.interactions.buttons",
            "cogs.interactions.dropdowns",
            # "cogs.events.signup_view",  # Comment out to avoid conflicts
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
            from config.settings import BOT_TOKEN
            if not BOT_TOKEN:
                issues.append("BOT_TOKEN not set in environment")

            from config.constants import ALERT_CHANNEL_ID
            # Handle both single channel ID and list of channel IDs
            channel_ids = [ALERT_CHANNEL_ID] if isinstance(ALERT_CHANNEL_ID, int) else ALERT_CHANNEL_ID
            accessible_channels = []

            for channel_id in channel_ids:
                channel = self.get_channel(channel_id)
                if channel:
                    try:
                        permissions = channel.permissions_for(channel.guild.me)
                        if permissions.send_messages and permissions.embed_links:
                            accessible_channels.append(f"{channel.guild.name}#{channel.name}")
                        else:
                            warnings.append(f"Limited permissions in channel: {channel.name}")
                    except Exception as e:
                        warnings.append(f"Permission check failed for {channel.name}: {e}")
                else:
                    issues.append(f"Cannot access channel ID: {channel_id}")

            required_cogs = ["EventManager", "Profile"]
            critical_missing = [c for c in required_cogs if not self.get_cog(c)]

            if critical_missing:
                issues.append(f"Critical cogs not loaded: {', '.join(critical_missing)}")

            optional_cogs = ["Results", "AdminActions", "ButtonCog", "OwnerActions"]
            missing_optional = [c for c in optional_cogs if not self.get_cog(c)]

            if missing_optional:
                warnings.append(f"Optional cogs not loaded: {', '.join(missing_optional)}")

            # Check if DataManager has validate_data_integrity method
            if hasattr(DataManager, 'validate_data_integrity'):
                data_issues = DataManager.validate_data_integrity()
                for issue in data_issues:
                    warnings.append(f"Data integrity: {issue}")

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

            await self._final_health_check()
            self.startup_completed = True
        else:
            logger.info(f"🔄 {self.user} reconnected")

    async def _final_health_check(self):
        """Final health check after bot is fully ready."""
        try:
            logger.info("🔍 Running final health check...")

            health_status = {
                "guilds": len(self.guilds),
                "channels_accessible": 0,
                "cogs_loaded": len(self.cogs),
                "commands_available": len(self.commands)
            }

            from config.constants import ALERT_CHANNEL_ID
            # Handle both single channel ID and list of channel IDs
            channel_ids = [ALERT_CHANNEL_ID] if isinstance(ALERT_CHANNEL_ID, int) else ALERT_CHANNEL_ID
            for channel_id in channel_ids:
                if self.get_channel(channel_id):
                    health_status["channels_accessible"] += 1

            logger.info("📊 Final Health Status:")
            for key, value in health_status.items():
                logger.info(f"  - {key}: {value}")

            if self.get_cog("EventManager"):
                logger.info("✅ EventManager cog is functional")
            else:
                logger.error("❌ EventManager cog not available")

            if self.get_cog("Profile"):
                logger.info("✅ Profile cog is functional")
            else:
                logger.error("❌ Profile cog not available")

            if self.get_cog("OwnerActions"):
                logger.info("✅ OwnerActions cog is functional")
            else:
                logger.warning("⚠️ OwnerActions cog not available")

            logger.info("✅ Final health check completed")

        except Exception as e:
            logger.exception(f"❌ Error during final health check: {e}")

    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("🛑 Shutting down bot...")

        try:
            # Check if stop_scheduler function exists
            try:
                from services.scheduler import stop_scheduler
                stop_scheduler()
                logger.info("✅ Scheduler stopped")
            except ImportError:
                logger.info("ℹ️ No stop_scheduler function available")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping scheduler: {e}")

        try:
            # Check if DataManager has backup_data_files method
            if hasattr(DataManager, 'backup_data_files'):
                backup_dir = DataManager.backup_data_files()
                if backup_dir:
                    logger.info(f"✅ Final backup created: {backup_dir}")
            else:
                logger.info("ℹ️ No backup function available")
        except Exception as e:
            logger.warning(f"⚠️ Error creating final backup: {e}")

        await super().close()
        logger.info("✅ Bot shutdown complete")
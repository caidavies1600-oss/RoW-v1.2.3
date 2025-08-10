# bot/client.py - Main bot client class
import os
import sys
import asyncio
import discord
from discord.ext import commands

print("DEBUG: Starting bot/client.py imports...")

try:
    from utils.logger import setup_logger
    print("DEBUG: utils.logger imported")
except Exception as e:
    print(f"DEBUG: utils.logger failed: {e}")

try:
    from bot.error_handler import setup_error_handler
    print("DEBUG: bot.error_handler imported")
except Exception as e:
    print(f"DEBUG: bot.error_handler failed: {e}")

try:
    from services.scheduler import start_scheduler
    print("DEBUG: services.scheduler imported")
except Exception as e:
    print(f"DEBUG: services.scheduler failed: {e}")
    start_scheduler = None

try:
    from services.sheets_manager import SheetsManager
    print("DEBUG: services.sheets_manager imported")
except Exception as e:
    print(f"DEBUG: services.sheets_manager failed: {e}")
    SheetsManager = None

logger = setup_logger("bot_client")


class RowBot(commands.Bot):
    def __init__(self):
        print("DEBUG: Initializing RowBot...")

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        intents.guild_reactions = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.startup_completed = False
        self.sheets = None  # Will be assigned in setup_hook
        print("DEBUG: RowBot initialization complete")

    async def setup_hook(self):
        """Called when the bot is starting up."""
        print("DEBUG: setup_hook() called")
        logger.info("Setting up bot...")

        try:
            print("DEBUG: Setting up error handler...")
            setup_error_handler(self)
            logger.info("Error handling configured")

            print("DEBUG: Running critical startup checks...")
            self._run_critical_startup_checks()
            logger.info("Critical startup checks completed")

            # Initialize Google Sheets integration
            if SheetsManager:
                print("DEBUG: Initializing SheetsManager...")
                self.sheets = SheetsManager()
                logger.info("SheetsManager initialized")
            else:
                logger.warning("SheetsManager not available")

            print("DEBUG: Loading cogs...")
            await self._load_cogs()

            print("DEBUG: Starting scheduler...")
            if start_scheduler:
                start_scheduler(self)
                logger.info("Scheduler started")
            else:
                logger.warning("Scheduler not available - continuing without it")
                print("DEBUG: Scheduler not available - continuing without it")

            logger.info("Bot setup complete!")
            print("DEBUG: setup_hook() completed successfully")

        except Exception as e:
            print(f"DEBUG: Critical error during bot setup: {e}")
            logger.exception(f"Critical error during bot setup: {e}")
            raise

    def _run_critical_startup_checks(self):
        """Run critical startup checks to ensure bot can function."""
        print("DEBUG: Running critical startup checks...")

        if not os.path.exists("data"):
            print("DEBUG: Creating data directory...")
            os.makedirs("data", exist_ok=True)
            logger.info("Created data directory")

        try:
            from config.constants import FILES, ALERT_CHANNEL_ID
            from config.settings import BOT_TOKEN

            if not BOT_TOKEN:
                raise Exception("BOT_TOKEN not configured")

            if not ALERT_CHANNEL_ID:
                logger.warning("ALERT_CHANNEL_ID not configured")

            logger.info("✅ Configuration checks passed")

        except ImportError as e:
            logger.error(f"❌ Failed to import configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Configuration error: {e}")
            raise

    async def _load_cogs(self):
        """Load all bot cogs in the correct order."""
        print("DEBUG: _load_cogs() called")

        cog_order = [
            "cogs.user.profile",
            "cogs.events.manager",
            "cogs.events.results",
            "cogs.admin.actions",
            "cogs.admin.attendance",
            "cogs.admin.exporter",
            "cogs.admin.owner_actions",
            "cogs.admin.sheet_formatter",
            "cogs.interactions.buttons",
            "cogs.interactions.dropdowns",
            "cogs.user.commands",
            "services.smart_notifications",
        ]

        print(f"DEBUG: Attempting to load {len(cog_order)} cogs...")
        loaded_cogs = []
        failed_cogs = []

        for cog in cog_order:
            print(f"DEBUG: Loading {cog}...")
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded {cog}")
                print(f"DEBUG: Successfully loaded {cog}")
                loaded_cogs.append(cog)
            except Exception as e:
                logger.error(f"❌ Failed to load {cog}: {e}")
                print(f"DEBUG: Failed to load {cog}: {e}")
                import traceback
                traceback.print_exc()
                failed_cogs.append((cog, str(e)))

        logger.info(f"Cog loading summary: {len(loaded_cogs)} loaded, {len(failed_cogs)} failed")
        print(f"DEBUG: Cog loading complete - {len(loaded_cogs)} loaded, {len(failed_cogs)} failed")

        if failed_cogs:
            logger.warning("Failed cogs:")
            print("DEBUG: Failed cogs:")
            for cog, error in failed_cogs:
                logger.warning(f"  - {cog}: {error}")
                print(f"DEBUG:   - {cog}: {error}")

        if len(loaded_cogs) == 0:
            raise Exception("No cogs loaded successfully - bot cannot function")

        return loaded_cogs, failed_cogs

    async def on_ready(self):
        """Called when the bot is connected and ready."""
        print("DEBUG: on_ready() called")

        if not self.startup_completed:
            logger.info(f"🤖 {self.user} is online!")
            print(f"DEBUG: Bot {self.user} is online!")
            logger.info(f"🌐 Serving {len(self.guilds)} guild(s)")
            print(f"DEBUG: Serving {len(self.guilds)} guild(s)")

            for guild in self.guilds:
                logger.info(f"  📍 {guild.name} (ID: {guild.id}, {guild.member_count} members)")

            await self._final_health_check()
            self.startup_completed = True
        else:
            logger.info(f"🔄 {self.user} reconnected")
            print(f"DEBUG: Bot {self.user} reconnected")

    async def _final_health_check(self):
        """Run final health checks after bot is ready."""
        print("DEBUG: _final_health_check() called")
        try:
            logger.info("🏥 Running final health check...")

            health_status = {
                "guilds": len(self.guilds),
                "cogs_loaded": len(self.cogs),
                "commands_available": len(self.commands)
            }

            logger.info("📊 Bot Health Status:")
            for key, value in health_status.items():
                logger.info(f"  ✅ {key}: {value}")
                print(f"DEBUG: Health - {key}: {value}")

            print(f"DEBUG: Available commands: {[cmd.name for cmd in self.commands]}")
            print(f"DEBUG: Loaded cogs: {list(self.cogs.keys())}")

            critical_cogs = {
                "EventManager": "Event signup and management",
                "Profile": "IGN management", 
                "Results": "Win/loss tracking"
            }

            for cog_name, description in critical_cogs.items():
                if self.get_cog(cog_name):
                    logger.info(f"✅ {cog_name} cog is functional ({description})")
                    print(f"DEBUG: {cog_name} cog found")
                else:
                    logger.error(f"❌ {cog_name} cog not available ({description})")
                    print(f"DEBUG: {cog_name} cog NOT found")

            try:
                from config.constants import ALERT_CHANNEL_ID
                channel = self.get_channel(ALERT_CHANNEL_ID)
                if channel:
                    logger.info(f"📡 Alert channel accessible: #{channel.name} in {channel.guild.name}")
                    print(f"DEBUG: Alert channel found: #{channel.name}")
                else:
                    logger.error(f"❌ Alert channel not accessible (ID: {ALERT_CHANNEL_ID})")
                    print(f"DEBUG: Alert channel NOT found (ID: {ALERT_CHANNEL_ID})")
            except ImportError:
                logger.warning("ALERT_CHANNEL_ID not configured")

            logger.info("✅ Final health check completed")
            print("DEBUG: Final health check completed")

        except Exception as e:
            logger.exception(f"❌ Error during final health check: {e}")
            print(f"DEBUG: Error during final health check: {e}")

    async def on_guild_join(self, guild):
        logger.info(f"📥 Joined new guild: {guild.name} (ID: {guild.id}, {guild.member_count} members)")

    async def on_guild_remove(self, guild):
        logger.info(f"📤 Left guild: {guild.name} (ID: {guild.id})")

    async def on_command(self, ctx):
        logger.debug(f"📝 Command executed: {ctx.command.name} by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}")

    async def on_command_error(self, ctx, error):
        logger.error(f"💥 Command error in {ctx.command}: {error}")

    async def close(self):
        print("DEBUG: close() called")
        logger.info("🛑 Shutting down bot...")

        try:
            from services.scheduler import post_event_signup, post_weekly_summary
            if hasattr(post_event_signup, 'cancel'):
                post_event_signup.cancel()
            if hasattr(post_weekly_summary, 'cancel'):
                post_weekly_summary.cancel()
            logger.info("📅 Scheduler tasks cancelled")
        except:
            pass

        await super().close()
        logger.info("✅ Bot shutdown complete")
        print("DEBUG: Bot shutdown complete")

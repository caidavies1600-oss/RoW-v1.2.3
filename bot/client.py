# bot/client.py - MINIMAL CHANGES VERSION

import os
import sys
import asyncio
import discord
import time
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
    from utils.data_manager import DataManager
    print("DEBUG: utils.data_manager imported")
except Exception as e:
    print(f"DEBUG: utils.data_manager failed: {e}")

# Import monitoring systems
try:
    from utils.admin_notifier import (
        setup_admin_notifier, notify_startup_begin, notify_startup_milestone,
        notify_startup_complete, notify_error, notify_activity
    )
    from utils.automatic_monitor import setup_automatic_monitoring
    from config.constants import BOT_ADMIN_USER_ID
    print("DEBUG: monitoring systems imported")
    MONITORING_AVAILABLE = True
except Exception as e:
    print(f"DEBUG: monitoring systems failed: {e}")
    # Create dummy functions if monitoring fails
    setup_admin_notifier = lambda *args: None
    notify_startup_begin = lambda: asyncio.sleep(0)
    notify_startup_milestone = lambda *args, **kwargs: asyncio.sleep(0)
    notify_startup_complete = lambda *args, **kwargs: asyncio.sleep(0)
    notify_error = lambda *args, **kwargs: asyncio.sleep(0)
    notify_activity = lambda *args, **kwargs: asyncio.sleep(0)
    setup_automatic_monitoring = lambda *args: None
    MONITORING_AVAILABLE = False

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
        self.startup_time = time.time()
        print("DEBUG: RowBot initialization complete")

    async def setup_hook(self):
        print("DEBUG: setup_hook() called")
        logger.info("Setting up bot...")

        # Setup monitoring systems
        if MONITORING_AVAILABLE:
            try:
                setup_admin_notifier(self, BOT_ADMIN_USER_ID)
                setup_automatic_monitoring(self)  # 🔔 AUTO-MONITOR ALL COMMANDS
                await notify_startup_begin()
                await notify_startup_milestone("Monitoring systems initialized")
            except Exception as e:
                logger.error(f"Failed to setup monitoring: {e}")

        try:
            print("DEBUG: Running startup data fixes...")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Data consistency fixes...", "🔄")

            # 🔧 AUTOMATIC DATA FIXING ON STARTUP
            from utils.startup_data_fixer import run_startup_data_fixes
            fix_success = run_startup_data_fixes(self)
            if fix_success:
                logger.info("✅ Startup data fixes completed successfully")
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("Data fixes completed")
            else:
                logger.warning("⚠️ Some startup data fixes failed, but continuing...")
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("Data fixes completed with warnings", "⚠️")

            print("DEBUG: Setting up error handler...")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Configuring error handling...", "🔄")
            setup_error_handler(self)
            logger.info("Error handling configured")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Error handling configured")

            print("DEBUG: Loading cogs...")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Loading bot modules...", "🔄")
            loaded_cogs, failed_cogs = await self._load_cogs()

            if failed_cogs:
                details = f"Loaded: {len(loaded_cogs)}, Failed: {len(failed_cogs)}\nFailed cogs: {', '.join([c[0] for c in failed_cogs])}"
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone(f"Cogs loaded with {len(failed_cogs)} failures", "⚠️", details)
            else:
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone(f"All {len(loaded_cogs)} cogs loaded successfully")

            print("DEBUG: Starting scheduler...")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Starting background tasks...", "🔄")
            if start_scheduler:
                start_scheduler(self)
                logger.info("Scheduler started")
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("Background scheduler started")
            else:
                logger.warning("Scheduler not available - continuing without it")
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("Scheduler unavailable", "⚠️", "Background tasks disabled")

            print("DEBUG: Initializing Google Sheets...")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Initializing Google Sheets...", "📊")
            
            # Initialize DataManager
            print("DEBUG: Initializing DataManager...")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Initializing data manager...", "💾")
            try:
                self.data_manager = DataManager()
                logger.info("✅ DataManager initialized successfully")
                print("DEBUG: DataManager initialized successfully")
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("DataManager initialized")
            except Exception as e:
                logger.error(f"❌ Error initializing DataManager: {e}")
                print(f"DEBUG: DataManager initialization error: {e}")
                import traceback
                print(f"DEBUG: DataManager traceback: {traceback.format_exc()}")
                self.data_manager = None
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("DataManager initialization error", "❌", str(e))

            # Initialize Google Sheets if credentials are available
            try:
                creds_env = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
                sheets_id_env = os.getenv('GOOGLE_SHEETS_ID')
                
                print(f"DEBUG: Checking Google Sheets environment variables...")
                print(f"DEBUG: GOOGLE_SHEETS_CREDENTIALS: {'Found' if creds_env else 'Missing'}")
                print(f"DEBUG: GOOGLE_SHEETS_ID: {'Found' if sheets_id_env else 'Missing'}")
                
                if creds_env and sheets_id_env:
                    print("DEBUG: Both environment variables found, initializing SheetsManager...")
                    from sheets import SheetsManager
                    
                    self.sheets = SheetsManager()
                    print(f"DEBUG: SheetsManager created, connected: {self.sheets.is_connected()}")
                    
                    if self.sheets.is_connected() and self.sheets.spreadsheet:
                        logger.info(f"✅ Google Sheets connected: {self.sheets.spreadsheet.url}")
                        print(f"DEBUG: Google Sheets connected successfully")
                        if MONITORING_AVAILABLE:
                            await notify_startup_milestone("Google Sheets connected")
                    else:
                        logger.warning("⚠️ Google Sheets credentials found but connection failed")
                        print(f"DEBUG: Google Sheets connection failed")
                        self.sheets = None
                        if MONITORING_AVAILABLE:
                            await notify_startup_milestone("Google Sheets connection failed", "⚠️")
                else:
                    logger.info("ℹ️ Google Sheets credentials not configured")
                    print(f"DEBUG: Google Sheets credentials not configured")
                    self.sheets = None
                    if MONITORING_AVAILABLE:
                        await notify_startup_milestone("Google Sheets not configured", "ℹ️")
                        
            except Exception as e:
                logger.error(f"❌ Error initializing Google Sheets: {e}")
                print(f"DEBUG: Google Sheets initialization error: {e}")
                import traceback
                print(f"DEBUG: Google Sheets traceback: {traceback.format_exc()}")
                self.sheets = None
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone("Google Sheets initialization error", "❌", str(e))

            logger.info("Bot setup complete!")
            if MONITORING_AVAILABLE:
                await notify_startup_milestone("Setup complete!")
            print("DEBUG: setup_hook() completed successfully")

        except Exception as e:
            print(f"DEBUG: Critical error during bot setup: {e}")
            logger.exception(f"Critical error during bot setup: {e}")
            if MONITORING_AVAILABLE:
                await notify_error("Setup Error", e, "Critical error during bot setup")
            raise

    async def _load_cogs(self):
        print("DEBUG: _load_cogs() called")

        cog_order = [
    "cogs.user.profile",
    "cogs.user.commands",
    "cogs.events.manager",
    "cogs.events.results",
    "cogs.admin.actions",
    "cogs.admin.attendance",
    "cogs.admin.exporter",
    "cogs.admin.owner_actions",
    "cogs.admin.sheets_test",
    "cogs.admin.sheet_formatter",
    "cogs.interactions.buttons",
    "cogs.interactions.dropdowns",
    "services.smart_notifications",
    "utils.health_monitor",
    "cogs.interactions.mention_handler"
]

        print(f"DEBUG: Attempting to load {len(cog_order)} cogs...")
        loaded_cogs = []
        failed_cogs = []

        for cog in cog_order:
            print(f"DEBUG: Loading {cog}...")
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded {cog}")
                print(f"DEBUG: Successfully loaded {cog}")
                loaded_cogs.append(cog)
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")
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

        return loaded_cogs, failed_cogs

    async def on_ready(self):
        print("DEBUG: on_ready() called")
        if not self.startup_completed:
            total_startup_time = time.time() - self.startup_time

            logger.info(f"{self.user} is online!")
            print(f"DEBUG: Bot {self.user} is online!")
            logger.info(f"Serving {len(self.guilds)} guild(s)")
            print(f"DEBUG: Serving {len(self.guilds)} guild(s)")

            health_stats = await self._final_health_check()

            # Send startup complete notification
            if MONITORING_AVAILABLE:
                stats = {
                    "guilds": len(self.guilds),
                    "cogs": len(self.cogs),
                    "commands": len(self.commands),
                    **health_stats
                }

                await notify_startup_complete(True, total_startup_time, stats)

                # Send activity notification
                await notify_activity(
                    "bot_online",
                    status="Online and ready",
                    guilds=len(self.guilds),
                    startup_time=f"{total_startup_time:.2f}s"
                )

            self.startup_completed = True
        else:
            logger.info(f"{self.user} reconnected")
            print(f"DEBUG: Bot {self.user} reconnected")

            # Notify reconnection
            if MONITORING_AVAILABLE:
                await notify_activity("bot_reconnected", status="Reconnected to Discord")

    async def _final_health_check(self):
        print("DEBUG: _final_health_check() called")
        try:
            logger.info("Running final health check...")

            health_status = {
                "guilds": len(self.guilds),
                "cogs_loaded": len(self.cogs),
                "commands_available": len(self.commands),
                "data_fixes": 0
            }

            logger.info("Final Health Status:")
            for key, value in health_status.items():
                logger.info(f"  - {key}: {value}")
                print(f"DEBUG: Health - {key}: {value}")

            print(f"DEBUG: Available commands: {[cmd.name for cmd in self.commands]}")
            print(f"DEBUG: Loaded cogs: {list(self.cogs.keys())}")

            # Check critical cogs
            critical_cogs = ["EventManager", "Profile"]
            missing_critical = []

            for cog_name in critical_cogs:
                if self.get_cog(cog_name):
                    logger.info(f"{cog_name} cog is functional")
                    print(f"DEBUG: {cog_name} cog found")
                else:
                    logger.error(f"{cog_name} cog not available")
                    print(f"DEBUG: {cog_name} cog NOT found")
                    missing_critical.append(cog_name)

            if missing_critical and MONITORING_AVAILABLE:
                health_status["missing_critical_cogs"] = missing_critical
                await notify_error(
                    "Missing Critical Cogs",
                    Exception(f"Critical cogs not loaded: {', '.join(missing_critical)}"),
                    "Some essential bot functionality may not work"
                )

            logger.info("Final health check completed")
            print("DEBUG: Final health check completed")

            return health_status

        except Exception as e:
            logger.exception(f"Error during final health check: {e}")
            print(f"DEBUG: Error during final health check: {e}")
            if MONITORING_AVAILABLE:
                await notify_error("Health Check Error", e, "Error during bot health check")
            return {"error": str(e)}

    async def close(self):
        print("DEBUG: close() called")
        logger.info("Shutting down bot...")

        # Notify admin of shutdown
        if MONITORING_AVAILABLE:
            try:
                await notify_activity("bot_shutdown", status="Bot is shutting down")
            except:
                pass  # Don't let notification failure prevent shutdown

        await super().close()
        logger.info("Bot shutdown complete")
        print("DEBUG: Bot shutdown complete")
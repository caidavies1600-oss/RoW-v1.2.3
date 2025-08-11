# bot/client.py - MINIMAL CHANGES VERSION

import asyncio
import os
import time

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
    from utils.data_manager import DataManager

    print("DEBUG: utils.data_manager imported")
except Exception as e:
    print(f"DEBUG: utils.data_manager failed: {e}")

# Import monitoring systems
try:
    from config.constants import BOT_ADMIN_USER_ID
    from utils.admin_notifier import (
        notify_activity,
        notify_error,
        notify_startup_begin,
        notify_startup_complete,
        notify_startup_milestone,
        setup_admin_notifier,
    )
    from utils.automatic_monitor import setup_automatic_monitoring

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

# Error logging setup
try:
    from services.error_logger import setup_error_logger

    ERROR_LOGGING_AVAILABLE = True
except ImportError:
    ERROR_LOGGING_AVAILABLE = False

logger = setup_logger("bot_client")


class RowBot(commands.Bot):
    """
    Custom Discord bot implementation for managing RoW events and teams.
    Handles user profiles, event management, and administrative functions.
    Includes monitoring, Google Sheets integration, and automatic data fixes.
    """

    def __init__(self):
        """Initialize the RowBot with required intents and configuration."""
        print("DEBUG: Initializing RowBot...")

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        intents.guild_reactions = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.startup_completed = False
        self.startup_time = time.time()
        print("DEBUG: RowBot initialization complete")

        # Error logger initialization
        if ERROR_LOGGING_AVAILABLE:
            setup_error_logger(self)
            logger.info("✅ Enhanced error logging initialized")

    async def setup_hook(self):
        """
        Initializes bot systems and loads required components.

        Handles:
        - Monitoring system setup
        - Data consistency fixes
        - Error handler configuration
        - Cog loading
        - Scheduler initialization
        - Google Sheets integration
        - DataManager initialization

        Raises:
            Exception: If critical initialization steps fail
        """
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
                    await notify_startup_milestone(
                        "Data fixes completed with warnings", "⚠️"
                    )

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
                    await notify_startup_milestone(
                        f"Cogs loaded with {len(failed_cogs)} failures", "⚠️", details
                    )
            else:
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone(
                        f"All {len(loaded_cogs)} cogs loaded successfully"
                    )

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
                    await notify_startup_milestone(
                        "Scheduler unavailable", "⚠️", "Background tasks disabled"
                    )

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
                    await notify_startup_milestone(
                        "DataManager initialization error", "❌", str(e)
                    )

            # Initialize Google Sheets if credentials are available
            try:
                creds_env = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
                sheets_id_env = os.getenv("GOOGLE_SHEETS_ID")

                print("DEBUG: Checking Google Sheets environment variables...")
                print(
                    f"DEBUG: GOOGLE_SHEETS_CREDENTIALS: {'Found' if creds_env else 'Missing'}"
                )
                print(
                    f"DEBUG: GOOGLE_SHEETS_ID: {'Found' if sheets_id_env else 'Missing'}"
                )

                if creds_env and sheets_id_env:
                    print(
                        "DEBUG: Both environment variables found, initializing SheetsManager..."
                    )
                    from utils.sheets_manager import SheetsManager

                    self.sheets = SheetsManager(sheets_id_env)
                    print(
                        f"DEBUG: SheetsManager created, connected: {self.sheets.is_connected()}"
                    )

                    if self.sheets.is_connected() and self.sheets.spreadsheet:
                        logger.info(
                            f"✅ Google Sheets connected: {self.sheets.spreadsheet.url}"
                        )
                        print("DEBUG: Google Sheets connected successfully")
                        if MONITORING_AVAILABLE:
                            await notify_startup_milestone("Google Sheets connected")
                    else:
                        logger.warning(
                            "⚠️ Google Sheets credentials found but connection failed"
                        )
                        print("DEBUG: Google Sheets connection failed")
                        self.sheets = None
                        if MONITORING_AVAILABLE:
                            await notify_startup_milestone(
                                "Google Sheets connection failed", "⚠️"
                            )
                else:
                    logger.info("ℹ️ Google Sheets credentials not configured")
                    print("DEBUG: Google Sheets credentials not configured")
                    self.sheets = None
                    if MONITORING_AVAILABLE:
                        await notify_startup_milestone(
                            "Google Sheets not configured", "ℹ️"
                        )

            except Exception as e:
                logger.error(f"❌ Error initializing Google Sheets: {e}")
                print(f"DEBUG: Google Sheets initialization error: {e}")
                import traceback

                print(f"DEBUG: Google Sheets traceback: {traceback.format_exc()}")
                self.sheets = None
                if MONITORING_AVAILABLE:
                    await notify_startup_milestone(
                        "Google Sheets initialization error", "❌", str(e)
                    )

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
        """
        Load cogs in proper dependency order to avoid failures.

        Returns:
            tuple: (loaded_cogs, failed_cogs) where:
                - loaded_cogs (list): Names of successfully loaded cogs
                - failed_cogs (list): Tuples of (cog_name, error_message)
        """
        print("DEBUG: _load_cogs() called")

        # TIER 1: Foundation cogs (no dependencies)
        tier_1_cogs = [
            "utils.health_monitor",  # Health monitoring - no dependencies
            "cogs.user.profile",  # IGN management - needed by most others
            "cogs.user.commands",  # Basic user commands - minimal dependencies
        ]

        # TIER 2: Core functionality (depends on Tier 1)
        tier_2_cogs = [
            "cogs.events.manager",  # Event system - needs profile for IGNs
            "cogs.admin.actions",  # Basic admin commands - standalone
            "cogs.admin.attendance",  # Attendance tracking - needs admin roles
            "cogs.admin.exporter",  # Data export - needs events data
        ]

        # TIER 3: Extended functionality (depends on Tier 1 & 2)
        tier_3_cogs = [
            "cogs.events.results",  # Win/loss tracking - needs manager
            "services.smart_notifications",  # Notification system - needs events
            "cogs.interactions.buttons",  # UI buttons - needs event manager
            "cogs.interactions.dropdowns",  # UI dropdowns - needs event manager
            "cogs.interactions.mention_handler",  # Mention handler - needs event manager
        ]

        # TIER 4: Advanced features (depends on previous tiers)
        tier_4_cogs = [
            "cogs.admin.owner_actions",  # Owner commands - needs all data systems
            "cogs.admin.sheets_test",  # Google Sheets testing - optional
        ]

        # TIER 5: Optional/experimental (can fail without breaking core)
        tier_5_cogs = [
            "cogs.admin.sheet_formatter",  # Sheets formatting - optional
        ]

        # Load all tiers in order
        all_tiers = [
            ("Foundation", tier_1_cogs),
            ("Core Functionality", tier_2_cogs),
            ("Extended Features", tier_3_cogs),
            ("Advanced Features", tier_4_cogs),
            ("Optional Features", tier_5_cogs),
        ]

        loaded_cogs = []
        failed_cogs = []

        for tier_name, cogs in all_tiers:
            print(f"DEBUG: Loading {tier_name} cogs...")
            logger.info(f"Loading {tier_name} cogs ({len(cogs)} cogs)")

            tier_loaded = 0
            tier_failed = 0

            for cog in cogs:
                print(f"DEBUG: Loading {cog}...")
                try:
                    await self.load_extension(cog)
                    logger.info(f"✅ Loaded {cog}")
                    print(f"DEBUG: Successfully loaded {cog}")
                    loaded_cogs.append(cog)
                    tier_loaded += 1

                    # Small delay between cogs to prevent rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"❌ Failed to load {cog}: {e}")
                    print(f"DEBUG: Failed to load {cog}: {e}")

                    # For debugging, print full traceback
                    import traceback

                    traceback.print_exc()

                    failed_cogs.append((cog, str(e)))
                    tier_failed += 1

                    # Critical cogs that should stop loading if they fail
                    critical_cogs = [
                        "cogs.user.profile",
                        "cogs.events.manager",
                        "cogs.admin.actions",
                    ]

                    if cog in critical_cogs:
                        logger.critical(
                            f"🚨 Critical cog {cog} failed to load! Bot may not function properly."
                        )
                        print(f"DEBUG: CRITICAL COG FAILURE: {cog}")

            logger.info(f"✅ {tier_name}: {tier_loaded} loaded, {tier_failed} failed")
            print(
                f"DEBUG: {tier_name} complete - {tier_loaded} loaded, {tier_failed} failed"
            )

            # If all foundation cogs fail, stop loading
            if tier_name == "Foundation" and tier_loaded == 0:
                logger.critical("🚨 No foundation cogs loaded! Stopping cog loading.")
                print("DEBUG: CRITICAL: No foundation cogs loaded!")
                break

        # Final summary
        total_attempted = sum(len(cogs) for _, cogs in all_tiers)
        success_rate = (
            (len(loaded_cogs) / total_attempted * 100) if total_attempted > 0 else 0
        )

        logger.info(
            f"📊 Cog loading summary: {len(loaded_cogs)}/{total_attempted} loaded ({success_rate:.1f}% success)"
        )
        print(
            f"DEBUG: Final summary - {len(loaded_cogs)}/{total_attempted} cogs loaded ({success_rate:.1f}% success)"
        )

        if failed_cogs:
            logger.warning("❌ Failed cogs:")
            print("DEBUG: Failed cogs:")
            for cog, error in failed_cogs:
                logger.warning(f"   - {cog}: {error}")
                print(f"DEBUG:   - {cog}: {error}")

            # Group failures by tier for analysis
            failure_analysis = {}
            for tier_name, cogs in all_tiers:
                failed_in_tier = [cog for cog, _ in failed_cogs if cog in cogs]
                if failed_in_tier:
                    failure_analysis[tier_name] = failed_in_tier

            if failure_analysis:
                logger.warning("📊 Failure analysis by tier:")
                for tier, failed_list in failure_analysis.items():
                    logger.warning(
                        f"   {tier}: {len(failed_list)} failed - {', '.join(failed_list)}"
                    )

        # Verify critical cogs loaded
        critical_verification = {
            "EventManager": self.get_cog("EventManager"),
            "Profile": self.get_cog("Profile"),
            "AdminActions": self.get_cog("AdminActions"),
        }

        missing_critical = [
            name for name, cog in critical_verification.items() if not cog
        ]
        if missing_critical:
            logger.error(f"🚨 Missing critical cogs: {', '.join(missing_critical)}")
            print(f"DEBUG: MISSING CRITICAL COGS: {missing_critical}")

        return loaded_cogs, failed_cogs

    async def on_ready(self):
        """
        Handles bot ready event and performs startup completion tasks.

        - Logs connection status
        - Performs health checks
        - Sends startup notifications
        - Tracks reconnection events
        """
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
                    **health_stats,
                }

                await notify_startup_complete(True, total_startup_time, stats)

                # Send activity notification
                await notify_activity(
                    "bot_online",
                    status="Online and ready",
                    guilds=len(self.guilds),
                    startup_time=f"{total_startup_time:.2f}s",
                )

            self.startup_completed = True
        else:
            logger.info(f"{self.user} reconnected")
            print(f"DEBUG: Bot {self.user} reconnected")

            # Notify reconnection
            if MONITORING_AVAILABLE:
                await notify_activity(
                    "bot_reconnected", status="Reconnected to Discord"
                )

    async def _final_health_check(self):
        """
        Perform final health check of bot systems after startup.

        Checks:
        - Guild connections
        - Loaded cogs
        - Available commands
        - Critical cog availability

        Returns:
            dict: Health status metrics and any detected issues
        """
        print("DEBUG: _final_health_check() called")
        try:
            logger.info("Running final health check...")

            health_status = {
                "guilds": len(self.guilds),
                "cogs_loaded": len(self.cogs),
                "commands_available": len(self.commands),
                "data_fixes": 0,
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
                health_status["missing_critical_cogs"] = len(missing_critical)
                await notify_error(
                    "Missing Critical Cogs",
                    Exception(
                        f"Critical cogs not loaded: {', '.join(missing_critical)}"
                    ),
                    "Some essential bot functionality may not work",
                )

            logger.info("Final health check completed")
            print("DEBUG: Final health check completed")

            return health_status

        except Exception as e:
            logger.exception(f"Error during final health check: {e}")
            print(f"DEBUG: Error during final health check: {e}")
            if MONITORING_AVAILABLE:
                await notify_error(
                    "Health Check Error", e, "Error during bot health check"
                )
            return {"error": str(e)}

    async def close(self):
        """
        Clean shutdown of the bot instance.

        - Notifies monitoring systems
        - Performs cleanup
        - Ensures graceful shutdown
        """
        print("DEBUG: close() called")
        logger.info("Shutting down bot...")

        # Notify admin of shutdown
        if MONITORING_AVAILABLE:
            try:
                await notify_activity("bot_shutdown", status="Bot is shutting down")
            except:
                pass  # Don't let notification failure prevent shutdown

        from utils.file_ops import file_ops

        # Perform file operations cleanup
        await file_ops.shutdown()

        await super().close()
        logger.info("Bot shutdown complete")
        print("DEBUG: Bot shutdown complete")

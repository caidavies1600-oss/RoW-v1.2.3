# Main bot client class
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
    from utils.data_manager import DataManager
    print("DEBUG: utils.data_manager imported")
except Exception as e:
    print(f"DEBUG: utils.data_manager failed: {e}")

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
        print("DEBUG: RowBot initialization complete")

    async def setup_hook(self):
        print("DEBUG: setup_hook() called")
        logger.info("Setting up bot...")

        try:
            print("DEBUG: Setting up error handler...")
            setup_error_handler(self)
            logger.info("Error handling configured")

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

    async def _load_cogs(self):
        print("DEBUG: _load_cogs() called")

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
            "cogs.user.commands"
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
            logger.info(f"{self.user} is online!")
            print(f"DEBUG: Bot {self.user} is online!")
            logger.info(f"Serving {len(self.guilds)} guild(s)")
            print(f"DEBUG: Serving {len(self.guilds)} guild(s)")

            await self._final_health_check()
            self.startup_completed = True
        else:
            logger.info(f"{self.user} reconnected")
            print(f"DEBUG: Bot {self.user} reconnected")

    async def _final_health_check(self):
        print("DEBUG: _final_health_check() called")
        try:
            logger.info("Running final health check...")

            health_status = {
                "guilds": len(self.guilds),
                "cogs_loaded": len(self.cogs),
                "commands_available": len(self.commands)
            }

            logger.info("Final Health Status:")
            for key, value in health_status.items():
                logger.info(f"  - {key}: {value}")
                print(f"DEBUG: Health - {key}: {value}")

            print(f"DEBUG: Available commands: {[cmd.name for cmd in self.commands]}")
            print(f"DEBUG: Loaded cogs: {list(self.cogs.keys())}")

            if self.get_cog("EventManager"):
                logger.info("EventManager cog is functional")
                print("DEBUG: EventManager cog found")
            else:
                logger.error("EventManager cog not available")
                print("DEBUG: EventManager cog NOT found")

            if self.get_cog("UserCommands"):
                logger.info("UserCommands cog is functional")
                print("DEBUG: UserCommands cog found")
            else:
                logger.warning("UserCommands cog not available")
                print("DEBUG: UserCommands cog NOT found")

            if self.get_cog("OwnerActions"):
                logger.info("OwnerActions cog is functional")
                print("DEBUG: OwnerActions cog found")
            else:
                logger.warning("OwnerActions cog not available")
                print("DEBUG: OwnerActions cog NOT found")

            logger.info("Final health check completed")
            print("DEBUG: Final health check completed")

        except Exception as e:
            logger.exception(f"Error during final health check: {e}")
            print(f"DEBUG: Error during final health check: {e}")

    async def close(self):
        print("DEBUG: close() called")
        logger.info("Shutting down bot...")
        await super().close()
        logger.info("Bot shutdown complete")
        print("DEBUG: Bot shutdown complete")
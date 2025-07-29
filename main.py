
"""
Discord RoW Bot - Main Entry Point
A Discord bot for managing Roots of War events and team signups.
"""

import asyncio
import discord
from discord.ext import commands
import traceback
import sys
import os

print("DEBUG: Starting main.py imports...")
print(f"DEBUG: Python version: {sys.version}")
print(f"DEBUG: Discord.py version: {discord.__version__}")

# Check environment first
print("DEBUG: Checking environment variables...")
bot_token_env = os.getenv("BOT_TOKEN")
if bot_token_env:
    print(f"DEBUG: BOT_TOKEN found in environment (length: {len(bot_token_env)})")
else:
    print("DEBUG: BOT_TOKEN not found in environment variables")

print("DEBUG: Available environment variables:")
for key in sorted(os.environ.keys()):
    if 'TOKEN' in key or 'BOT' in key:
        print(f"  - {key}: {'*' * min(len(os.environ[key]), 10)}")

print("DEBUG: Attempting imports...")

try:
    print("DEBUG: Importing bot.client...")
    from bot.client import RowBot
    print("DEBUG: RowBot imported successfully")
except Exception as e:
    print(f"DEBUG: Failed to import RowBot: {e}")
    print("DEBUG: Full traceback:")
    traceback.print_exc()
    print("DEBUG: Attempting to import individual components...")

    try:
        print("DEBUG: Testing utils.logger import...")
        from utils.logger import setup_logger
        print("DEBUG: utils.logger imported")
    except Exception as e2:
        print(f"DEBUG: utils.logger failed: {e2}")
        try:
            print("DEBUG: Testing config.settings import...")
            from config.settings import BOT_TOKEN
            print("DEBUG: config.settings imported")
        except Exception as e2:
            print(f"DEBUG: config.settings failed: {e2}")

        try:
            print("DEBUG: Testing config.constants import...")
            from config.constants import COLORS
            print("DEBUG: config.constants imported")
        except Exception as e2:
            print(f"DEBUG: config.constants failed: {e2}")

        sys.exit(1)

try:
    print("DEBUG: Importing config.settings...")
    from config.settings import BOT_TOKEN
    print("DEBUG: BOT_TOKEN imported successfully")
    if not BOT_TOKEN:
        print("DEBUG: BOT_TOKEN is empty!")
        sys.exit(1)
    else:
        print(f"DEBUG: BOT_TOKEN length: {len(BOT_TOKEN)} characters")
        if len(BOT_TOKEN) > 10:
            print(f"DEBUG: BOT_TOKEN format: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
except Exception as e:
    print(f"DEBUG: Failed to import BOT_TOKEN: {e}")
    print("DEBUG: Full traceback:")
    traceback.print_exc()
    sys.exit(1)

try:
    print("DEBUG: Setting up logger...")
    from utils.logger import setup_logger  # Safe here
    logger = setup_logger("main")
    print("DEBUG: Logger setup successful")
except Exception as e:
    print(f"DEBUG: Failed to setup logger (continuing without): {e}")
    logger = None

print("DEBUG: All imports completed successfully!")

async def main():
    """Main entry point for the bot."""
    print("DEBUG: Entering main() function...")

    try:
        print("DEBUG: Creating RowBot instance...")
        bot = RowBot()
        print("DEBUG: RowBot instance created successfully")

        print("DEBUG: Bot intents:")
        print(f"  - members: {bot.intents.members}")
        print(f"  - message_content: {bot.intents.message_content}")
        print(f"  - guilds: {bot.intents.guilds}")

        print("DEBUG: Starting bot connection to Discord...")
        async with bot:
            if logger:
                logger.info("Starting Discord RoW Bot...")
            print("DEBUG: Bot.start() called with token...")
            await bot.start(BOT_TOKEN)

    except discord.LoginFailure as e:
        print(f"DEBUG: Discord login failed: {e}")
        print("DEBUG: This usually means:")
        print("   1. Invalid bot token")
        print("   2. Token has wrong permissions")
        print("   3. Token was regenerated/revoked")
        print("DEBUG: Full traceback:")
        traceback.print_exc()

    except discord.HTTPException as e:
        print(f"DEBUG: Discord HTTP error: {e}")
        print("DEBUG: This could be a network or API issue")
        print("DEBUG: Full traceback:")
        traceback.print_exc()

    except discord.errors.ConnectionClosed as e:
        print(f"DEBUG: Discord connection closed: {e}")
        print("DEBUG: Full traceback:")
        traceback.print_exc()

    except KeyboardInterrupt:
        print("DEBUG: Bot shutdown requested by user (KeyboardInterrupt)")
        if logger:
            logger.info("Bot shutdown requested by user")

    except Exception as e:
        print(f"DEBUG: Unexpected critical error in main(): {e}")
        print(f"DEBUG: Error type: {type(e).__name__}")
        print("DEBUG: Full traceback:")
        traceback.print_exc()
        if logger:
            logger.exception(f"Critical error starting bot: {e}")
        raise

if __name__ == "__main__":
    print("DEBUG: Script started as main module")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Python path: {sys.path}")

    # List files to verify structure
    print("DEBUG: Checking file structure...")
    if os.path.exists("bot"):
        print("DEBUG: /bot directory exists")
        if os.path.exists("bot/client.py"):
            print("DEBUG: /bot/client.py exists")
        else:
            print("DEBUG: /bot/client.py missing")
    else:
        print("DEBUG: /bot directory missing")

    if os.path.exists("config"):
        print("DEBUG: /config directory exists")
        if os.path.exists("config/settings.py"):
            print("DEBUG: /config/settings.py exists")
        else:
            print("DEBUG: /config/settings.py missing")
    else:
        print("DEBUG: /config directory missing")

    print("DEBUG: Starting asyncio.run(main())...")
    try:
        asyncio.run(main())
        print("DEBUG: asyncio.run(main()) completed normally")
    except KeyboardInterrupt:
        print("DEBUG: Received KeyboardInterrupt in asyncio.run()")
    except Exception as e:
        print(f"DEBUG: Fatal error in asyncio.run(): {e}")
        print(f"DEBUG: Error type: {type(e).__name__}")
        print("DEBUG: Full traceback:")
        traceback.print_exc()
        sys.exit(1)

    print("DEBUG: Script execution completed")

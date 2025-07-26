"""
Discord RoW Bot - Main Entry Point
A Discord bot for managing Roots of War events and team signups.
"""

import asyncio
import discord
from discord.ext import commands
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from bot.client import RowBot
    from config.settings import BOT_TOKEN
    from utils.logger import setup_logger
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("📁 Current working directory:", os.getcwd())
    print("📂 Files in current directory:")
    for item in os.listdir('.'):
        print(f"  - {item}")
    
    # Try alternative import paths
    try:
        print("🔄 Trying alternative imports...")
        import bot.client as bot_client
        import config.settings as settings
        import utils.logger as logger_utils
        
        RowBot = bot_client.RowBot
        BOT_TOKEN = settings.BOT_TOKEN
        setup_logger = logger_utils.setup_logger
        print("✅ Alternative imports successful!")
    except ImportError as e2:
        print(f"❌ Alternative imports also failed: {e2}")
        print("\n🚨 CRITICAL: Bot files not found!")
        print("Please check that these folders exist:")
        print("  - bot/")
        print("  - config/")
        print("  - utils/")
        print("  - cogs/")
        sys.exit(1)

logger = setup_logger("main")

async def main():
    """Main entry point for the bot."""
    try:
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not found in environment variables")
            print("❌ Please set BOT_TOKEN in your environment or config/settings.py")
            return
            
        bot = RowBot()
        async with bot:
            logger.info("🚀 Starting Discord RoW Bot...")
            await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown requested by user")
    except Exception as e:
        logger.exception(f"💥 Critical error starting bot: {e}")
        print(f"💥 Critical error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
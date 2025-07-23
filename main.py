"""
Discord RoW Bot - Main Entry Point
A Discord bot for managing Roots of War events and team signups.
"""

import asyncio
import discord
from discord.ext import commands

from bot.client import RowBot
from config.settings import BOT_TOKEN
from utils.logger import setup_logger

logger = setup_logger("main")

async def main():
    """Main entry point for the bot."""
    try:
        bot = RowBot()
        async with bot:
            logger.info("Starting Discord RoW Bot...")
            await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.exception(f"Critical error starting bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
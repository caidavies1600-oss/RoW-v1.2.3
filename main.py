    """
Discord RoW Bot - Main Entry Point
A Discord bot for managing Roots of War events and team signups.
"""

    import asyncio
    import discord
    from discord.ext import commands
    import sys
    import os

    # Add the current directory to Python path for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    def validate_environment():
        """Validate environment before starting bot."""
        issues = []

        # Check if we can import required modules
        try:
            from bot.client import RowBot
            from config.settings import BOT_TOKEN
            from utils.logger import setup_logger
        except ImportError as e:
            issues.append(f"Import error: {e}")
            print(f"❌ Import Error: {e}")

            # Try to diagnose the issue
            print("📁 Current working directory:", os.getcwd())
            print("📂 Files in current directory:")
            try:
                for item in sorted(os.listdir('.')):
                    item_type = "📁" if os.path.isdir(item) else "📄"
                    print(f"  {item_type} {item}")
            except Exception:
                print("  (Could not list directory contents)")

            return issues

        # Check BOT_TOKEN
        if not BOT_TOKEN:
            issues.append("BOT_TOKEN not found in environment variables")

        # Check for required directories
        required_dirs = ['bot', 'config', 'utils', 'cogs', 'data']
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                issues.append(f"Missing required directory: {dir_name}")

        return issues

    async def main():
        """Main entry point for the bot."""
        print("🚀 Starting Discord RoW Bot...")

        # Validate environment first
        env_issues = validate_environment()
        if env_issues:
            print("❌ Environment validation failed:")
            for issue in env_issues:
                print(f"  - {issue}")
            print("\n🔧 Please fix these issues before starting the bot.")
            return 1

        try:
            # Import after validation
            from bot.client import RowBot
            from config.settings import BOT_TOKEN
            from utils.logger import setup_logger

            logger = setup_logger("main")
            logger.info("🚀 Starting Discord RoW Bot...")

            # Create and start bot
            bot = RowBot()

            async with bot:
                logger.info("🔗 Connecting to Discord...")
                await bot.start(BOT_TOKEN)

        except KeyboardInterrupt:
            print("\n👋 Bot shutdown requested by user")
            if 'logger' in locals():
                logger.info("👋 Bot shutdown requested by user")
            return 0

        except discord.LoginFailure:
            print("❌ Invalid BOT_TOKEN - please check your token")
            if 'logger' in locals():
                logger.error("❌ Invalid BOT_TOKEN")
            return 1

        except discord.PrivilegedIntentsRequired:
            print("❌ Missing required intents - please enable them in Discord Developer Portal")
            if 'logger' in locals():
                logger.error("❌ Missing required intents")
            return 1

        except Exception as e:
            print(f"💥 Critical error starting bot: {e}")
            if 'logger' in locals():
                logger.exception(f"💥 Critical error starting bot: {e}")

            # Try to provide helpful error information
            if "No module named" in str(e):
                print("\n🔧 This looks like a module import issue.")
                print("Please check that all required files are present:")
                print("  - bot/client.py")
                print("  - config/settings.py") 
                print("  - utils/logger.py")

            elif "BOT_TOKEN" in str(e):
                print("\n🔧 This looks like a token issue.")
                print("Please set your BOT_TOKEN environment variable.")

            return 1

    if __name__ == "__main__":
        try:
            exit_code = asyncio.run(main())
            sys.exit(exit_code)
        except KeyboardInterrupt:
            print("\n👋 Shutdown complete")
            sys.exit(0)
        except Exception as e:
            print(f"💥 Fatal error: {e}")
            sys.exit(1)
"""
One-off test script to post a test event message for the Discord RoW bot.

This script:
- Creates a temporary bot instance
- Posts a test event message with signup buttons
- Keeps the bot running for 5 minutes to allow testing
- Cleans up test data before shutting down

Usage:
    Run this file directly to test the event system:
    python test_event_post.py

Requirements:
    - Bot token must be configured in config/settings.py
    - Alert channel and role IDs must be set in config/constants.py
    - Event manager and profile cogs must be available
"""

import asyncio
from datetime import datetime

import discord

from bot.client import RowBot
from cogs.events.signup_view import EventSignupView
from config.constants import ALERT_CHANNEL_ID, COLORS, EMOJIS, ROW_NOTIFICATION_ROLE_ID

# Import your bot's configuration
from config.settings import BOT_TOKEN
from utils.logger import setup_logger

logger = setup_logger("test_event")


async def post_test_event():
    """
    Post a one-off test event message to verify event system functionality.

    Features tested:
    - Event message formatting and embedding
    - Role mentions and notifications
    - Signup button functionality
    - Team role restrictions
    - Event data persistence

    The test runs for 5 minutes before automatically cleaning up and shutting down.
    All test signups are cleared when the test completes.

    Raises:
        Exception: If channel access fails or required cogs cannot be loaded
    """
    # Create a minimal bot instance
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.guilds = True

    bot = RowBot()

    @bot.event
    async def on_ready():
        logger.info(f"Test bot logged in as {bot.user}")

        try:
            # Get the alert channel
            alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
            if not alert_channel or not isinstance(alert_channel, discord.TextChannel):
                logger.error(f"Could not find text channel with ID {ALERT_CHANNEL_ID}")
                await bot.close()
                return

            # Load the EventManager cog to access its functionality
            await bot.load_extension("cogs.events.manager")
            await bot.load_extension(
                "cogs.user.profile"
            )  # Needed for IGN functionality

            event_manager = bot.get_cog("EventManager")
            if not event_manager:
                logger.error("Could not load EventManager cog")
                await bot.close()
                return

            # Create the test embed
            embed = discord.Embed(
                title="🧪 TEST: Weekly RoW Sign-Up",
                description=(
                    "**Hey! I'm testing the new bot for next RoW.**\n\n"
                    "This is a TEST signup - please try the buttons below:\n\n"
                    f"{EMOJIS['CALENDAR']} **Schedule**:\n"
                    f"🏆 Main Team → {EMOJIS['CLOCK']} `Saturday 14:00 UTC` *(Main Team role required)*\n"
                    f"🔸 Team 2 → {EMOJIS['CLOCK']} `Sunday 14:00 UTC` *(Open to all)*\n"
                    f"🔸 Team 3 → {EMOJIS['CLOCK']} `Sunday 20:00 UTC` *(Open to all)*\n\n"
                    f"{EMOJIS['WARNING']} **Note:** Only people with the RoW Main Team role can choose Main Team.\n"
                    f"Other teams are open to everyone!\n\n"
                    f"{EMOJIS['SUCCESS']} Use the buttons below to test joining!"
                ),
                color=COLORS["WARNING"],  # Different color to indicate test
            )

            embed.set_footer(
                text="⚠️ This is a TEST - Signups will be cleared after testing"
            )
            embed.timestamp = datetime.utcnow()

            # Create the signup view
            view = EventSignupView(event_manager)

            # Send the test message with role ping
            message = await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}> **[TEST MESSAGE]**",
                embed=embed,
                view=view,
            )

            logger.info(f"✅ Test event posted successfully in {alert_channel.name}")
            logger.info(f"Message ID: {message.id}")

            # Keep bot running for 5 minutes to allow testing
            await asyncio.sleep(300)  # 5 minutes

            # Clear test signups before closing
            await event_manager.clear_all_signups()
            logger.info("✅ Test signups cleared")

            await bot.close()

        except Exception as e:
            logger.exception(f"Error posting test event: {e}")
            await bot.close()

    # Start the bot
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in config/settings.py")
    await bot.start(BOT_TOKEN)


def main():
    """
    Run the test event post script.

    Handles:
    - Script initialization
    - Asyncio event loop setup
    - Error handling and graceful shutdown
    - User feedback and logging
    - Cleanup of test data

    The script will run for exactly 5 minutes unless interrupted.
    Use Ctrl+C to cancel the test early.
    """
    print("🚀 Starting test event post...")
    print(f"📅 Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("⏰ Bot will stay online for 5 minutes to allow testing")
    print("-" * 50)

    try:
        asyncio.run(post_test_event())
    except KeyboardInterrupt:
        print("\n⛔ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

    print("\n✅ Test completed!")


if __name__ == "__main__":
    main()

"""Global error handling system for the RoW bot.

This module provides centralized error handling for all bot commands,
including user-friendly error messages and admin notifications for critical errors.

Error types handled:
- Permission errors (CheckFailure)
- Missing arguments
- Invalid arguments
- Unknown commands
- Cooldown violations
- Unexpected errors
"""

import discord
from discord.ext import commands

from config.settings import BOT_ADMIN_USER_ID
from utils.logger import setup_logger

logger = setup_logger("error_handler")


def setup_error_handler(bot):
    """
    Setup global error handling for the bot.

    Args:
        bot: The Discord bot instance to attach error handlers to

    Implements handlers for common error types and provides:
    - User-friendly error messages
    - Error logging
    - Admin notifications for critical errors
    - Cooldown management
    """

    @bot.event
    async def on_command_error(ctx, error):
        """
        Global error handler for all bot commands.

        Args:
            ctx: The command context where the error occurred
            error: The error that was raised

        Handles:
            - commands.CheckFailure: Permission errors
            - commands.MissingRequiredArgument: Missing parameters
            - commands.BadArgument: Invalid argument types/values
            - commands.CommandNotFound: Unknown commands
            - commands.CommandOnCooldown: Rate limit/cooldown errors
            - Unexpected errors: Logged and reported to admin
        """

        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")

        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided.")

        elif isinstance(error, commands.CommandNotFound):
            # Silently ignore unknown commands
            return

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Command on cooldown. Try again in {error.retry_after:.1f}s"
            )

        else:
            # Log unexpected errors and notify admin
            logger.exception(f"Unhandled error in {ctx.command}: {error}")
            await ctx.send("❌ An unexpected error occurred.")

            try:
                admin = await bot.fetch_user(BOT_ADMIN_USER_ID)
                if admin:
                    embed = discord.Embed(
                        title="🚨 Bot Error",
                        description=f"Command: `{ctx.command}`\nError: `{error}`",
                        color=discord.Color.red(),
                    )
                    await admin.send(embed=embed)
            except Exception:
                pass  # Don't fail if we can't notify admin

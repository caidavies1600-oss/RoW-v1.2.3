"""Global error handling for the bot."""

import discord
from discord.ext import commands
import traceback
from utils.logger import setup_logger
from config.settings import BOT_ADMIN_USER_ID
from config.constants import EMOJIS, COLORS

logger = setup_logger("error_handler")

def setup_error_handler(bot):
    """Setup global error handling for the bot."""

    @bot.event
    async def on_command_error(ctx, error):
        """Handle command errors globally with detailed logging."""

        # Get error details
        command_name = ctx.command.name if ctx.command else "unknown"
        user_info = f"{ctx.author} (ID: {ctx.author.id})"
        guild_info = f"{ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "DM"

        # Handle different error types
        if isinstance(error, commands.CheckFailure):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} You don't have permission to use this command.")
            logger.warning(f"Permission denied for {user_info} in {guild_info} - command: {command_name}")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} Missing required argument: `{error.param.name}`")
            logger.warning(f"Missing argument for {user_info} - command: {command_name}, missing: {error.param.name}")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} Invalid argument provided. Please check your input.")
            logger.warning(f"Bad argument for {user_info} - command: {command_name}")

        elif isinstance(error, commands.CommandNotFound):
            # Silently ignore unknown commands but log them
            logger.debug(f"Unknown command attempted by {user_info}: {ctx.message.content}")
            return

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"{EMOJIS.get('WARNING', '⏰')} Command on cooldown. Try again in {error.retry_after:.1f}s")
            logger.info(f"Cooldown hit by {user_info} - command: {command_name}")

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} This command is currently disabled.")
            logger.warning(f"Disabled command attempted by {user_info} - command: {command_name}")

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} This command can't be used in private messages.")
            logger.warning(f"Guild-only command in DM by {user_info} - command: {command_name}")

        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} You need these permissions: {perms}")
            logger.warning(f"Missing permissions for {user_info} - command: {command_name}, needs: {perms}")

        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} I need these permissions: {perms}")
            logger.error(f"Bot missing permissions in {guild_info} - command: {command_name}, needs: {perms}")

        elif isinstance(error, discord.Forbidden):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} I don't have permission to do that.")
            logger.error(f"Discord Forbidden error in {guild_info} - command: {command_name}")

        elif isinstance(error, discord.NotFound):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} The requested resource was not found.")
            logger.error(f"Discord NotFound error in {guild_info} - command: {command_name}")

        elif isinstance(error, discord.HTTPException):
            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} A network error occurred. Please try again.")
            logger.error(f"Discord HTTP error in {guild_info} - command: {command_name}: {error}")

        else:
            # Log unexpected errors with full traceback
            error_id = f"ERR_{ctx.message.id}"
            logger.error(f"Unhandled error [{error_id}] in {guild_info} - command: {command_name}")
            logger.error(f"User: {user_info}")
            logger.error(f"Error: {error}")
            logger.error(f"Traceback:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")

            await ctx.send(f"{EMOJIS.get('ERROR', '❌')} An unexpected error occurred. Error ID: `{error_id}`")

            # Notify admin of critical errors
            try:
                admin = await bot.fetch_user(BOT_ADMIN_USER_ID)
                if admin:
                    embed = discord.Embed(
                        title="🚨 Bot Error",
                        description=f"**Command:** `{command_name}`\n**User:** {user_info}\n**Guild:** {guild_info}",
                        color=COLORS.get("DANGER", 0xED4245)
                    )
                    embed.add_field(name="Error ID", value=error_id, inline=True)
                    embed.add_field(name="Error Type", value=type(error).__name__, inline=True)
                    embed.add_field(name="Error Message", value=str(error)[:1000], inline=False)

                    await admin.send(embed=embed)
            except:
                pass  # Don't fail if we can't notify admin

    @bot.event
    async def on_error(event, *args, **kwargs):
        """Handle general bot errors (not command-specific)."""
        error_info = traceback.format_exc()
        logger.error(f"Unhandled error in event '{event}':")
        logger.error(error_info)

        # Try to notify admin of critical errors
        try:
            admin = await bot.fetch_user(BOT_ADMIN_USER_ID)
            if admin:
                embed = discord.Embed(
                    title="🚨 Bot Event Error",
                    description=f"**Event:** `{event}`",
                    color=COLORS.get("DANGER", 0xED4245)
                )
                embed.add_field(name="Error", value=error_info[:1000], inline=False)
                await admin.send(embed=embed)
        except:
            pass

    @bot.event
    async def on_command_completion(ctx):
        """Log successful command completions."""
        command_name = ctx.command.name if ctx.command else "unknown"
        user_info = f"{ctx.author} (ID: {ctx.author.id})"
        guild_info = f"{ctx.guild.name}" if ctx.guild else "DM"

        logger.info(f"✅ Command completed: {command_name} by {user_info} in {guild_info}")

    logger.info("✅ Enhanced error handling configured")
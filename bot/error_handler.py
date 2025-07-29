“”“Global error handling for the bot.”””

import discord
from discord.ext import commands
from utils.logger import setup_logger
from config.settings import BOT_ADMIN_USER_ID

logger = setup_logger(“error_handler”)

def setup_error_handler(bot):
“”“Setup global error handling for the bot.”””

```
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors globally."""

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
        await ctx.send(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f}s")

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
                    color=discord.Color.red()
                )
                await admin.send(embed=embed)
        except:
            pass  # Don't fail if we can't notify admin
```
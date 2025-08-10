"""User profile management cog."""

import discord
from discord.ext import commands

from utils.data_manager import DataManager
from utils.validators import Validators
from utils.logger import setup_logger
from config.constants import FILES, EMOJIS

logger = setup_logger("profile")


class ProfileCog(commands.Cog, name="Profile"):
    """Manages user profiles and IGN mappings."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()
        self.ign_map = self.data_manager.load_json(FILES["IGN_MAP"], {})

    def save_data(self) -> bool:
        """Save IGN mappings to file."""
        success = self.data_manager.save_json(FILES["IGN_MAP"], self.ign_map)
        if not success:
            logger.error("❌ Failed to save IGN mappings to ign_map.json")
        return success

    def get_ign(self, user: discord.User) -> str:
        """Get user's IGN or fallback to display name."""
        return self.ign_map.get(str(user.id), user.display_name)

    def has_ign(self, user: discord.User) -> bool:
        """Check if user has set a custom IGN."""
        return str(user.id) in self.ign_map

    async def warn_if_no_ign(self, interaction: discord.Interaction):
        """Warn user if they haven't set their IGN."""
        if not self.has_ign(interaction.user):
            await interaction.response.send_message(
                f"{EMOJIS['WARNING']} You haven't set your IGN yet. Use `!setign YourName`.",
                ephemeral=True
            )
            return True
        return False

    @commands.command(name="setign")
    async def set_ign(self, ctx, *, ign: str):
        """Set your in-game name."""
        valid, error = Validators.validate_ign(ign)
        if not valid:
            return await ctx.send(f"{EMOJIS['ERROR']} {error}")

        user_id = str(ctx.author.id)
        old_ign = self.ign_map.get(user_id)
        self.ign_map[user_id] = ign.strip()

        if self.save_data():
            if old_ign:
                await ctx.send(f"{EMOJIS['SUCCESS']} IGN updated from `{old_ign}` to `{ign}`")
                logger.info(f"{ctx.author} updated IGN from '{old_ign}' to '{ign}'")
            else:
                await ctx.send(f"{EMOJIS['SUCCESS']} IGN set to `{ign}`")
                logger.info(f"{ctx.author} set IGN to '{ign}'")
        else:
            await ctx.send(f"{EMOJIS['ERROR']} Failed to save IGN. Please try again.")

    @commands.command(name="myign")
    async def show_ign(self, ctx):
        """View your stored IGN."""
        if self.has_ign(ctx.author):
            ign = self.get_ign(ctx.author)
            await ctx.send(f"🎮 Your IGN is: `{ign}`")
        else:
            await ctx.send(f"{EMOJIS['ERROR']} You haven't set your IGN yet. Use `!setign YourName`")

    @commands.command(name="clearign")
    async def clear_ign(self, ctx):
        """Clear your stored IGN."""
        user_id = str(ctx.author.id)
        if user_id in self.ign_map:
            old_ign = self.ign_map[user_id]
            del self.ign_map[user_id]

            if self.save_data():
                await ctx.send(f"{EMOJIS['SUCCESS']} Your IGN `{old_ign}` has been cleared.")
                logger.info(f"{ctx.author} cleared their IGN")
            else:
                await ctx.send(f"{EMOJIS['ERROR']} Failed to clear IGN. Please try again.")
        else:
            await ctx.send(f"{EMOJIS['ERROR']} You haven't set an IGN yet.")


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))

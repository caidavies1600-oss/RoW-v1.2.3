# cogs/user/commands.py

import discord
from discord.ext import commands
import json
import os
from config.constants import ADMIN_ROLE_IDS  # This was missing!


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ign_map = {}
        self.ign_file = "data/ign_map.json"
        self.load_ign_map()

    def load_ign_map(self):
        if os.path.exists(self.ign_file):
            with open(self.ign_file, "r") as f:
                self.ign_map = json.load(f)
        else:
            self.ign_map = {}

    def save_ign_map(self):
        with open(self.ign_file, "w") as f:
            json.dump(self.ign_map, f, indent=4)

    def get_ign(self, user):
        return self.ign_map.get(str(user.id))

    def has_ign(self, user):
        return str(user.id) in self.ign_map

    async def warn_if_no_ign(self, interaction: discord.Interaction):
        if not self.has_ign(interaction.user):
            await interaction.response.send_message(
                "⚠️ You haven't set your IGN yet. Use `!setign YourName`.",
                ephemeral=True
            )

    @commands.command(name="commands", help="Show available commands.")
    async def list_commands(self, ctx):
        """List all available commands dynamically, split by user/admin."""
        try:
            is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

            # Simple hardcoded lists (reliable)
            admin_commands = [
                "`!win` — Record a win for a team",
                "`!loss` — Record a loss for a team", 
                "`!block` — Block a user from signing up",
                "`!unblock` — Unblock a user manually",
                "`!blocklist` — List all currently blocked users",
                "`!absent` — Mark player absent from this week's RoW event",
                "`!present` — Remove a user's absence mark",
                "`!absentees` — Show all users marked absent",
                "`!rowstats` — Show comprehensive RoW stats",
                "`!exportteams` — Export current team signups to a text file",
                "`!exporthistory` — Export event history to a text file",
                "`!startevent` — Start a new event",
                "`!backup` — Create a manual backup of all data files",
                "`!testchannels` — Test channel access"
            ]

            user_commands = [
                "`!myign` — View your stored IGN",
                "`!setign` — Set your in-game name", 
                "`!clearign` — Clear your stored IGN",
                "`!showteams` — Show current teams"
            ]

            embed = discord.Embed(
                title="📜 Available Bot Commands",
                color=discord.Color.blurple()
            )
            
            embed.add_field(
                name="👤 User Commands", 
                value="\n".join(user_commands),
                inline=False
            )

            if is_admin:
                embed.add_field(
                    name="🛡️ Admin Commands", 
                    value="\n".join(admin_commands),
                    inline=False
                )
            else:
                embed.set_footer(text="Admin commands are only visible if you have the required roles.")

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error in commands: {str(e)}")
            print(f"Commands error: {e}")

    @commands.command(name="test123")
    async def test_command(self, ctx):
        """Test command to verify cog is working"""
        await ctx.send("✅ User commands cog is working!")


async def setup(bot):
    await bot.add_cog(UserCommands(bot))
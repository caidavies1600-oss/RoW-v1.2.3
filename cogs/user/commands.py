           # cogs/user/commands.py

import discord
from discord.ext import commands
import json
import os
from config.settings import ADMIN_ROLE_IDS, BOT_ADMIN_USER_ID


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
        """List all available commands dynamically, split by user/admin/owner."""
        try:
            is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)
            is_owner = ctx.author.id == BOT_ADMIN_USER_ID

            # Owner commands (only you see these)
            owner_commands = [
                "`!checkjson` — Check the integrity of all JSON data files",
                "`!fixjson` — Attempt to fix corrupted or missing JSON files",
                "`!resetjson` — Reset a specific JSON file to its default structure",
                "`!migratedata` — Convert user IDs in events.json to IGN strings",
                "`!sheetsconnect` — Connect and test Google Sheets integration",
                "`!sheetsync` — Manually sync data with Google Sheets",  
                "`!sheetsstatus` — Check Google Sheets connection status",
                "`!healthcheck` — Run comprehensive bot health diagnostics"
            ]

            # Admin commands
            admin_commands = [
                "`!win` — Record a win for a team",
                "`!loss` — Record a loss for a team", 
                "`!block` — Block a user from signing up",
                "`!unblock` — Unblock a user manually",
                "`!blocklist` — List all currently blocked users",
                "`!absent` — Mark player absent from this week's RoW event",
                "`!present` — Remove a user's absence mark",
                "`!absentees` — Show all users marked absent",
                "`!rowstats` — Show comprehensive RoW stats and analytics",
                "`!exportteams` — Export current team signups to a text file",
                "`!exporthistory` — Export event history to a text file",
                "`!startevent` — Start a new event and clear signups",
                "`!endweek` — End current week and generate summary",
                "`!settime` — Set event time for a specific team",
                "`!gettimes` — Show all team event times",
                "`!forceremove` — Force remove user from all teams",
                "`!teamstats` — Show detailed team performance statistics",
                "`!playerstats` — Show individual player statistics",
                "`!attendance` — Show attendance tracking for players",
                "`!backup` — Create manual backup of bot data",
                "`!restore` — Restore from backup file"
            ]

            # User commands
            user_commands = [
                "`!commands` — Show this command list",
                "`!myign` — View your stored IGN",
                "`!setign` — Set your in-game name", 
                "`!clearign` — Clear your stored IGN",
                "`!showteams` — Show current teams and signups",
                "`!mystats` — View your personal RoW statistics",
                "`!leaderboard` — Show top players by wins",
                "`!nextevent` — Show time until next RoW event",
                "`!eventinfo` — Show information about current events",
                "`!ping` — Check if bot is responsive",
                "`!help` — Get help with bot usage"
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

            if is_owner:
                embed.add_field(
                    name="👑 Bot Owner Commands", 
                    value="\n".join(owner_commands),
                    inline=False
                )

            # Set footer based on permissions
            if is_owner:
                embed.set_footer(text="You have full access to all bot commands.")
            elif is_admin:
                embed.set_footer(text="Admin commands are visible. Owner commands require bot owner permissions.")
            else:
                embed.set_footer(text="Admin and owner commands are only visible if you have the required permissions.")

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
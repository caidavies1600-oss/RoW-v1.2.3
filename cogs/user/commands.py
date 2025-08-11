# cogs/user/commands.py

import json
import os

import discord
from discord.ext import commands

from config.settings import ADMIN_ROLE_IDS, BOT_ADMIN_USER_ID


class UserCommands(commands.Cog):
    """
    Handles basic user commands and IGN management.

    Features:
    - IGN (in-game name) storage and retrieval
    - Command listing with permission levels
    - Basic user utilities
    - IGN validation and warnings
    """

    def __init__(self, bot):
        """
        Initialize the UserCommands cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.ign_map = {}
        self.ign_file = "data/ign_map.json"
        self.load_ign_map()

    def load_ign_map(self):
        """
        Load IGN mapping from JSON file.

        Creates empty mapping if file doesn't exist.
        """
        if os.path.exists(self.ign_file):
            with open(self.ign_file, "r") as f:
                self.ign_map = json.load(f)
        else:
            self.ign_map = {}

    def save_ign_map(self):
        """Save current IGN mapping to JSON file."""
        with open(self.ign_file, "w") as f:
            json.dump(self.ign_map, f, indent=4)

    def get_ign(self, user):
        """
        Get user's IGN if it exists.

        Args:
            user: Discord user object

        Returns:
            str: User's IGN or None if not set
        """
        return self.ign_map.get(str(user.id))

    def has_ign(self, user):
        """
        Check if user has set their IGN.

        Args:
            user: Discord user object

        Returns:
            bool: True if user has IGN set
        """
        return str(user.id) in self.ign_map

    async def warn_if_no_ign(self, interaction: discord.Interaction):
        """
        Send warning message if user hasn't set IGN.

        Args:
            interaction: Discord interaction to respond to
        """
        if not self.has_ign(interaction.user):
            await interaction.response.send_message(
                "⚠️ You haven't set your IGN yet. Use `!setign YourName`.",
                ephemeral=True,
            )

    @commands.command(name="commands", help="Show available commands.")
    async def list_commands(self, ctx):
        """
        Show available commands based on user permissions.

        Lists:
        - Basic user commands for everyone
        - Admin commands for users with admin roles
        - Owner commands for bot owner
        """
        try:
            is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)
            is_owner = ctx.author.id == BOT_ADMIN_USER_ID

            # Owner commands (only you see these)
            owner_commands = [
                "`!checkjson` — Check the integrity of all JSON data files",
                "`!fixjson` — Attempt to fix corrupted or missing JSON files",
                "`!resetjson` — Reset a specific JSON file to its default structure",
                "`!syncmembers` — Sync Discord members to Google Sheets",
                "`!fullsync` — Complete setup: sync members + create templates",
                "`!healthcheck` — Run comprehensive bot health diagnostics",
                "`!backup` — Create manual backup of bot data",
                "`!restore` — Restore from backup file",
                "`!addresult` — Add match result",
                "`!createtemplate` — Create Google Sheets templates",
                "`!sheetstest` — Test Google Sheets connection",
                "`!sheetsstatus` — Check Google Sheets status",
                "`!formatsheets` — Format Google Sheets",
                "`!export` — General export command",
                "`!importdata` — Import data",
                "`!cleardata` — Clear specific data",
                "`!resetstats` — Reset player statistics",
                "`!migratedata` — Migrate data between formats",
                "`!reloadcog` — Reload a specific cog",
                "`!unloadcog` — Unload a cog",
                "`!loadcog` — Load a cog",
                "`!serverinfo` — Get server information",
                "`!botinfo` — Get bot information",
                "`!shutdown` — Shutdown the bot",
                "`!restart` — Restart the bot",
                "`!logs` — View bot logs",
                "`!cleanlogs` — Clean log files",
                "`!maintenance` — Enable/disable maintenance mode",
            ]

            # Admin commands - only showing actually implemented ones
            admin_commands = [
                "`!win` — Record a win for a team",
                "`!loss` — Record a loss for a team",
                "`!results` — Show overall and recent results summary",
                "`!playerstats` — Show detailed player statistics",
                "`!block` — Block a user from signing up",
                "`!unblock` — Unblock a user manually",
                "`!blocklist` — List all currently blocked users",
                "`!absent` — Mark player absent from this week's RoW event",
                "`!present` — Remove a user's absence mark",
                "`!absentees` — Show all users marked absent",
                "`!exportteams` — Export current team signups to a text file",
                "`!exporthistory` — Export event history to a text file",
                "`!lockteams` — Lock team signups",
                "`!unlockteams` — Unlock team signups",
                "`!settime` — Set event time",
                "`!gettime` — Get event time",
                "`!notify` — Send notifications",
                "`!announce` — Make announcements",
                "`!notifications remind` — Send team reminders",
            ]

            # User commands
            user_commands = [
                "`!commands` — Show this command list",
                "`!setign` — Set your in-game name",
                "`!clearign` — Clear your stored IGN",
                "`!myign` — View your stored IGN",
                "`!events` — View current signups",
                "`!mystats` — View your personal statistics",
                "`!teams` — View current team compositions",
                "`!notifications settings` — Configure notification preferences",
                "`!notifications test` — Test notification delivery",
            ]

            # Create main embed for user and admin commands
            embed = discord.Embed(
                title="📜 Available Bot Commands", color=discord.Color.blurple()
            )

            embed.add_field(
                name="👤 User Commands", value="\n".join(user_commands), inline=False
            )

            if is_admin:
                embed.add_field(
                    name="🛡️ Admin Commands",
                    value="\n".join(admin_commands),
                    inline=False,
                )

            # Set footer based on permissions
            if is_owner:
                embed.set_footer(text="You have full access to all bot commands.")
            elif is_admin:
                embed.set_footer(
                    text="Admin commands are visible. Owner commands require bot owner permissions."
                )
            else:
                embed.set_footer(
                    text="Admin and owner commands are only visible if you have the required permissions."
                )

            await ctx.send(embed=embed)

            # Send separate embed for owner commands if user is owner
            if is_owner:
                # Split owner commands into chunks to avoid 1024 character limit
                owner_embed = discord.Embed(
                    title="👑 Owner Commands", 
                    color=discord.Color.gold(),
                    description="Commands exclusive to the bot owner:"
                )

                # Split commands into two groups for better organization
                data_commands = [cmd for cmd in owner_commands if any(keyword in cmd for keyword in ['json', 'backup', 'restore', 'data', 'migrate'])]
                sheets_commands = [cmd for cmd in owner_commands if any(keyword in cmd for keyword in ['sync', 'sheets', 'template', 'export', 'import'])]
                system_commands = [cmd for cmd in owner_commands if cmd not in data_commands and cmd not in sheets_commands]

                if data_commands:
                    owner_embed.add_field(
                        name="📁 Data Management",
                        value="\n".join(data_commands),
                        inline=False
                    )

                if sheets_commands:
                    owner_embed.add_field(
                        name="📊 Google Sheets",
                        value="\n".join(sheets_commands),
                        inline=False
                    )

                if system_commands:
                    owner_embed.add_field(
                        name="⚙️ System Control",
                        value="\n".join(system_commands),
                        inline=False
                    )

                owner_embed.set_footer(text="⚠️ Use owner commands with caution - they can affect the entire bot.")
                await ctx.send(embed=owner_embed)

        except Exception as e:
            await ctx.send(f"❌ Error in commands: {str(e)}")
            print(f"Commands error: {e}")

    @commands.command(name="test123")
    async def test_command(self, ctx):
        """Test command to verify the cog is loaded and responding."""
        await ctx.send("✅ User commands cog is working!")


async def setup(bot):
    """
    Set up the UserCommands cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(UserCommands(bot))
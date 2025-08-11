from datetime import datetime

import discord
from discord.ext import commands

from config.constants import FILES
from config.settings import ADMIN_ROLE_IDS
from utils.data_manager import DataManager


class Attendance(commands.Cog):
    """
    Manages RoW event attendance tracking and reporting.

    Features:
    - Track player absences with reasons
    - Remove absence marks
    - View current absentees
    - Sync attendance data with Google Sheets
    - Update player statistics for absences
    """

    def __init__(self, bot):
        """
        Initialize the Attendance cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.data_manager = DataManager()
        self.absent_data = self.load_absent_data()

    def load_absent_data(self):
        """
        Load absent data using DataManager.

        Returns:
            dict: Dictionary containing absence records
                  Format: {user_id: {reason, timestamp, marked_by}}
        """
        return self.data_manager.load_json(FILES["ABSENT"], {})

    def save_absent_data(self):
        """
        Save absent data and sync with Google Sheets.

        Updates player statistics to reflect absences.

        Returns:
            bool: True if save was successful, False otherwise
        """
        success = self.data_manager.save_json(
            FILES["ABSENT"], self.absent_data, sync_to_sheets=True
        )
        if success:
            # Update player stats for absents count
            for user_id in self.absent_data.keys():
                if user_id in self.data_manager.player_stats:
                    self.data_manager.player_stats[user_id]["absents"] = (
                        self.data_manager.player_stats[user_id].get("absents", 0) + 1
                    )
                else:
                    # Initialize player stats if not exists
                    self.data_manager.player_stats[user_id] = {
                        "name": f"User_{user_id}",
                        "team_results": {
                            "main_team": {"wins": 0, "losses": 0},
                            "team_2": {"wins": 0, "losses": 0},
                            "team_3": {"wins": 0, "losses": 0},
                        },
                        "absents": 1,
                        "blocked": False,
                    }
            self.data_manager.save_player_stats()
        else:
            print("❌ Failed to save absent data")
        return success

    @commands.command(name="absent")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def mark_absent(self, ctx, *, reason: str = "No reason provided"):
        """
        Mark player absent from this week's RoW event.

        Args:
            ctx: The command context
            reason: Reason for absence (optional)

        Requires:
            Admin role permissions

        Effects:
            - Records absence with timestamp and reason
            - Updates player statistics
            - Syncs with Google Sheets
        """
        user_id = str(ctx.author.id)
        self.absent_data[user_id] = {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "marked_by": str(ctx.author),
        }

        if self.save_absent_data():
            await ctx.send(
                f"✅ {ctx.author.mention} marked as absent. Reason: *{reason}*"
            )
            print(f"📌 {ctx.author} marked themselves absent. Reason: {reason}")
        else:
            await ctx.send("❌ Failed to save absence record. Please try again.")

    @commands.command(name="present")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def mark_present(self, ctx, member: discord.Member):
        """
        Remove a user's absence mark.

        Args:
            ctx: The command context
            member: The Discord member to mark as present

        Requires:
            Admin role permissions

        Effects:
            - Removes absence record
            - Updates player statistics
            - Syncs with Google Sheets
        """
        user_id = str(member.id)

        if user_id in self.absent_data:
            removed = self.absent_data.pop(user_id)
            if self.save_absent_data():
                await ctx.send(f"✅ Removed absence mark for {member.mention}")
                print(
                    f"🧹 {ctx.author} removed absence for {member} (was marked: {removed})"
                )
            else:
                await ctx.send("❌ Failed to save changes. Please try again.")
        else:
            await ctx.send(f"ℹ️ {member.mention} is not marked as absent.")

    @commands.command(name="absentees")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def show_absentees(self, ctx):
        """
        Show all users marked absent.

        Args:
            ctx: The command context

        Requires:
            Admin role permissions

        Displays:
            - List of absent users with mentions
            - Absence reasons
            - Who marked each absence
        """
        self.absent_data = self.load_absent_data()

        if not self.absent_data:
            await ctx.send("✅ No absentees recorded for this week.")
            return

        lines = []
        for uid, entry in self.absent_data.items():
            try:
                user = self.bot.get_user(int(uid))
                name = user.mention if user else f"<@{uid}>"
            except (ValueError, TypeError):
                name = f"Invalid User ID: {uid}"

            reason = entry.get("reason", "No reason")
            marked_by = entry.get("marked_by", "Unknown")
            lines.append(f"- {name} ({reason}) — marked by **{marked_by}**")

        embed = discord.Embed(
            title="📥 Absentees This Week",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """
    Set up the Attendance cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(Attendance(bot))

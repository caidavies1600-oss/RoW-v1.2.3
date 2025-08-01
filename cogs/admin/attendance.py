import discord
from discord.ext import commands
from datetime import datetime
from config.constants import FILES
from config.settings import ADMIN_ROLE_IDS
from utils.helpers import Helpers
from utils.data_manager import DataManager

class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()
        self.absent_data = self.load_absent_data()

    def load_absent_data(self):
        """Load absent data using DataManager."""
        return self.data_manager.load_json(FILES["ABSENT"], {})

    def save_absent_data(self):
        """Save absent data using DataManager."""
        success = self.data_manager.save_json(FILES["ABSENT"], self.absent_data)
        if not success:
            print(f"❌ Failed to save absent data")
        return success

    @commands.command(name="absent")
    @commands.has_any_role(*ADMIN_ROLE_IDS)  # Added admin restriction
    async def mark_absent(self, ctx, *, reason: str = "No reason provided"):
        """Mark player absent from this week's RoW event"""  # Updated description
        user_id = str(ctx.author.id)
        self.absent_data[user_id] = {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "marked_by": str(ctx.author)
        }
        
        if self.save_absent_data():
            await ctx.send(f"✅ {ctx.author.mention} marked as absent. Reason: *{reason}*")
            print(f"📌 {ctx.author} marked themselves absent. Reason: {reason}")
        else:
            await ctx.send("❌ Failed to save absence record. Please try again.")

    @commands.command(name="present")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def mark_present(self, ctx, member: discord.Member):
        """Remove a user's absence mark."""
        user_id = str(member.id)

        if user_id in self.absent_data:
            removed = self.absent_data.pop(user_id)
            if self.save_absent_data():
                await ctx.send(f"✅ Removed absence mark for {member.mention}")
                print(f"🧹 {ctx.author} removed absence for {member} (was marked: {removed})")
            else:
                await ctx.send("❌ Failed to save changes. Please try again.")
        else:
            await ctx.send(f"ℹ️ {member.mention} is not marked as absent.")

    @commands.command(name="absentees")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def show_absentees(self, ctx):
        """Show all users marked absent."""
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
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Attendance(bot))
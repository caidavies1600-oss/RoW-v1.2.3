import discord
from discord.ext import commands
import os
import json
from datetime import datetime
from config.constants import ADMIN_ROLE_IDS, FILES
from utils.helpers import Helpers


def load_absent_data():
    path = FILES["ABSENT"]
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load absent data: {e}")
        return {}


def save_absent_data(data):
    path = FILES["ABSENT"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to save absent data: {e}")


class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.absent_data = load_absent_data()

    @commands.command(name="absent")
    async def mark_absent(self, ctx, *, reason: str = "No reason provided"):
        """Mark yourself as absent from this week's RoW event."""
        user_id = str(ctx.author.id)
        self.absent_data[user_id] = {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "marked_by": str(ctx.author)
        }
        save_absent_data(self.absent_data)

        await ctx.send(f"✅ {ctx.author.mention} marked as absent. Reason: *{reason}*")
        print(f"📌 {ctx.author} marked themselves absent. Reason: {reason}")

    @commands.command(name="present")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def mark_present(self, ctx, member: discord.Member):
        """Remove a user's absence mark."""
        user_id = str(member.id)

        if user_id in self.absent_data:
            removed = self.absent_data.pop(user_id)
            save_absent_data(self.absent_data)
            await ctx.send(f"✅ Removed absence mark for {member.mention}")
            print(f"🧹 {ctx.author} removed absence for {member} (was marked: {removed})")
        else:
            await ctx.send(f"ℹ️ {member.mention} is not marked as absent.")

    @commands.command(name="absentees")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def show_absentees(self, ctx):
        """Show all users marked absent."""
        if not self.absent_data:
            await ctx.send("✅ No absentees recorded for this week.")
            return

        lines = []
        for uid, entry in self.absent_data.items():
            user = self.bot.get_user(int(uid))
            name = user.mention if user else f"<@{uid}>"
            reason = entry.get("reason", "No reason")
            marked_by = entry.get("marked_by", "Unknown")
            time = Helpers.format_time_remaining(entry.get("timestamp", ""))
            lines.append(f"- {name} ({reason}) — marked by **{marked_by}**")

        embed = discord.Embed(
            title="📥 Absentees This Week",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Attendance(bot))

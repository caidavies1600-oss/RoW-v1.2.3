import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta

from utils.logger import setup_logger
from config.constants import ADMIN_ROLE_IDS, FILES, TEAM_DISPLAY, BOT_ADMIN_USER_ID, ALERT_CHANNEL_ID
from utils.helpers import Helpers

logger = setup_logger(“admin_actions”)

class AdminActions(commands.Cog):
def **init**(self, bot):
self.bot = bot
self.blocked_file = FILES[“BLOCKED”]
self.history_file = FILES[“HISTORY”]
self.results_file = FILES[“RESULTS”]

```
def load_results(self):
    if os.path.exists(self.results_file):
        with open(self.results_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Results file corrupted, resetting.")
    return {"wins": 0, "losses": 0, "history": []}

def load_blocked_users(self):
    if os.path.exists(self.blocked_file):
        try:
            with open(self.blocked_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"❌ Failed to load blocked users: {e}")
    return {}

def save_blocked_users(self, data):
    try:
        os.makedirs(os.path.dirname(self.blocked_file), exist_ok=True)
        with open(self.blocked_file, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"❌ Failed to save blocked users: {e}")

@commands.command()
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def block(self, ctx, member: discord.Member, days: int):
    """Block a user from signing up for a number of days."""
    user_id = str(member.id)
    blocked_by = ctx.author.name
    blocked_at = datetime.utcnow().isoformat()
    duration = max(days, 1)

    data = self.load_blocked_users()
    data[user_id] = {
        "blocked_by": blocked_by,
        "blocked_at": blocked_at,
        "ban_duration_days": duration
    }
    self.save_blocked_users(data)

    # Calculate time remaining properly
    blocked_time = datetime.fromisoformat(blocked_at)
    expiry_time = blocked_time + timedelta(days=duration)
    remaining = expiry_time - datetime.utcnow()

    if remaining.total_seconds() > 0:
        days_left = remaining.days
        hours_left = remaining.seconds // 3600
        time_text = f"{days_left}d {hours_left}h" if days_left > 0 else f"{hours_left}h"
    else:
        time_text = "Expired"

    # Send confirmation to the channel
    await ctx.send(f"✅ {member.mention} has been blocked for `{duration}` day(s).")

    # DM bot admin
    try:
        admin = self.bot.get_user(BOT_ADMIN_USER_ID)
        if admin:
            embed = discord.Embed(
                title="🚫 User Blocked",
                description=f"**{member}** has been blocked from RoW signups.",
                color=discord.Color.red()
            )
            embed.add_field(name="Nickname", value=member.display_name, inline=True)
            embed.add_field(name="Duration", value=f"{duration} days", inline=True)
            embed.add_field(name="Blocked By", value=ctx.author.mention, inline=True)
            embed.add_field(name="Time Remaining", value=time_text, inline=False)
            await admin.send(embed=embed)
    except Exception as e:
        logger.warning(f"Failed to DM bot admin: {e}")

    logger.info(f"{ctx.author} blocked {member} for {duration} days")

@commands.command()
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def unblock(self, ctx, member: discord.Member):
    """Unblock a user manually."""
    user_id = str(member.id)
    data = self.load_blocked_users()

    if user_id not in data:
        await ctx.send("⚠️ That user is not currently blocked.")
        return

    del data[user_id]
    self.save_blocked_users(data)

    await ctx.send(f"✅ {member.mention} has been unblocked.")
    logger.info(f"{ctx.author} manually unblocked {member}")

    # DM bot admin
    try:
        admin = self.bot.get_user(BOT_ADMIN_USER_ID)
        if admin:
            embed = discord.Embed(
                title="✅ User Unblocked (Manual)",
                description=f"**{member}** has been manually unblocked.",
                color=discord.Color.green()
            )
            embed.add_field(name="Unblocked By", value=ctx.author.mention, inline=True)
            await admin.send(embed=embed)
    except Exception as e:
        logger.warning(f"Failed to DM bot admin: {e}")

    # Announce in alert channel
    try:
        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if channel:
            await channel.send(f"✅ {member.mention} has been unblocked.")
    except Exception as e:
        logger.warning(f"Failed to send unblock alert: {e}")

@commands.command(name="blocklist")
async def blocklist(self, ctx):
    """List all currently blocked users and remaining ban time."""
    data = self.load_blocked_users()
    if not data:
        await ctx.send("✅ No users are currently blocked.")
        return

    lines = []
    for user_id, info in data.items():
        user = ctx.guild.get_member(int(user_id)) or await self.bot.fetch_user(int(user_id))
        name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{user_id}>"

        # Calculate time remaining properly
        blocked_at = info.get("blocked_at")
        duration = info.get("ban_duration_days", 7)

        if blocked_at:
            try:
                blocked_time = datetime.fromisoformat(blocked_at)
                expiry_time = blocked_time + timedelta(days=duration)
                remaining = expiry_time - datetime.utcnow()

                if remaining.total_seconds() > 0:
                    days_left = remaining.days
                    hours_left = remaining.seconds // 3600
                    time_left = f"{days_left}d {hours_left}h" if days_left > 0 else f"{hours_left}h"
                else:
                    time_left = "Expired"
            except:
                time_left = "Invalid"
        else:
            time_left = "Unknown"

        lines.append(f"{name} - `{time_left}`")

    embed = discord.Embed(
        title=f"🚫 Blocked Users ({len(lines)})",
        description="\n".join(lines),
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@commands.command()
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def rowstats(self, ctx):
    """Show RoW stats with team signups, results, and blocks."""
    try:
        event_cog = self.bot.get_cog("EventManager")
        profile_cog = self.bot.get_cog("Profile")

        if not event_cog:
            await ctx.send("❌ Event system not available.")
            return

        results = self.load_results()
        wins = results.get("wins", 0)
        losses = results.get("losses", 0)
        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

        # Team signups with IGNs
        team_fields = []
        for team, members in event_cog.events.items():
            igns = []
            for uid in members:
                try:
                    user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
                    if profile_cog and user:
                        ign = profile_cog.get_ign(user)
                    else:
                        ign = user.display_name if user else "Unknown"

                    name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
                    igns.append(f"{name} (`{ign}`)")
                except:
                    igns.append(f"<@{uid}> (`Unknown`)")

            team_display = TEAM_DISPLAY.get(team, team.replace("_", " ").title())
            value = "\n".join(igns) if igns else "No members"
            team_fields.append((team_display, f"**{len(igns)} signed up**\n{value}"))

        # Blocked users
        blocked_info = []
        for uid, info in self.load_blocked_users().items():
            try:
                user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
                name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"

                # Calculate time remaining
                blocked_at = info.get("blocked_at")
                duration = info.get("ban_duration_days", 7)

                if blocked_at:
                    try:
                        blocked_time = datetime.fromisoformat(blocked_at)
                        expiry_time = blocked_time + timedelta(days=duration)
                        remaining = expiry_time - datetime.utcnow()

                        if remaining.total_seconds() > 0:
                            days_left = remaining.days
                            hours_left = remaining.seconds // 3600
                            time_left = f"{days_left}d {hours_left}h" if days_left > 0 else f"{hours_left}h"
                        else:
                            time_left = "Expired"
                    except:
                        time_left = "Invalid"
                else:
                    time_left = "Unknown"

                blocked_info.append(f"{name} - `{time_left}` remaining")
            except:
                blocked_info.append(f"<@{uid}> - `Unknown` remaining")

        # Event trends and results
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                try:
                    history = json.load(f)
                    if not isinstance(history, list):
                        history = []
                except json.JSONDecodeError:
                    history = []
        else:
            history = []

        trend_lines = []
        for entry in history[-5:]:
            date = entry.get("timestamp", "").split("T")[0]
            team_data = entry.get("teams", {})
            parts = [f"`{date}`:"]
            for key in ["main_team", "team_2", "team_3"]:
                name = TEAM_DISPLAY.get(key, key.title())
                count = len(team_data.get(key, []))
                parts.append(f"{name}: {count}")
            trend_lines.append(" | ".join(parts))

        result_lines = []
        for entry in results.get("history", [])[-5:]:
            date = entry.get("timestamp", "").split("T")[0]
            result = entry.get("result", "loss")
            team_key = entry.get("team", "Unknown")
            emoji = "🏆" if result == "win" else "💔"
            display = TEAM_DISPLAY.get(team_key, team_key.title())
            result_lines.append(f"`{date}`: {emoji} {display}")

        embed = discord.Embed(title="📊 RoW Stats Report", color=discord.Color.blurple())

        for name, value in team_fields:
            embed.add_field(name=name, value=value, inline=False)

        embed.add_field(name=f"🚫 Blocked Users ({len(blocked_info)})",
                        value="\n".join(blocked_info) or "None", inline=False)

        embed.add_field(name="📈 Event Trends (Last 5)",
                        value="\n".join(trend_lines) or "No history available.", inline=False)

        embed.add_field(name="📉 Recent Results",
                        value="\n".join(result_lines) or "No recent results.", inline=False)

        embed.add_field(name="📊 Overall Record",
                        value=f"🏆 {wins} Wins | 💔 {losses} Losses\n📈 Win Rate: `{win_rate:.1f}%`",
                        inline=False)

        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} requested !rowstats")

    except Exception as e:
        logger.exception("Error in !rowstats command:")
        await ctx.send("❌ Failed to generate stats report.")
```

# Required setup

async def setup(bot):
await bot.add_cog(AdminActions(bot))
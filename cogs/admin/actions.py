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
    return {"total_wins": 0, "total_losses": 0, "history": []}

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

    time_text = Helpers.format_time_remaining(data[user_id])

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
        user = ctx.guild.get_member(int(user_id))
        if not user:
            try:
                user = await self.bot.fetch_user(int(user_id))
            except:
                user = None

        name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{user_id}>"
        time_left = Helpers.format_time_remaining(info)
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

        if not event_cog or not profile_cog:
            await ctx.send("❌ Event or profile system not available.")
            return

        results = self.load_results()
        wins = results.get("total_wins", 0)
        losses = results.get("total_losses", 0)
        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

        # Team signups with IGNs
        team_fields = []
        for team, members in event_cog.events.items():
            igns = []
            for uid in members:
                try:
                    user = ctx.guild.get_member(int(uid))
                    if not user:
                        user = await self.bot.fetch_user(int(uid))

                    ign = profile_cog.get_ign(user) if user else "Unknown"
                    name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
                    igns.append(f"{name} (`{ign}`)")
                except Exception as e:
                    logger.warning(f"Failed to get user info for {uid}: {e}")
                    igns.append(f"<@{uid}> (`Unknown`)")

            team_display = TEAM_DISPLAY.get(team, team.replace("_", " ").title())
            value = "\n".join(igns) if igns else "No members"
            team_fields.append((team_display, f"**{len(igns)} signed up**\n{value}"))

        # Blocked users
        blocked_info = []
        for uid, info in self.load_blocked_users().items():
            try:
                user = ctx.guild.get_member(int(uid))
                if not user:
                    user = self.bot.get_user(int(uid))
                name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
            except:
                name = f"<@{uid}>"

            time_left = Helpers.format_time_remaining(info)
            blocked_info.append(f"{name} - `{time_left}` remaining")

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

@commands.command()
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def backup(self, ctx):
    """Create a manual backup of all data files."""
    try:
        import shutil
        from datetime import datetime

        backup_dir = f"data/backups/manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)

        files_backed_up = []
        for file_key, file_path in FILES.items():
            if os.path.exists(file_path):
                backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                shutil.copy2(file_path, backup_path)
                files_backed_up.append(os.path.basename(file_path))

        if files_backed_up:
            embed = discord.Embed(
                title="💾 Manual Backup Complete",
                description=f"Backed up {len(files_backed_up)} files to `{backup_dir}`",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Files Backed Up",
                value="\n".join([f"• {f}" for f in files_backed_up]),
                inline=False
            )
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} created manual backup: {backup_dir}")
        else:
            await ctx.send("⚠️ No data files found to backup.")

    except Exception as e:
        logger.exception("Error creating manual backup:")
        await ctx.send("❌ Failed to create backup.")

@commands.command()
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def testchannels(self, ctx):
    """Test channel access and permissions."""
    try:
        embed = discord.Embed(
            title="🔍 Channel Access Test",
            color=discord.Color.blue()
        )

        # Test alert channel
        alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            try:
                # Test if we can send messages
                perms = alert_channel.permissions_for(ctx.guild.me)
                can_send = perms.send_messages and perms.embed_links

                embed.add_field(
                    name="📢 Alert Channel",
                    value=f"✅ Found: {alert_channel.mention}\n{'✅' if can_send else '❌'} Can send messages",
                    inline=False
                )
            except Exception as e:
                embed.add_field(
                    name="📢 Alert Channel", 
                    value=f"❌ Error checking permissions: {str(e)[:100]}",
                    inline=False
                )
        else:
            embed.add_field(
                name="📢 Alert Channel",
                value=f"❌ Channel with ID {ALERT_CHANNEL_ID} not found",
                inline=False
            )

        # Test current channel permissions
        current_perms = ctx.channel.permissions_for(ctx.guild.me)
        embed.add_field(
            name="📝 Current Channel Permissions",
            value=f"{'✅' if current_perms.send_messages else '❌'} Send Messages\n"
                  f"{'✅' if current_perms.embed_links else '❌'} Embed Links\n"
                  f"{'✅' if current_perms.attach_files else '❌'} Attach Files\n"
                  f"{'✅' if current_perms.add_reactions else '❌'} Add Reactions",
            inline=False
        )

        # Test bot admin user
        admin_user = self.bot.get_user(BOT_ADMIN_USER_ID)
        embed.add_field(
            name="👤 Bot Admin User",
            value=f"{'✅' if admin_user else '❌'} Admin user accessible: {admin_user or 'Not found'}",
            inline=False
        )

        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} ran channel access test")

    except Exception as e:
        logger.exception("Error in testchannels command:")
        await ctx.send("❌ Failed to run channel test.")
```

# Required setup

async def setup(bot):
await bot.add_cog(AdminActions(bot))
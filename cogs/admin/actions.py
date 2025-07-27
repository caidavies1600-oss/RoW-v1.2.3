            import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta

            from utils.logger import setup_logger
            from config.constants import FILES, TEAM_DISPLAY
            from config.settings import ADMIN_ROLE_IDS, BOT_ADMIN_USER_ID, ALERT_CHANNEL_ID
            from utils.helpers import Helpers

            logger = setup_logger("admin_actions")

            class AdminActions(commands.Cog):
                def __init__(self, bot):
                    self.bot = bot
                    self.blocked_file = FILES["BLOCKED"]
                    self.history_file = FILES["HISTORY"]
                    self.results_file = FILES["RESULTS"]

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

                    time_text = Helpers.format_time_remaining(blocked_at)

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
                        time_left = Helpers.format_time_remaining(info.get("blocked_at", ""))
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
                                    user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
                                    ign = profile_cog.get_ign(user) if user else "Unknown"
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

                                blocked_at = datetime.fromisoformat(info.get("blocked_at", ""))
                                duration = info.get("ban_duration_days", 0)
                                expiry = blocked_at + timedelta(days=duration)
                                remaining = expiry - datetime.utcnow()

                                if remaining.total_seconds() > 0:
                                    days_left = remaining.days
                                    hours_left = remaining.seconds // 3600
                                    time_left = f"{days_left}d {hours_left}h remaining"
                                else:
                                    time_left = "Expired"

                                blocked_info.append(f"{name} - `{time_left}`")
                            except:
                                blocked_info.append(f"<@{uid}> - `Error`")

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

                @commands.command(name="checkjson")
                @commands.has_any_role(*ADMIN_ROLE_IDS)
                async def check_json(self, ctx):
                    """Check all JSON files for errors and display their status."""
                    embed = discord.Embed(
                        title="🔍 JSON File Status Check",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )

                    files_to_check = {
                        "Events": FILES["EVENTS"],
                        "Blocked Users": FILES["BLOCKED"],
                        "IGN Map": FILES["IGN_MAP"],
                        "Results": FILES["RESULTS"],
                        "History": FILES["HISTORY"],
                        "Row Times": FILES["TIMES"],
                        "Absent Users": FILES["ABSENT"]
                    }

                    all_good = True

                    for name, filepath in files_to_check.items():
                        status = "✅"
                        message = "Valid JSON"

                        if not os.path.exists(filepath):
                            status = "⚠️"
                            message = "File does not exist"
                            all_good = False
                        else:
                            try:
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    data = json.load(f)

                                # Get file size
                                size = os.path.getsize(filepath)
                                size_str = f"{size:,} bytes"

                                # Get entry count based on data type
                                if isinstance(data, dict):
                                    count = len(data)
                                    message = f"Valid JSON ({count} entries, {size_str})"
                                elif isinstance(data, list):
                                    count = len(data)
                                    message = f"Valid JSON ({count} items, {size_str})"
                                else:
                                    message = f"Valid JSON ({type(data).__name__}, {size_str})"

                            except json.JSONDecodeError as e:
                                status = "❌"
                                message = f"Invalid JSON: {str(e)}"
                                all_good = False
                            except Exception as e:
                                status = "❌"
                                message = f"Error: {str(e)}"
                                all_good = False

                        embed.add_field(
                            name=f"{status} {name}",
                            value=f"`{os.path.basename(filepath)}`\n{message}",
                            inline=False
                        )

                    # Add summary
                    if all_good:
                        embed.description = "✅ All JSON files are valid and accessible!"
                        embed.color = discord.Color.green()
                    else:
                        embed.description = "⚠️ Some JSON files have issues. See details below."
                        embed.color = discord.Color.orange()

                    embed.set_footer(text=f"Requested by {ctx.author}")
                    await ctx.send(embed=embed)
                    logger.info(f"{ctx.author} ran !checkjson command")

            # Required setup
            async def setup(bot):
                await bot.add_cog(AdminActions(bot))
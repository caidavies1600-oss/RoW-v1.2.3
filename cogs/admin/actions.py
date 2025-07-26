
import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta

from utils.logger import setup_logger
from config.constants import ADMIN_ROLE_IDS, FILES, TEAM_DISPLAY, BOT_ADMIN_USER_ID, ALERT_CHANNEL_ID
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
        return {"total_wins": 0, "total_losses": 0, "history": []}

    def save_results(self, data):
        try:
            os.makedirs(os.path.dirname(self.results_file), exist_ok=True)
            with open(self.results_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

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
                embed.add_field(name="Time Remaining", value=f"{duration} days", inline=False)
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
            try:
                user = ctx.guild.get_member(int(user_id)) or await self.bot.fetch_user(int(user_id))
                name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{user_id}>"
            except:
                name = f"<@{user_id}>"

            blocked_at = info.get("blocked_at", "")
            duration = info.get("ban_duration_days", 0)
            time_left = Helpers.days_until_expiry(blocked_at, duration)
            lines.append(f"{name} - `{time_left} days remaining`")

        embed = discord.Embed(
            title=f"🚫 Blocked Users ({len(lines)})",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def win(self, ctx, team_key: str):
        """Record a win for a team."""
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
            return

        results = self.load_results()
        results["total_wins"] = results.get("total_wins", 0) + 1

        # Add to history
        if "history" not in results:
            results["history"] = []

        results["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": "win",
            "team": team_key,
            "recorded_by": str(ctx.author)
        })

        self.save_results(results)
        team_display = TEAM_DISPLAY.get(team_key, team_key)
        await ctx.send(f"🏆 Win recorded for **{team_display}**!")
        logger.info(f"{ctx.author} recorded win for {team_key}")

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def loss(self, ctx, team_key: str):
        """Record a loss for a team."""
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
            return

        results = self.load_results()
        results["total_losses"] = results.get("total_losses", 0) + 1

        # Add to history
        if "history" not in results:
            results["history"] = []

        results["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": "loss",
            "team": team_key,
            "recorded_by": str(ctx.author)
        })

        self.save_results(results)
        team_display = TEAM_DISPLAY.get(team_key, team_key)
        await ctx.send(f"💔 Loss recorded for **{team_display}**.")
        logger.info(f"{ctx.author} recorded loss for {team_key}")

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def results(self, ctx):
        """Show win/loss results summary."""
        results = self.load_results()
        total_wins = results.get("total_wins", 0)
        total_losses = results.get("total_losses", 0)
        total_games = total_wins + total_losses
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

        embed = discord.Embed(
            title="🏆 RoW Results Summary",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📊 Overall Record",
            value=f"**Wins:** {total_wins}\n**Losses:** {total_losses}\n**Win Rate:** {win_rate:.1f}%",
            inline=False
        )

        # Recent results
        recent = results.get("history", [])[-10:]
        if recent:
            recent_text = ""
            for result in reversed(recent):
                date = result.get("timestamp", "").split("T")[0]
                team = TEAM_DISPLAY.get(result.get("team", ""), "Unknown")
                outcome = "🏆" if result.get("result") == "win" else "💔"
                recent_text += f"{outcome} {team} - {date}\n"

            embed.add_field(
                name="📅 Recent Results (Last 10)",
                value=recent_text or "No recent results",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def rowstats(self, ctx):
        """Show comprehensive RoW stats with team signups, results, and blocks."""
        try:
            event_cog = self.bot.get_cog("EventManager")
            profile_cog = self.bot.get_cog("Profile")

            if not event_cog:
                await ctx.send("❌ Event system not available.")
                return

            results = self.load_results()
            wins = results.get("total_wins", 0)
            losses = results.get("total_losses", 0)
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

            embed = discord.Embed(title="📊 Comprehensive RoW Stats Report", color=discord.Color.blurple())

            # Team signups with IGNs
            for team, members in event_cog.events.items():
                igns = []
                for member in members:
                    # Handle both user IDs and IGNs
                    if isinstance(member, int):
                        try:
                            user = ctx.guild.get_member(member) or await self.bot.fetch_user(member)
                            if user and profile_cog and profile_cog.has_ign(user):
                                ign = profile_cog.get_ign(user)
                                name = user.display_name if hasattr(user, 'display_name') else user.name
                                igns.append(f"{name} (`{ign}`)")
                            else:
                                name = user.display_name if user and hasattr(user, 'display_name') else user.name if user else f"User_{member}"
                                igns.append(f"{name}")
                        except:
                            igns.append(f"<@{member}> (Left server)")
                    else:
                        # Already an IGN string
                        igns.append(str(member))

                team_display = TEAM_DISPLAY.get(team, team.replace("_", " ").title())
                value = "\n".join(igns[:15]) if igns else "No members"
                if len(igns) > 15:
                    value += f"\n... and {len(igns) - 15} more"

                embed.add_field(
                    name=f"{team_display} ({len(igns)} signed up)",
                    value=value,
                    inline=False
                )

            # Blocked users
            blocked_info = []
            blocked_data = self.load_blocked_users()
            for uid, info in blocked_data.items():
                try:
                    user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
                    name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
                except:
                    name = f"<@{uid}>"

                blocked_at = info.get("blocked_at", "")
                duration = info.get("ban_duration_days", 0)
                time_left = Helpers.days_until_expiry(blocked_at, duration)
                blocked_by = info.get("blocked_by", "Unknown")
                blocked_info.append(f"{name} - `{time_left} days` (by {blocked_by})")

            embed.add_field(
                name=f"🚫 Blocked Users ({len(blocked_info)})",
                value="\n".join(blocked_info) or "None",
                inline=False
            )

            # Event history trends
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

            embed.add_field(
                name="📈 Event Trends (Last 5 Events)",
                value="\n".join(trend_lines) or "No history available",
                inline=False
            )

            # Recent match results
            result_lines = []
            for entry in results.get("history", [])[-5:]:
                date = entry.get("timestamp", "").split("T")[0]
                result = entry.get("result", "loss")
                team_key = entry.get("team", "Unknown")
                recorded_by = entry.get("recorded_by", "Unknown")
                emoji = "🏆" if result == "win" else "💔"
                display = TEAM_DISPLAY.get(team_key, team_key.title())
                result_lines.append(f"`{date}`: {emoji} {display} (by {recorded_by})")

            embed.add_field(
                name="📉 Recent Match Results",
                value="\n".join(result_lines) or "No recent results",
                inline=False
            )

            # Overall statistics
            embed.add_field(
                name="📊 Overall Record",
                value=f"🏆 **{wins}** Wins | 💔 **{losses}** Losses\n📈 Win Rate: **{win_rate:.1f}%**\n📅 Total Events: **{len(history)}**",
                inline=False
            )

            # Absence tracking
            try:
                from cogs.admin.attendance import load_absent_data
                absent_data = load_absent_data()
                if absent_data:
                    absent_lines = []
                    for user_id, info in list(absent_data.items())[:5]:
                        try:
                            user = ctx.guild.get_member(int(user_id)) or self.bot.get_user(int(user_id))
                            name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{user_id}>"
                        except:
                            name = f"<@{user_id}>"
                        reason = info.get("reason", "No reason")
                        marked_by = info.get("marked_by", "Unknown")
                        absent_lines.append(f"{name} - {reason} (by {marked_by})")

                    embed.add_field(
                        name=f"🔁 Currently Absent ({len(absent_data)})",
                        value="\n".join(absent_lines) or "None",
                        inline=False
                    )
            except ImportError:
                pass

            embed.set_footer(text=f"Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} requested comprehensive !rowstats")

        except Exception as e:
            logger.exception("Error in !rowstats command:")
            await ctx.send("❌ Failed to generate comprehensive stats report.")

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def clearresults(self, ctx):
        """Clear all win/loss results (with confirmation)."""
        embed = discord.Embed(
            title="⚠️ Clear All Results?",
            description="This will permanently delete ALL win/loss records. React with ✅ to confirm.",
            color=discord.Color.red()
        )

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

            if str(reaction.emoji) == "✅":
                # Clear results
                self.save_results({"total_wins": 0, "total_losses": 0, "history": []})
                await ctx.send("✅ All results have been cleared.")
                logger.info(f"{ctx.author} cleared all results")
            else:
                await ctx.send("❌ Results clearing cancelled.")

        except TimeoutError:
            await ctx.send("⏰ Confirmation timed out. Results not cleared.")

# Required setup function
async def setup(bot):
    await bot.add_cog(AdminActions(bot))

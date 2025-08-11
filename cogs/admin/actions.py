import json
import os
from datetime import datetime

import discord
from discord.ext import commands

from config.constants import (  # Fixed import
    ADMIN_ROLE_IDS,
    ALERT_CHANNEL_ID,
    BOT_ADMIN_USER_ID,
    FILES,
    TEAM_DISPLAY,
)
from utils.helpers import Helpers
from utils.logger import setup_logger
from utils.validators import validate_days

logger = setup_logger("admin_actions")


class AdminActions(commands.Cog):
    """
    Administrative actions for managing user blocks and RoW event statistics.
    Provides commands for blocking/unblocking users and viewing event stats.
    """

    def __init__(self, bot):
        """
        Initialize the AdminActions cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.blocked_file = FILES["BLOCKED"]
        self.history_file = FILES["HISTORY"]
        self.results_file = FILES["RESULTS"]

    def load_results(self):
        """
        Load event results from the results file.

        Returns:
            dict: Dictionary containing wins, losses, and history data
        """
        if os.path.exists(self.results_file):
            with open(self.results_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Results file corrupted, resetting.")
        return {"wins": 0, "losses": 0, "history": []}

    def load_blocked_users(self):
        """
        Load the list of currently blocked users from file.

        Returns:
            dict: Dictionary of blocked users and their block information
        """
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
        """
        Save blocked users data to file.

        Args:
            data (dict): Dictionary containing blocked users information
        """
        try:
            os.makedirs(os.path.dirname(self.blocked_file), exist_ok=True)
            with open(self.blocked_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"❌ Failed to save blocked users: {e}")

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.cooldown(3, 300, commands.BucketType.guild)
    async def block(self, ctx, member: discord.Member, days: int):
        """
        Block a user from signing up for RoW events.

        Args:
            ctx: The command context
            member: The Discord member to block
            days: Number of days to block the user (minimum 1)

        Requires:
            Admin role permissions

        Effects:
            - Blocks user from RoW signups
            - Notifies the blocked user
            - Sends confirmation to admin channel
            - DMs bot admin
        """
        # Validate inputs
        valid_days, error = validate_days(days)
        if not valid_days:
            await ctx.send(MESSAGES["INVALID_INPUT"].format(detail=error))
            return

        user_id = str(member.id)
        blocked_by = ctx.author.name
        blocked_at = datetime.utcnow().isoformat()
        duration = max(days, 1)

        data = self.load_blocked_users()
        data[user_id] = {
            "blocked_by": blocked_by,
            "blocked_at": blocked_at,
            "ban_duration_days": duration,
        }
        self.save_blocked_users(data)

        time_text = Helpers.days_until_expiry(blocked_at, duration)

        # Send confirmation to the channel
        await ctx.send(f"✅ {member.mention} has been blocked for `{duration}` day(s).")

        # DM bot admin
        try:
            admin = self.bot.get_user(BOT_ADMIN_USER_ID)
            if admin:
                embed = discord.Embed(
                    title="🚫 User Blocked",
                    description=f"**{member}** has been blocked from RoW signups.",
                    color=discord.Color.red(),
                )
                embed.add_field(name="Nickname", value=member.display_name, inline=True)
                embed.add_field(name="Duration", value=f"{duration} days", inline=True)
                embed.add_field(
                    name="Blocked By", value=ctx.author.mention, inline=True
                )
                embed.add_field(
                    name="Days Remaining", value=f"{time_text} days", inline=False
                )
                await admin.send(embed=embed)
        except Exception as e:
            logger.warning(f"Failed to DM bot admin: {e}")

        logger.info(f"{ctx.author} blocked {member} for {duration} days")

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def unblock(self, ctx, member: discord.Member):
        """
        Manually unblock a user from RoW events.

        Args:
            ctx: The command context
            member: The Discord member to unblock

        Requires:
            Admin role permissions

        Effects:
            - Removes user from block list
            - Notifies the unblocked user
            - Sends confirmation to admin channel
            - DMs bot admin
        """
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
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="Unblocked By", value=ctx.author.mention, inline=True
                )
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
        """
        Display all currently blocked users and their remaining ban time.

        Args:
            ctx: The command context

        Shows:
            - List of blocked users
            - Remaining days for each block
            - User nicknames/mentions
        """
        data = self.load_blocked_users()
        if not data:
            await ctx.send("✅ No users are currently blocked.")
            return

        lines = []
        for user_id, info in data.items():
            user = ctx.guild.get_member(int(user_id)) or await self.bot.fetch_user(
                int(user_id)
            )
            name = (
                user.display_name
                if isinstance(user, discord.Member)
                else user.name
                if user
                else f"<@{user_id}>"
            )
            blocked_at = info.get("blocked_at", "")
            duration = info.get("ban_duration_days", 0)
            time_left = Helpers.days_until_expiry(blocked_at, duration)
            lines.append(f"{name} - `{time_left} days left`")

        embed = discord.Embed(
            title=f"🚫 Blocked Users ({len(lines)})",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def rowstats(self, ctx):
        """
        Display comprehensive RoW event statistics.

        Args:
            ctx: The command context

        Requires:
            Admin role permissions

        Shows:
            - Current team signups and IGNs
            - List of blocked users
            - Event participation trends
            - Recent event results
            - Overall win/loss record
        """
        try:
            event_cog = self.bot.get_cog("EventManager")
            profile_cog = self.bot.get_cog("Profile")

            if not event_cog or not profile_cog:
                await ctx.send("❌ Event or profile system not available.")
                return

            results = self.load_results()
            wins = results.get("wins", 0)
            losses = results.get("losses", 0)
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

            # Team signups with IGNs
            team_fields = []
            for team, members in event_cog.events.items():
                igns = []
                for member_ign in members:
                    # members should already be IGN strings, not user IDs
                    igns.append(f"{member_ign}")

                team_display = TEAM_DISPLAY.get(team, team.replace("_", " ").title())
                value = "\n".join(igns) if igns else "No members"
                team_fields.append(
                    (team_display, f"**{len(igns)} signed up**\n{value}")
                )

            # Blocked users
            blocked_info = []
            for uid, info in self.load_blocked_users().items():
                user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
                name = (
                    user.display_name
                    if isinstance(user, discord.Member)
                    else user.name
                    if user
                    else f"<@{uid}>"
                )
                blocked_at = info.get("blocked_at", "")
                duration = info.get("ban_duration_days", 0)
                time_left = Helpers.days_until_expiry(blocked_at, duration)
                blocked_info.append(f"{name} - `{time_left} days left`")

            # Event trends and results
            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as f:
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

            embed = discord.Embed(
                title="📊 RoW Stats Report", color=discord.Color.blurple()
            )

            for name, value in team_fields:
                embed.add_field(name=name, value=value, inline=False)

            embed.add_field(
                name=f"🚫 Blocked Users ({len(blocked_info)})",
                value="\n".join(blocked_info) or "None",
                inline=False,
            )

            embed.add_field(
                name="📈 Event Trends (Last 5)",
                value="\n".join(trend_lines) or "No history available.",
                inline=False,
            )

            embed.add_field(
                name="📉 Recent Results",
                value="\n".join(result_lines) or "No recent results.",
                inline=False,
            )

            embed.add_field(
                name="📊 Overall Record",
                value=f"🏆 {wins} Wins | 💔 {losses} Losses\n📈 Win Rate: `{win_rate:.1f}%`",
                inline=False,
            )

            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} requested !rowstats")

        except Exception:
            logger.exception("Error in !rowstats command:")
            await ctx.send("❌ Failed to generate stats report.")


# Required setup
async def setup(bot):
    """
    Set up the AdminActions cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(AdminActions(bot))

    import discord
    from discord.ext import commands
    import json
    import os
    from datetime import datetime, timedelta

    from utils.logger import setup_logger
    from utils.data_manager import DataManager
    from config.constants import ADMIN_ROLE_IDS, FILES, TEAM_DISPLAY, COLORS, EMOJIS
    from config.settings import BOT_ADMIN_USER_ID, ALERT_CHANNEL_ID
    from utils.helpers import Helpers

    logger = setup_logger("admin_actions")


    class AdminActions(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.data_manager = DataManager()

        @commands.command(name="checkjson")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def check_json(self, ctx):
            """Check all JSON files for errors and display their status."""
            embed = discord.Embed(
                title="🔍 JSON File Status Check",
                color=COLORS["INFO"],
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
                status = EMOJIS["SUCCESS"]
                message = "Valid JSON"

                if not os.path.exists(filepath):
                    status = EMOJIS["WARNING"]
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
                        status = EMOJIS["ERROR"]
                        message = f"Invalid JSON: {str(e)}"
                        all_good = False
                    except Exception as e:
                        status = EMOJIS["ERROR"]
                        message = f"Error: {str(e)}"
                        all_good = False

                embed.add_field(
                    name=f"{status} {name}",
                    value=f"`{os.path.basename(filepath)}`\n{message}",
                    inline=False
                )

            # Add summary
            if all_good:
                embed.description = f"{EMOJIS['SUCCESS']} All JSON files are valid and accessible!"
                embed.color = COLORS["SUCCESS"]
            else:
                embed.description = f"{EMOJIS['WARNING']} Some JSON files have issues. See details below."
                embed.color = COLORS["WARNING"]

            embed.set_footer(text=f"Requested by {ctx.author}")
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} ran !checkjson command")

        @commands.command(name="block")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def block(self, ctx, member: discord.Member, days: int = 7):
            """Block a user from signing up for events."""
            if days < 1 or days > 365:
                await ctx.send(f"{EMOJIS['ERROR']} Days must be between 1 and 365.")
                return

            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Event system not available.")
                return

            event_cog.block_user(member.id, ctx.author.id, days)

            expiry = datetime.utcnow() + timedelta(days=days)
            embed = discord.Embed(
                title=f"{EMOJIS['BLOCKED']} User Blocked",
                description=f"{member.mention} has been blocked from event signups.",
                color=COLORS["DANGER"]
            )
            embed.add_field(name="Duration", value=f"{days} days", inline=True)
            embed.add_field(name="Expires", value=expiry.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
            embed.add_field(name="Blocked By", value=ctx.author.mention, inline=True)

            await ctx.send(embed=embed)

            # Notify bot admin
            try:
                admin = await self.bot.fetch_user(BOT_ADMIN_USER_ID)
                if admin:
                    await admin.send(embed=embed)
            except Exception as e:
                logger.warning(f"Failed to notify bot admin: {e}")

        @commands.command(name="unblock")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def unblock(self, ctx, member: discord.Member):
            """Unblock a user from event signups."""
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Event system not available.")
                return

            if not event_cog.is_user_blocked(member.id):
                await ctx.send(f"{EMOJIS['WARNING']} {member.mention} is not currently blocked.")
                return

            event_cog.unblock_user(member.id)

            embed = discord.Embed(
                title=f"{EMOJIS['SUCCESS']} User Unblocked",
                description=f"{member.mention} has been unblocked.",
                color=COLORS["SUCCESS"]
            )
            embed.add_field(name="Unblocked By", value=ctx.author.mention, inline=True)

            await ctx.send(embed=embed)

            # Notify in alert channel
            try:
                alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
                if alert_channel:
                    await alert_channel.send(f"{EMOJIS['SUCCESS']} {member.mention} has been unblocked and can now sign up for events.")
            except Exception as e:
                logger.warning(f"Failed to send unblock notification: {e}")

        @commands.command(name="blocklist")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def blocklist(self, ctx):
            """Show all currently blocked users."""
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Event system not available.")
                return

            blocked_users = event_cog.blocked_users
            if not blocked_users:
                embed = discord.Embed(
                    title=f"{EMOJIS['SUCCESS']} No Blocked Users",
                    description="There are no users currently blocked from events.",
                    color=COLORS["SUCCESS"]
                )
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"{EMOJIS['BLOCKED']} Blocked Users ({len(blocked_users)})",
                color=COLORS["WARNING"]
            )

            for user_id, info in blocked_users.items():
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    blocked_at = datetime.fromisoformat(info.get("blocked_at", ""))
                    duration = info.get("ban_duration_days", 0)
                    expiry = blocked_at + timedelta(days=duration)
                    remaining = expiry - datetime.utcnow()

                    if remaining.total_seconds() > 0:
                        days_left = remaining.days
                        hours_left = remaining.seconds // 3600
                        time_text = f"{days_left}d {hours_left}h remaining"
                    else:
                        time_text = "Expired (will be removed soon)"

                    blocked_by = info.get("blocked_by", "Unknown")

                    embed.add_field(
                        name=f"{user.name if user else f'User {user_id}'}",
                        value=f"**Time Left:** {time_text}\n**Blocked By:** <@{blocked_by}>",
                        inline=False
                    )
                except Exception as e:
                    logger.warning(f"Error displaying blocked user {user_id}: {e}")
                    embed.add_field(
                        name=f"User {user_id}",
                        value="Error loading user data",
                        inline=False
                    )

            await ctx.send(embed=embed)

        @commands.command(name="win")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def record_win(self, ctx, team: str):
            """Record a win for a team."""
            results_cog = self.bot.get_cog("Results")
            if not results_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Results system not available.")
                return

            # Validate team name
            from utils.validators import Validators
            team_key = Validators.validate_team_name(team)
            if not team_key:
                await ctx.send(f"{EMOJIS['ERROR']} Invalid team. Use: main_team, team_2, or team_3")
                return

            await results_cog.record_win(ctx, team_key)

        @commands.command(name="loss")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def record_loss(self, ctx, team: str):
            """Record a loss for a team."""
            results_cog = self.bot.get_cog("Results")
            if not results_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Results system not available.")
                return

            # Validate team name
            from utils.validators import Validators
            team_key = Validators.validate_team_name(team)
            if not team_key:
                await ctx.send(f"{EMOJIS['ERROR']} Invalid team. Use: main_team, team_2, or team_3")
                return

            await results_cog.record_loss(ctx, team_key)

        @commands.command(name="rowstats")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def row_stats(self, ctx):
            """Display comprehensive RoW statistics."""
            try:
                event_cog = self.bot.get_cog("EventManager")
                results_cog = self.bot.get_cog("Results")

                if not event_cog:
                    await ctx.send(f"{EMOJIS['ERROR']} Event system not available.")
                    return

                embed = discord.Embed(
                    title=f"{EMOJIS['STATS']} RoW Statistics Report",
                    color=COLORS["PRIMARY"],
                    timestamp=datetime.utcnow()
                )

                # Current signups
                total_signups = 0
                for team_key, members in event_cog.events.items():
                    team_name = TEAM_DISPLAY.get(team_key, team_key)
                    member_count = len(members)
                    total_signups += member_count

                    # Get member names
                    member_list = []
                    for i, user_id in enumerate(members[:5]):  # Show first 5
                        display_name = await event_cog.get_user_display_name(
                            await self.bot.fetch_user(int(user_id))
                        )
                        member_list.append(f"{i+1}. {display_name}")

                    if len(members) > 5:
                        member_list.append(f"... and {len(members) - 5} more")

                    value = "\n".join(member_list) if member_list else "*No signups yet*"
                    embed.add_field(
                        name=f"{team_name} ({member_count}/35)",
                        value=value,
                        inline=False
                    )

                # Win/Loss statistics
                if results_cog:
                    results_data = results_cog.results
                    overall_stats = []

                    for team_key in ["main_team", "team_2", "team_3"]:
                        if team_key in results_data:
                            wins = results_data[team_key].get("wins", 0)
                            losses = results_data[team_key].get("losses", 0)
                            total = wins + losses
                            rate = (wins / total * 100) if total > 0 else 0

                            team_name = TEAM_DISPLAY.get(team_key, team_key)
                            overall_stats.append(f"{team_name}: {wins}W-{losses}L ({rate:.1f}%)")

                    if overall_stats:
                        embed.add_field(
                            name=f"{EMOJIS['TROPHY']} Win/Loss Records",
                            value="\n".join(overall_stats),
                            inline=False
                        )

                # Blocked users summary
                blocked_count = len(event_cog.blocked_users)
                if blocked_count > 0:
                    embed.add_field(
                        name=f"{EMOJIS['BLOCKED']} Blocked Users",
                        value=f"{blocked_count} user(s) currently blocked\nUse `!blocklist` for details",
                        inline=True
                    )

                # Event time info
                time_info = []
                for team_key, time_str in event_cog.event_times.items():
                    team_name = TEAM_DISPLAY.get(team_key, team_key)
                    time_info.append(f"{team_name}: `{time_str}`")

                embed.add_field(
                    name=f"{EMOJIS['CLOCK']} Event Schedule",
                    value="\n".join(time_info),
                    inline=True
                )

                embed.set_footer(text=f"Total signups: {total_signups} • Requested by {ctx.author}")
                await ctx.send(embed=embed)

            except Exception as e:
                logger.exception("Error in rowstats command")
                await ctx.send(f"{EMOJIS['ERROR']} An error occurred while generating statistics.")

        @commands.command(name="clearevents")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def clear_events(self, ctx):
            """Clear all current event signups (use with caution)."""
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Event system not available.")
                return

            # Save to history first
            event_cog.save_history()

            # Clear events
            event_cog.events = {"main_team": [], "team_2": [], "team_3": []}
            event_cog.save_events()

            embed = discord.Embed(
                title=f"{EMOJIS['WARNING']} Events Cleared",
                description="All event signups have been cleared and saved to history.",
                color=COLORS["WARNING"]
            )
            embed.add_field(name="Cleared By", value=ctx.author.mention, inline=True)

            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} cleared all event signups")

        @commands.command(name="settime")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def set_event_time(self, ctx, team: str, *, time: str):
            """Set the event time for a specific team."""
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send(f"{EMOJIS['ERROR']} Event system not available.")
                return

            # Validate team
            from utils.validators import Validators
            team_key = Validators.validate_team_name(team)
            if not team_key:
                await ctx.send(f"{EMOJIS['ERROR']} Invalid team. Use: main_team, team_2, or team_3")
                return

            # Update time
            event_cog.event_times[team_key] = time
            event_cog.save_times()

            team_name = TEAM_DISPLAY.get(team_key, team_key)
            embed = discord.Embed(
                title=f"{EMOJIS['CLOCK']} Event Time Updated",
                description=f"{team_name} event time set to: `{time}`",
                color=COLORS["SUCCESS"]
            )

            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} set {team_key} time to {time}")


    async def setup(bot):
        await bot.add_cog(AdminActions(bot))
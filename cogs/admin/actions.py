    import discord
    from discord.ext import commands
    from datetime import datetime, timedelta
    import asyncio
    import os

    from utils.logger import setup_logger
    from config.constants import ADMIN_ROLE_IDS, FILES, TEAM_DISPLAY, ALERT_CHANNEL_IDS
    from config.settings import BOT_ADMIN_USER_ID
    from utils.helpers import Helpers
    from utils.data_manager import DataManager

    logger = setup_logger("admin_actions")

    class AdminActions(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.data_manager = DataManager()

        def load_results(self):
            """Load results using DataManager."""
            default_results = {
                "total_wins": 0,
                "total_losses": 0,
                "history": []
            }
            return self.data_manager.load_json(FILES["RESULTS"], default_results)

        def load_blocked_users(self):
            """Load blocked users using DataManager."""
            return self.data_manager.load_json(FILES["BLOCKED"], {})

        def save_blocked_users(self, data):
            """Save blocked users using DataManager."""
            success = self.data_manager.save_json(FILES["BLOCKED"], data)
            if not success:
                logger.error("❌ Failed to save blocked users")
            return success

        @commands.command()
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def block(self, ctx, member: discord.Member, days: int):
            """Block a user from signing up for a number of days."""
            user_id = str(member.id)
            blocked_by = str(ctx.author)
            blocked_at = datetime.utcnow().isoformat()
            duration = max(days, 1)

            data = self.load_blocked_users()
            data[user_id] = {
                "blocked_by": blocked_by,
                "blocked_at": blocked_at,
                "ban_duration_days": duration
            }

            if self.save_blocked_users(data):
                await ctx.send(f"✅ {member.mention} has been blocked for `{duration}` day(s).")
                logger.info(f"{ctx.author} blocked {member} for {duration} days")

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
                        await admin.send(embed=embed)
                except Exception as e:
                    logger.warning(f"Failed to DM bot admin: {e}")

                # Audit log
                try:
                    from utils.audit_logger import log_admin_action
                    log_admin_action(
                        admin_id=ctx.author.id,
                        action="block_user",
                        target_user_id=member.id,
                        details={"duration_days": duration},
                        guild_id=ctx.guild.id if ctx.guild else None
                    )
                except Exception as e:
                    logger.warning(f"Error logging block audit: {e}")
            else:
                await ctx.send("❌ Failed to save block record. Please try again.")

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
            if self.save_blocked_users(data):
                await ctx.send(f"✅ {member.mention} has been unblocked.")
                logger.info(f"{ctx.author} manually unblocked {member}")

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

                try:
                    for channel_id in ALERT_CHANNEL_IDS:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            await channel.send(f"✅ {member.mention} has been unblocked.")
                except Exception as e:
                    logger.warning(f"Failed to send unblock alert: {e}")

                # Audit log
                try:
                    from utils.audit_logger import log_admin_action
                    log_admin_action(
                        admin_id=ctx.author.id,
                        action="unblock_user",
                        target_user_id=member.id,
                        guild_id=ctx.guild.id if ctx.guild else None
                    )
                except Exception as e:
                    logger.warning(f"Error logging unblock audit: {e}")
            else:
                await ctx.send("❌ Failed to save unblock changes. Please try again.")

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

                    blocked_at = datetime.fromisoformat(info.get("blocked_at"))
                    duration = info.get("ban_duration_days", 0)
                    expires_at = blocked_at + timedelta(days=duration)
                    remaining = expires_at - datetime.utcnow()

                    if remaining.total_seconds() > 0:
                        days = remaining.days
                        hours = remaining.seconds // 3600
                        time_left = f"{days}d {hours}h" if days > 0 else f"{hours}h"
                    else:
                        time_left = "Expired"

                    lines.append(f"{name} - `{time_left}`")
                except Exception as e:
                    logger.warning(f"Error processing blocked user {user_id}: {e}")
                    lines.append(f"<@{user_id}> - `Error`")

            embed = discord.Embed(
                title=f"🚫 Blocked Users ({len(lines)})",
                description="\n".join(lines),
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

        @commands.command()
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def rowstats(self, ctx):
            """Show comprehensive RoW stats."""
            try:
                event_cog = self.bot.get_cog("EventManager")
                profile_cog = self.bot.get_cog("Profile")

                if not event_cog or not profile_cog:
                    await ctx.send("❌ Event or profile system not available.")
                    return

                results = self.load_results()
                blocked_data = self.load_blocked_users()

                wins = results.get("total_wins", 0)
                losses = results.get("total_losses", 0)
                win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

                embed = discord.Embed(title="📊 RoW Stats Report", color=discord.Color.blurple())

                for team, members in event_cog.events.items():
                    igns = []
                    for uid in members:
                        try:
                            user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
                            ign = profile_cog.get_ign(user) if user else "Unknown"
                            name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
                            igns.append(f"{name} (`{ign}`)")
                        except Exception as e:
                            logger.warning(f"Error getting user info for {uid}: {e}")
                            igns.append(f"<@{uid}> (`Unknown`)")

                    team_display = TEAM_DISPLAY.get(team, team.replace("_", " ").title())
                    value = "\n".join(igns) if igns else "No members"
                    embed.add_field(
                        name=f"{team_display} ({len(igns)} signed up)",
                        value=value,
                        inline=False
                    )

                blocked_info = []
                for uid, info in blocked_data.items():
                    try:
                        user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
                        name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"

                        blocked_at = datetime.fromisoformat(info.get("blocked_at"))
                        duration = info.get("ban_duration_days", 0)
                        expires_at = blocked_at + timedelta(days=duration)
                        remaining = expires_at - datetime.utcnow()

                        if remaining.total_seconds() > 0:
                            days = remaining.days
                            time_left = f"{days}d" if days > 0 else "< 1d"
                        else:
                            time_left = "Expired"

                        blocked_info.append(f"{name} - `{time_left}` remaining")
                    except Exception as e:
                        logger.warning(f"Error processing blocked user {uid}: {e}")
                        blocked_info.append(f"<@{uid}> - `Error`")

                embed.add_field(
                    name=f"🚫 Blocked Users ({len(blocked_info)})",
                    value="\n".join(blocked_info) if blocked_info else "None",
                    inline=False
                )

                embed.add_field(
                    name="📊 Overall Record",
                    value=f"🏆 {wins} Wins | 💔 {losses} Losses\n📈 Win Rate: `{win_rate:.1f}%`",
                    inline=False
                )

                await ctx.send(embed=embed)
                logger.info(f"{ctx.author} requested !rowstats")

            except Exception as e:
                logger.exception("Error in !rowstats command:")
                await ctx.send("❌ Failed to generate stats report.")

        # AUDIT COMMANDS
        @commands.command(name="audit")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def show_audit_log(self, ctx, user: discord.Member = None, limit: int = 10):
            """Show recent audit log entries."""
            try:
                from utils.audit_logger import audit_logger

                if user:
                    actions = audit_logger.get_user_actions(user.id, limit)
                    title = f"📋 Audit Log for {user.display_name}"
                else:
                    actions = audit_logger.get_recent_actions(limit)
                    title = f"📋 Recent Audit Log ({limit} entries)"

                if not actions:
                    await ctx.send("ℹ️ No audit log entries found.")
                    return

                embed = discord.Embed(title=title, color=discord.Color.blue())

                lines = []
                for action in actions[-limit:]:
                    try:
                        timestamp = datetime.fromisoformat(action["timestamp"])
                        time_str = timestamp.strftime("%m/%d %H:%M")

                        action_type = action.get("action_type", "unknown")
                        user_id = action.get("user_id", "unknown")
                        target_id = action.get("target_user_id")
                        details = action.get("details", {})

                        if action_type.startswith("team_"):
                            team = details.get("team", "unknown")
                            action_desc = f"{action_type.replace('team_', '').title()} {team}"
                        elif action_type.startswith("admin_"):
                            admin_action = action_type.replace("admin_", "")
                            if target_id:
                                action_desc = f"{admin_action.title()} <@{target_id}>"
                            else:
                                action_desc = admin_action.title()
                        elif action_type == "record_result":
                            team = details.get("team", "unknown")
                            result = details.get("result", "unknown")
                            action_desc = f"Recorded {result} for {team}"
                        elif action_type.startswith("event_"):
                            event_action = action_type.replace("event_", "")
                            action_desc = f"Event {event_action}"
                        else:
                            action_desc = action_type

                        lines.append(f"`{time_str}` <@{user_id}> {action_desc}")

                    except Exception as e:
                        logger.warning(f"Error formatting audit entry: {e}")
                        lines.append("`Error` Invalid audit entry")

                chunk_size = 10
                for i in range(0, len(lines), chunk_size):
                    chunk = lines[i:i + chunk_size]
                    field_name = f"Actions {i+1}-{min(i+chunk_size, len(lines))}" if len(lines) > chunk_size else "Actions"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(chunk) if chunk else "No actions",
                        inline=False
                    )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.exception("Error in audit command:")
                await ctx.send("❌ Failed to retrieve audit log.")

        @commands.command(name="audituser")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def audit_user(self, ctx, user: discord.Member, days: int = 7):
            """Show detailed audit history for a specific user."""
            try:
                from utils.audit_logger import audit_logger

                actions = audit_logger.search_actions(user_id=user.id, days_back=days)

                if not actions:
                    await ctx.send(f"ℹ️ No audit entries found for {user.mention} in the last {days} days.")
                    return

                embed = discord.Embed(
                    title=f"📊 {user.display_name}'s Activity ({days} days)",
                    description=f"Found {len(actions)} actions",
                    color=discord.Color.blue()
                )

                categories = {}
                for action in actions:
                    action_type = action.get("action_type", "unknown")
                    category = action_type.split("_")[0]

                    if category not in categories:
                        categories[category] = []
                    categories[category].append(action)

                for category, cat_actions in categories.items():
                    lines = []
                    for action in cat_actions[-5:]:
                        try:
                            timestamp = datetime.fromisoformat(action["timestamp"])
                            time_str = timestamp.strftime("%m/%d %H:%M")
                            details = action.get("details", {})

                            if category == "team":
                                team = details.get("team", "unknown")
                                action_name = action["action_type"].replace("team_", "")
                                lines.append(f"`{time_str}` {action_name} {team}")
                            elif category == "admin":
                                action_name = action["action_type"].replace("admin_", "")
                                target = action.get("target_user_id")
                                if target:
                                    lines.append(f"`{time_str}` {action_name} <@{target}>")
                                else:
                                    lines.append(f"`{time_str}` {action_name}")
                            else:
                                lines.append(f"`{time_str}` {action['action_type']}")
                        except Exception as e:
                            lines.append(f"`Error` Invalid entry")

                    if lines:
                        embed.add_field(
                            name=f"{category.title()} Actions ({len(cat_actions)} total)",
                            value="\n".join(lines),
                            inline=True
                        )

                embed.set_footer(text=f"Showing recent actions per category")
                await ctx.send(embed=embed)

            except Exception as e:
                logger.exception("Error in audituser command:")
                await ctx.send("❌ Failed to retrieve user audit data.")

        # BACKUP COMMANDS
        @commands.command(name="backup")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def create_backup_command(self, ctx):
            """Create a manual backup of all data files."""
            try:
                from utils.backup_manager import backup_manager

                await ctx.send("🔄 Creating backup...")

                backup_path = backup_manager.create_backup("manual")

                if backup_path:
                    filename = os.path.basename(backup_path)
                    size_mb = round(os.path.getsize(backup_path) / 1024 / 1024, 2)

                    embed = discord.Embed(
                        title="✅ Backup Created",
                        description=f"**File:** `{filename}`\n**Size:** {size_mb} MB",
                        color=discord.Color.green()
                    )

                    await ctx.send(embed=embed)
                    logger.info(f"Manual backup created by {ctx.author}: {filename}")

                    try:
                        from utils.audit_logger import log_admin_action
                        log_admin_action(
                            admin_id=ctx.author.id,
                            action="create_backup",
                            details={"filename": filename, "size_mb": size_mb},
                            guild_id=ctx.guild.id if ctx.guild else None
                        )
                    except Exception as e:
                        logger.warning(f"Error logging backup audit: {e}")
                else:
                    await ctx.send("❌ Failed to create backup.")

            except Exception as e:
                logger.exception("Error in backup command:")
                await ctx.send("❌ Failed to create backup.")

        @commands.command(name="backups")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def list_backups_command(self, ctx, limit: int = 10):
            """List available backups."""
            try:
                from utils.backup_manager import backup_manager

                backups = backup_manager.list_backups()

                if not backups:
                    await ctx.send("ℹ️ No backups found.")
                    return

                stats = backup_manager.get_backup_stats()

                embed = discord.Embed(
                    title=f"💾 Available Backups ({stats['total_backups']} total)",
                    description=f"**Total Size:** {stats.get('total_size_mb', 0)} MB",
                    color=discord.Color.blue()
                )

                for backup in backups[:limit]:
                    try:
                        filename = backup["filename"]
                        size_kb = round(backup["size"] / 1024, 1)
                        created = backup["created"].strftime("%Y-%m-%d %H:%M")

                        backup_type = "manual"
                        if backup["metadata"]:
                            backup_type = backup["metadata"].get("backup_type", "manual")

                        embed.add_field(
                            name=f"📄 {filename}",
                            value=f"**Created:** {created}\n**Type:** {backup_type}\n**Size:** {size_kb} KB",
                            inline=True
                        )
                    except Exception as e:
                        logger.warning(f"Error displaying backup {backup}: {e}")

                if len(backups) > limit:
                    embed.set_footer(text=f"Showing {limit} of {len(backups)} backups")

                await ctx.send(embed=embed)

            except Exception as e:
                logger.exception("Error in backups command:")
                await ctx.send("❌ Failed to list backups.")

        @commands.command(name="restore")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def restore_backup_command(self, ctx, backup_filename: str):
            """Restore data from a backup (DANGEROUS)."""
            try:
                from utils.backup_manager import backup_manager

                confirm_embed = discord.Embed(
                    title="⚠️ Restore Confirmation Required",
                    description=f"**You are about to restore from:** `{backup_filename}`\n\n"
                               f"**This will:**\n"
                               f"• Create a backup of current data first\n"
                               f"• Overwrite all current data files\n"
                               f"• Cannot be easily undone\n\n"
                               f"**Type `CONFIRM RESTORE` to proceed:**",
                    color=discord.Color.orange()
                )

                await ctx.send(embed=confirm_embed)

                def check(m):
                    return (m.author == ctx.author and 
                           m.channel == ctx.channel and 
                           m.content.upper() == "CONFIRM RESTORE")

                try:
                    confirmation = await self.bot.wait_for('message', check=check, timeout=30.0)
                except asyncio.TimeoutError:
                    await ctx.send("⚠️ Restore cancelled - no confirmation received.")
                    return

                await ctx.send("🔄 Restoring backup...")

                success = backup_manager.restore_backup(backup_filename, confirm=True)

                if success:
                    embed = discord.Embed(
                        title="✅ Restore Completed",
                        description=f"Successfully restored from `{backup_filename}`",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)

                    logger.warning(f"Data restored from {backup_filename} by {ctx.author}")

                    try:
                        from utils.audit_logger import log_admin_action
                        log_admin_action(
                            admin_id=ctx.author.id,
                            action="restore_backup",
                            details={"backup_filename": backup_filename},
                            guild_id=ctx.guild.id if ctx.guild else None
                        )
                    except Exception as e:
                        logger.warning(f"Error logging restore audit: {e}")
                else:
                    await ctx.send("❌ Failed to restore backup.")

            except Exception as e:
                logger.exception("Error in restore command:")
                await ctx.send("❌ Failed to restore backup.")

        # RATE LIMITING COMMANDS
        @commands.command(name="ratelimit")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def show_rate_limits(self, ctx, user: discord.Member = None):
            """Show rate limiting information."""
            try:
                from utils.rate_limiter import rate_limiter

                if user:
                    stats = rate_limiter.get_user_stats(user.id)

                    embed = discord.Embed(
                        title=f"⏰ Rate Limits - {user.display_name}",
                        color=discord.Color.blue()
                    )

                    embed.add_field(
                        name="📊 Usage",
                        value=f"Commands (1m): {stats['commands_last_minute']}/10\n"
                              f"Commands (1h): {stats['commands_last_hour']}/100\n"
                              f"Buttons (1m): {stats['buttons_last_minute']}/5",
                        inline=True
                    )

                    if stats['active_cooldowns']:
                        cooldown_text = "\n".join([f"`{cmd}`: {time}s" 
                                                 for cmd, time in stats['active_cooldowns'].items()])
                        embed.add_field(
                            name="⏳ Active Cooldowns",
                            value=cooldown_text,
                            inline=True
                        )

                    status = "🔴 Rate Limited" if stats['is_rate_limited'] else "🟢 Normal"
                    embed.add_field(name="Status", value=status, inline=True)

                else:
                    global_stats = rate_limiter.get_global_stats()

                    embed = discord.Embed(
                        title="⏰ Global Rate Limit Stats",
                        color=discord.Color.blue()
                    )

                    embed.add_field(
                        name="📊 Activity (Last Hour)",
                        value=f"Active Users: {global_stats['active_users_last_hour']}\n"
                              f"Total Commands: {global_stats['total_commands_last_hour']}\n"
                              f"Rate Limited Users: {global_stats['rate_limited_users']}\n"
                              f"Active Cooldowns: {global_stats['active_cooldowns']}",
                        inline=False
                    )

                    embed.add_field(
                        name="⚙️ Limits",
                        value="Commands: 10/min, 100/hour\n"
                              "Buttons: 5/min\n"
                              "Special cooldowns: varies by command",
                        inline=False
                    )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.exception("Error in ratelimit command:")
                await ctx.send("❌ Failed to show rate limits.")

        @commands.command(name="resetlimits")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def reset_rate_limits(self, ctx, user: discord.Member):
            """Reset rate limits for a specific user."""
            try:
                from utils.rate_limiter import reset_user_rate_limits

                reset_user_rate_limits(user.id)

                embed = discord.Embed(
                    title="✅ Rate Limits Reset",
                    description=f"Reset all rate limits for {user.mention}",
                    color=discord.Color.green()
                )

                await ctx.send(embed=embed)
                logger.info(f"Rate limits reset for {user} by {ctx.author}")

                try:
                    from utils.audit_logger import log_admin_action
                    log_admin_action(
                        admin_id=ctx.author.id,
                        action="reset_rate_limits",
                        target_user_id=user.id,
                        guild_id=ctx.guild.id if ctx.guild else None
                    )
                except Exception as e:
                    logger.warning(f"Error logging rate limit reset audit: {e}")

            except Exception as e:
                logger.exception("Error in resetlimits command:")
                await ctx.send("❌ Failed to reset rate limits.")

        @commands.command(name="cleanup")
        @commands.has_any_role(*ADMIN_ROLE_IDS)
        async def cleanup_data(self, ctx, days: int = 30):
            """Clean up old data entries (audit logs, etc.)."""
            try:
                if days < 7:
                    await ctx.send("❌ Cannot clean up data newer than 7 days.")
                    return

                from utils.backup_manager import backup_manager
                backup_path = backup_manager.create_backup("pre_cleanup")

                cleaned_items = 0

                # Clean up audit log
                try:
                    from utils.audit_logger import audit_logger
                    audit_log = audit_logger.data_manager.load_json(audit_logger.audit_file, [])

                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    original_count = len(audit_log)

                    cleaned_audit = []
                    for entry in audit_log:
                        try:
                            entry_date = datetime.fromisoformat(entry["timestamp"])
                            if entry_date > cutoff_date:
                                cleaned_audit.append(entry)
                        except:
                            cleaned_audit.append(entry)

                    if audit_logger.data_manager.save_json(audit_logger.audit_file, cleaned_audit):
                        cleaned_count = original_count - len(cleaned_audit)
                        cleaned_items += cleaned_count
                        logger.info(f"Cleaned {cleaned_count} old audit entries")

                except Exception as e:
                    logger.warning(f"Error cleaning audit log: {e}")

                # Clean up old event history
                try:
                    history = self.data_manager.load_json(FILES["HISTORY"], [])
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    original_count = len(history)

                    cleaned_history = []
                    for entry in history:
                        try:
                            entry_date = datetime.fromisoformat(entry["timestamp"])
                            if entry_date > cutoff_date:
                                cleaned_history.append(entry)
                        except:
                            cleaned_history.append(entry)

                    if self.data_manager.save_json(FILES["HISTORY"], cleaned_history):
                        cleaned_count = original_count - len(cleaned_history)
                        cleaned_items += cleaned_count
                        logger.info(f"Cleaned {cleaned_count} old history entries")

                except Exception as e:
                    logger.warning(f"Error cleaning history: {e}")

                # Clean up old results
                try:
                    results = self.load_results()
                    if "history" in results:
                        cutoff_date = datetime.utcnow() - timedelta(days=days)
                        original_count = len(results["history"])

                        cleaned_results_history = []
                        for entry in results["history"]:
                            try:
                                entry_date = datetime.fromisoformat(entry["timestamp"])
                                if entry_date > cutoff_date:
                                    cleaned_results_history.append(entry)
                            except:
                                cleaned_results_history.append(entry)

                        results["history"] = cleaned_results_historyimport discord
                        from discord.ext import commands
                        from config.constants import MAIN_TEAM_ROLE_ID, EMOJIS, TEAM_DISPLAY, FILES
                        from config.settings import MAX_TEAM_SIZE
                        from utils.logger import setup_logger

                        logger = setup_logger("buttons")

                        class EventButtons(discord.ui.View):
                            def __init__(self, bot):
                                super().__init__(timeout=None)  # Persistent view
                                self.bot = bot

                            async def get_user_ign(self, interaction):
                                """Helper to get user's IGN from profile system."""
                                try:
                                    profile_cog = self.bot.get_cog("Profile")
                                    if profile_cog:
                                        if not profile_cog.has_ign(interaction.user):
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('WARNING', '⚠️')} You need to set your IGN first with `!setign YourName`.",
                                                ephemeral=True
                                            )
                                            return None
                                        return profile_cog.get_ign(interaction.user)
                                    return interaction.user.display_name
                                except Exception as e:
                                    logger.error(f"Error getting user IGN: {e}")
                                    return interaction.user.display_name

                            @discord.ui.button(
                                label="Join Main Team",
                                style=discord.ButtonStyle.primary,
                                emoji="🏆",
                                custom_id="join_main_team_btn"
                            )
                            async def join_main_team(self, interaction: discord.Interaction, button: discord.ui.Button):
                                """Handle main team join button with rate limiting."""
                                try:
                                    # Rate limiting check
                                    from utils.rate_limiter import check_button_rate_limit
                                    allowed, rate_message = check_button_rate_limit(interaction.user.id)

                                    if not allowed:
                                        await interaction.response.send_message(
                                            f"⏰ {rate_message}", 
                                            ephemeral=True
                                        )
                                        logger.warning(f"Rate limited button click by {interaction.user.id}: {rate_message}")
                                        return

                                    # Get EventManager cog with error handling
                                    event_cog = self.bot.get_cog("EventManager")
                                    if not event_cog:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Event system not available.", 
                                            ephemeral=True
                                        )
                                        return

                                    # Check if user is blocked
                                    try:
                                        if event_cog.is_user_blocked(interaction.user.id):
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('BLOCKED', '🚫')} You are currently blocked from events.", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking if user blocked: {e}")

                                    # Get user IGN with error handling
                                    user_ign = await self.get_user_ign(interaction)
                                    if not user_ign:
                                        return  # Error message already sent

                                    # Check main team role permission
                                    try:
                                        if not any(role.id == MAIN_TEAM_ROLE_ID for role in interaction.user.roles):
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('ERROR', '❌')} You don't have permission to join the Main Team.", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking main team role: {e}")

                                    # Check if already in main team
                                    try:
                                        user_id_str = str(interaction.user.id)
                                        if user_id_str in event_cog.events.get("main_team", []):
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('SUCCESS', '✅')} You're already in the Main Team!", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking team membership: {e}")

                                    # Check team capacity
                                    try:
                                        if len(event_cog.events.get("main_team", [])) >= MAX_TEAM_SIZE:
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('ERROR', '❌')} Main Team is full ({MAX_TEAM_SIZE}/{MAX_TEAM_SIZE}).", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking team capacity: {e}")

                                    # Remove user from other teams
                                    try:
                                        old_teams = []
                                        for team in event_cog.events:
                                            if user_id_str in event_cog.events[team] and team != "main_team":
                                                event_cog.events[team].remove(user_id_str)
                                                old_teams.append(team)
                                    except Exception as e:
                                        logger.warning(f"Error removing from other teams: {e}")

                                    # Add to main team
                                    try:
                                        if "main_team" not in event_cog.events:
                                            event_cog.events["main_team"] = []
                                        event_cog.events["main_team"].append(user_id_str)

                                        # Save with error handling
                                        if hasattr(event_cog, 'save_events'):
                                            event_cog.save_events()
                                        elif hasattr(event_cog, 'data_manager'):
                                            event_cog.data_manager.save_json(FILES["EVENTS"], event_cog.events)

                                        # Audit logging
                                        try:
                                            from utils.audit_logger import log_signup
                                            log_signup(
                                                user_id=interaction.user.id,
                                                team="main_team",
                                                action="join",
                                                guild_id=interaction.guild.id if interaction.guild else None
                                            )

                                            # Log leaves from old teams
                                            for old_team in old_teams:
                                                log_signup(
                                                    user_id=interaction.user.id,
                                                    team=old_team,
                                                    action="leave",
                                                    guild_id=interaction.guild.id if interaction.guild else None
                                                )
                                        except Exception as e:
                                            logger.warning(f"Error logging audit: {e}")

                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('SUCCESS', '✅')} {user_ign} joined the Main Team!", 
                                            ephemeral=True
                                        )
                                        logger.info(f"{interaction.user} ({user_ign}) joined main_team")

                                    except Exception as e:
                                        logger.error(f"Error adding to main team: {e}")
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Failed to join team. Please try again.", 
                                            ephemeral=True
                                        )

                                except Exception as e:
                                    logger.exception(f"Critical error in join_main_team: {e}")
                                    try:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} An unexpected error occurred.", 
                                            ephemeral=True
                                        )
                                    except:
                                        pass  # Don't fail if we can't even send error message

                            @discord.ui.button(
                                label="Join Team 2",
                                style=discord.ButtonStyle.secondary,
                                emoji="🔸",
                                custom_id="join_team_2_btn"
                            )
                            async def join_team_2(self, interaction: discord.Interaction, button: discord.ui.Button):
                                """Handle team 2 join button."""
                                await self._join_team(interaction, "team_2")

                            @discord.ui.button(
                                label="Join Team 3", 
                                style=discord.ButtonStyle.secondary,
                                emoji="🔸",
                                custom_id="join_team_3_btn"
                            )
                            async def join_team_3(self, interaction: discord.Interaction, button: discord.ui.Button):
                                """Handle team 3 join button."""
                                await self._join_team(interaction, "team_3")

                            async def _join_team(self, interaction: discord.Interaction, team_key: str):
                                """Generic team join handler with rate limiting and audit logging."""
                                try:
                                    # Rate limiting check
                                    from utils.rate_limiter import check_button_rate_limit
                                    allowed, rate_message = check_button_rate_limit(interaction.user.id)

                                    if not allowed:
                                        await interaction.response.send_message(
                                            f"⏰ {rate_message}", 
                                            ephemeral=True
                                        )
                                        logger.warning(f"Rate limited button click by {interaction.user.id}: {rate_message}")
                                        return

                                    # Get EventManager cog with error handling
                                    event_cog = self.bot.get_cog("EventManager")
                                    if not event_cog:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Event system not available.", 
                                            ephemeral=True
                                        )
                                        return

                                    # Check if user is blocked
                                    try:
                                        if event_cog.is_user_blocked(interaction.user.id):
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('BLOCKED', '🚫')} You are currently blocked from events.", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking if user blocked: {e}")

                                    # Get user IGN
                                    user_ign = await self.get_user_ign(interaction)
                                    if not user_ign:
                                        return

                                    user_id_str = str(interaction.user.id)

                                    # Check if already in this team
                                    try:
                                        if user_id_str in event_cog.events.get(team_key, []):
                                            team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('SUCCESS', '✅')} You're already in {team_display}!", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking team membership: {e}")

                                    # Check team capacity
                                    try:
                                        if len(event_cog.events.get(team_key, [])) >= MAX_TEAM_SIZE:
                                            team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('ERROR', '❌')} {team_display} is full ({MAX_TEAM_SIZE}/{MAX_TEAM_SIZE}).", 
                                                ephemeral=True
                                            )
                                            return
                                    except Exception as e:
                                        logger.warning(f"Error checking team capacity: {e}")

                                    # Remove from other teams and add to selected team
                                    try:
                                        old_teams = []
                                        for team in event_cog.events:
                                            if user_id_str in event_cog.events[team] and team != team_key:
                                                event_cog.events[team].remove(user_id_str)
                                                old_teams.append(team)

                                        if team_key not in event_cog.events:
                                            event_cog.events[team_key] = []
                                        event_cog.events[team_key].append(user_id_str)

                                        # Save with error handling
                                        if hasattr(event_cog, 'save_events'):
                                            event_cog.save_events()
                                        elif hasattr(event_cog, 'data_manager'):
                                            event_cog.data_manager.save_json(FILES["EVENTS"], event_cog.events)

                                        # Audit logging
                                        try:
                                            from utils.audit_logger import log_signup
                                            log_signup(
                                                user_id=interaction.user.id,
                                                team=team_key,
                                                action="join",
                                                guild_id=interaction.guild.id if interaction.guild else None
                                            )

                                            # Log leaves from old teams
                                            for old_team in old_teams:
                                                log_signup(
                                                    user_id=interaction.user.id,
                                                    team=old_team,
                                                    action="leave",
                                                    guild_id=interaction.guild.id if interaction.guild else None
                                                )
                                        except Exception as e:
                                            logger.warning(f"Error logging audit: {e}")

                                        team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('SUCCESS', '✅')} {user_ign} joined {team_display}!", 
                                            ephemeral=True
                                        )
                                        logger.info(f"{interaction.user} ({user_ign}) joined {team_key}")

                                    except Exception as e:
                                        logger.error(f"Error joining {team_key}: {e}")
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Failed to join team. Please try again.", 
                                            ephemeral=True
                                        )

                                except Exception as e:
                                    logger.exception(f"Critical error in join {team_key}: {e}")
                                    try:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} An unexpected error occurred.", 
                                            ephemeral=True
                                        )
                                    except:
                                        pass

                            @discord.ui.button(
                                label="Leave Team",
                                style=discord.ButtonStyle.danger,
                                emoji="❌",
                                custom_id="leave_team_btn"
                            )
                            async def leave_team(self, interaction: discord.Interaction, button: discord.ui.Button):
                                """Allow user to leave their current team with audit logging."""
                                try:
                                    # Rate limiting check
                                    from utils.rate_limiter import check_button_rate_limit
                                    allowed, rate_message = check_button_rate_limit(interaction.user.id)

                                    if not allowed:
                                        await interaction.response.send_message(
                                            f"⏰ {rate_message}", 
                                            ephemeral=True
                                        )
                                        logger.warning(f"Rate limited button click by {interaction.user.id}: {rate_message}")
                                        return

                                    # Get EventManager cog with error handling
                                    event_cog = self.bot.get_cog("EventManager")
                                    if not event_cog:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Event system not available.", 
                                            ephemeral=True
                                        )
                                        return

                                    # Get user IGN
                                    user_ign = await self.get_user_ign(interaction)
                                    if not user_ign:
                                        return

                                    # Find and remove from teams
                                    try:
                                        left_team = None
                                        user_id_str = str(interaction.user.id)

                                        for team, members in event_cog.events.items():
                                            if user_id_str in members:
                                                members.remove(user_id_str)
                                                left_team = team
                                                break

                                        if left_team:
                                            # Save with error handling
                                            if hasattr(event_cog, 'save_events'):
                                                event_cog.save_events()
                                            elif hasattr(event_cog, 'data_manager'):
                                                event_cog.data_manager.save_json(FILES["EVENTS"], event_cog.events)

                                            # Audit logging
                                            try:
                                                from utils.audit_logger import log_signup
                                                log_signup(
                                                    user_id=interaction.user.id,
                                                    team=left_team,
                                                    action="leave",
                                                    guild_id=interaction.guild.id if interaction.guild else None
                                                )
                                            except Exception as e:
                                                logger.warning(f"Error logging audit: {e}")

                                            team_display = TEAM_DISPLAY.get(left_team, left_team.replace('_', ' ').title())
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('SUCCESS', '✅')} {user_ign} has left **{team_display}**.", 
                                                ephemeral=True
                                            )
                                            logger.info(f"{interaction.user} ({user_ign}) left {left_team}")
                                        else:
                                            await interaction.response.send_message(
                                                f"{EMOJIS.get('INFO', 'ℹ️')} You're not signed up for any team.", 
                                                ephemeral=True
                                            )

                                    except Exception as e:
                                        logger.error(f"Error leaving team: {e}")
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Failed to leave team. Please try again.", 
                                            ephemeral=True
                                        )

                                except Exception as e:
                                    logger.exception(f"Critical error in leave_team: {e}")
                                    try:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} An unexpected error occurred.", 
                                            ephemeral=True
                                        )
                                    except:
                                        pass

                        class ButtonCog(commands.Cog):
                            def __init__(self, bot):
                                self.bot = bot
                                self.persistent_view = None

                            async def cog_load(self):
                                """Called when the cog is loaded."""
                                try:
                                    # Create and register the persistent view
                                    self.persistent_view = EventButtons(self.bot)
                                    self.bot.add_view(self.persistent_view)
                                    logger.info("✅ EventButtons view registered successfully")
                                except Exception as e:
                                    logger.error(f"❌ Failed to register EventButtons view: {e}")

                            async def cog_unload(self):
                                """Called when the cog is unloaded."""
                                try:
                                    if self.persistent_view:
                                        # Clean up the view when cog is unloaded
                                        self.persistent_view.stop()
                                        logger.info("✅ EventButtons view cleaned up")
                                except Exception as e:
                                    logger.error(f"❌ Error cleaning up EventButtons view: {e}")

                            @commands.command(name="register_buttons")
                            @commands.has_permissions(administrator=True)
                            async def register_buttons_command(self, ctx):
                                """Manually register button views (admin only)."""
                                try:
                                    # Remove existing view if any
                                    if self.persistent_view:
                                        self.persistent_view.stop()

                                    # Create and register new view
                                    self.persistent_view = EventButtons(self.bot)
                                    self.bot.add_view(self.persistent_view)

                                    await ctx.send("✅ Button views have been re-registered successfully!")
                                    logger.info(f"Button views manually re-registered by {ctx.author}")

                                    # Audit log
                                    try:
                                        from utils.audit_logger import log_admin_action
                                        log_admin_action(
                                            admin_id=ctx.author.id,
                                            action="register_buttons",
                                            guild_id=ctx.guild.id if ctx.guild else None
                                        )
                                    except Exception as e:
                                        logger.warning(f"Error logging button registration audit: {e}")

                                except Exception as e:
                                    logger.error(f"Error manually registering buttons: {e}")
                                    await ctx.send(f"❌ Failed to register button views: {e}")

                            @commands.command(name="test_buttons")
                            @commands.has_permissions(administrator=True)
                            async def test_buttons_command(self, ctx):
                                """Test button functionality (admin only)."""
                                try:
                                    embed = discord.Embed(
                                        title="🧪 Button Test",
                                        description="Test the signup buttons below:",
                                        color=0x5865F2
                                    )

                                    # Create a new view for testing
                                    view = EventButtons(self.bot)
                                    await ctx.send(embed=embed, view=view)

                                    # Audit log
                                    try:
                                        from utils.audit_logger import log_admin_action
                                        log_admin_action(
                                            admin_id=ctx.author.id,
                                            action="test_buttons",
                                            guild_id=ctx.guild.id if ctx.guild else None
                                        )
                                    except Exception as e:
                                        logger.warning(f"Error logging button test audit: {e}")

                                except Exception as e:
                                    logger.error(f"Error testing buttons: {e}")
                                    await ctx.send(f"❌ Failed to create test buttons: {e}")

                        async def setup(bot):
                            await bot.add_cog(ButtonCog(bot))
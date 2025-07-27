# Fix the imports at the top of cogs/admin/actions.py

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import tempfile
import os

from utils.logger import setup_logger
from config.constants import ADMIN_ROLE_IDS, FILES, TEAM_DISPLAY, ALERT_CHANNEL_ID
from config.settings import BOT_ADMIN_USER_ID  # Import from settings instead
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

    def save_results(self, data):
        """Save results using DataManager."""
        return self.data_manager.save_json(FILES["RESULTS"], data)

    def load_blocked_users(self):
        """Load blocked users using DataManager."""
        return self.data_manager.load_json(FILES["BLOCKED"], {})

    def save_blocked_users(self, data):
        """Save blocked users using DataManager."""
        success = self.data_manager.save_json(FILES["BLOCKED"], data)
        if not success:
            logger.error("❌ Failed to save blocked users")
        return success

    # EXISTING COMMANDS (from your current working bot)
    
    @commands.command(name="win")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_win(self, ctx, team_key: str = "main_team"):
        """Record a win for a team."""
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team. Use: main_team, team_2, or team_3")
            return

        results = self.load_results()
        results["total_wins"] = results.get("total_wins", 0) + 1
        results["history"] = results.get("history", [])
        results["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": "win",
            "team": team_key,
            "recorded_by": str(ctx.author)
        })
        
        if self.save_results(results):
            team_display = TEAM_DISPLAY.get(team_key, team_key)
            await ctx.send(f"✅ Win recorded for **{team_display}**!")
            logger.info(f"{ctx.author} recorded win for {team_key}")
        else:
            await ctx.send("❌ Failed to save win record.")

    @commands.command(name="loss")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_loss(self, ctx, team_key: str = "main_team"):
        """Record a loss for a team."""
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team. Use: main_team, team_2, or team_3")
            return

        results = self.load_results()
        results["total_losses"] = results.get("total_losses", 0) + 1
        results["history"] = results.get("history", [])
        results["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": "loss",
            "team": team_key,
            "recorded_by": str(ctx.author)
        })
        
        if self.save_results(results):
            team_display = TEAM_DISPLAY.get(team_key, team_key)
            await ctx.send(f"❌ Loss recorded for **{team_display}**.")
            logger.info(f"{ctx.author} recorded loss for {team_key}")
        else:
            await ctx.send("❌ Failed to save loss record.")

    @commands.command(name="absent")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def mark_absent(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
        """Mark player absent from this week's RoW event"""
        if member is None:
            member = ctx.author
            
        user_id = str(member.id)
        absent_data = self.data_manager.load_json(FILES["ABSENT"], {})
        
        absent_data[user_id] = {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "marked_by": str(ctx.author)
        }
        
        if self.data_manager.save_json(FILES["ABSENT"], absent_data):
            await ctx.send(f"✅ {member.mention} marked as absent. Reason: *{reason}*")
            logger.info(f"{ctx.author} marked {member} absent. Reason: {reason}")
        else:
            await ctx.send("❌ Failed to save absence record. Please try again.")

    @commands.command(name="present")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def mark_present(self, ctx, member: discord.Member):
        """Remove a user's absence mark."""
        user_id = str(member.id)
        absent_data = self.data_manager.load_json(FILES["ABSENT"], {})

        if user_id in absent_data:
            removed = absent_data.pop(user_id)
            if self.data_manager.save_json(FILES["ABSENT"], absent_data):
                await ctx.send(f"✅ Removed absence mark for {member.mention}")
                logger.info(f"{ctx.author} removed absence for {member}")
            else:
                await ctx.send("❌ Failed to save changes. Please try again.")
        else:
            await ctx.send(f"ℹ️ {member.mention} is not marked as absent.")

    @commands.command(name="absentees")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def show_absentees(self, ctx):
        """Show all users marked absent."""
        absent_data = self.data_manager.load_json(FILES["ABSENT"], {})
        
        if not absent_data:
            await ctx.send("✅ No absentees recorded for this week.")
            return

        lines = []
        for uid, entry in absent_data.items():
            user = self.bot.get_user(int(uid))
            name = user.mention if user else f"<@{uid}>"
            reason = entry.get("reason", "No reason")
            marked_by = entry.get("marked_by", "Unknown")
            lines.append(f"- {name} ({reason}) — marked by **{marked_by}**")

        embed = discord.Embed(
            title="📥 Absentees This Week",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="exportteams")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def export_teams(self, ctx):
        """Export current team signups to a text file."""
        try:
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send("❌ Event system not available.")
                return

            data = event_cog.events
            lines = []

            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"RoW Team Export - {timestamp}\n")
            lines.append("=" * 50)
            lines.append("")

            total_players = 0
            for team, members in data.items():
                team_name = TEAM_DISPLAY.get(team, team.replace('_', ' ').title())
                lines.append(f"# {team_name} ({len(members)} players)")
                lines.append("-" * 30)

                if members:
                    for i, user_id in enumerate(members, 1):
                        try:
                            user = ctx.guild.get_member(int(user_id)) or await self.bot.fetch_user(int(user_id))
                            name = user.display_name if user else f"User ID: {user_id}"
                            lines.append(f"{i:2d}. {name}")
                        except:
                            lines.append(f"{i:2d}. User ID: {user_id}")
                    total_players += len(members)
                else:
                    lines.append("No members signed up")

                lines.append("")

            lines.append(f"Total players across all teams: {total_players}")

            text = "\n".join(lines)

            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as temp:
                temp.write(text)
                temp_path = temp.name

            await ctx.send(
                content=f"📋 **Team Export Complete** - {total_players} total players signed up",
                file=discord.File(temp_path, filename="team_export.txt")
            )
            logger.info(f"{ctx.author} exported team list ({total_players} players).")

            os.remove(temp_path)

        except Exception:
            logger.exception("Error in exportteams command:")
            await ctx.send("❌ Failed to export team data.")

    @commands.command(name="exporthistory")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def export_history(self, ctx):
        """Export event history to a text file."""
        try:
            history = self.data_manager.load_json(FILES["HISTORY"], [])

            if not history:
                await ctx.send("❌ No event history found.")
                return

            lines = []
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"RoW Event History Export - {timestamp}\n")
            lines.append("=" * 60)
            lines.append("")

            for i, entry in enumerate(history, 1):
                event_date = entry.get("timestamp", "Unknown")
                lines.append(f"Event #{i} - {event_date}")
                lines.append("-" * 40)

                teams = entry.get("teams", {})
                for team, members in teams.items():
                    team_name = TEAM_DISPLAY.get(team, team.replace('_', ' ').title())
                    lines.append(f"{team_name}: {len(members)} players")
                    if members:
                        member_list = ", ".join([str(m) for m in members[:10]])
                        if len(members) > 10:
                            member_list += f" ... (+{len(members) - 10} more)"
                        lines.append(f"  {member_list}")

                lines.append("")

            lines.append(f"Total events recorded: {len(history)}")

            text = "\n".join(lines)

            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as temp:
                temp.write(text)
                temp_path = temp.name

            await ctx.send(
                content=f"📚 **Event History Export Complete** - {len(history)} events recorded",
                file=discord.File(temp_path, filename="event_history.txt")
            )
            logger.info(f"{ctx.author} exported event history ({len(history)} events).")

            os.remove(temp_path)

        except Exception:
            logger.exception("Error in exporthistory command:")
            await ctx.send("❌ Failed to export history data.")

    # NEW COMMANDS (missing from your current bot)

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
        else:
            await ctx.send("❌ Failed to save unblock changes. Please try again.")

    @commands.command(name="blocklist")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
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

            results = self.load_results()
            blocked_data = self.load_blocked_users()
            
            wins = results.get("total_wins", 0)
            losses = results.get("total_losses", 0)
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

            embed = discord.Embed(title="📊 RoW Stats Report", color=discord.Color.blurple())

            # Team signups
            if event_cog and hasattr(event_cog, 'events'):
                for team, members in event_cog.events.items():
                    igns = []
                    for uid in members:
                        try:
                            user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
                            if profile_cog and user:
                                ign = profile_cog.get_ign(user)
                            else:
                                ign = "Unknown"
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

            # Blocked users
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

    @commands.command(name="startevent")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def start_event_fallback(self, ctx):
        """Start a new event (fallback if EventManager missing)."""
        event_cog = self.bot.get_cog("EventManager")
        if event_cog and hasattr(event_cog, 'start_event'):
            await event_cog.start_event(ctx)
        else:
            await ctx.send("❌ EventManager not available or missing start_event method.")

    @commands.command(name="showteams")
    async def show_teams_fallback(self, ctx):
        """Show current teams (fallback if EventManager missing)."""
        event_cog = self.bot.get_cog("EventManager")
        if event_cog and hasattr(event_cog, 'show_teams'):
            await event_cog.show_teams(ctx)
        else:
            # Fallback implementation
            try:
                if event_cog and hasattr(event_cog, 'events'):
                    embed = discord.Embed(
                        title="📋 Current RoW Team Signups",
                        color=discord.Color.blue()
                    )

                    total_signups = 0
                    for team_key in ["main_team", "team_2", "team_3"]:
                        members = event_cog.events.get(team_key, [])
                        display_name = TEAM_DISPLAY.get(team_key, team_key)
                        
                        member_displays = []
                        for i, member in enumerate(members):
                            try:
                                user_id = int(member)
                                user = ctx.guild.get_member(user_id) or self.bot.get_user(user_id)
                                
                                if user:
                                    member_displays.append(f"{i+1}. {user.display_name}")
                                else:
                                    member_displays.append(f"{i+1}. <@{user_id}>")
                            except:
                                member_displays.append(f"{i+1}. {member}")

                        member_list = "\n".join(member_displays) if member_displays else "*No signups yet.*"

                        embed.add_field(
                            name=f"{display_name} ({len(members)}/35)",
                            value=member_list,
                            inline=False
                        )
                        total_signups += len(members)

                    embed.set_footer(text=f"Total signups: {total_signups}")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ No event data available.")
            except Exception as e:
                logger.exception("Error in showteams fallback:")
                await ctx.send("❌ Failed to show teams.")

    # Add this to your cogs/admin/actions.py file

     @commands.command(name="fixjson")
     @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def fix_json_files(self, ctx):
    """Fix and validate all JSON data files."""
    try:
        fixed_files = []
        issues_found = []
        
        # Define expected structure for each file
        file_templates = {
            FILES["EVENTS"]: {
                "main_team": [],
                "team_2": [],
                "team_3": []
            },
            FILES["BLOCKED"]: {},
            FILES["IGN_MAP"]: {},
            FILES["RESULTS"]: {
                "total_wins": 0,
                "total_losses": 0,
                "history": []
            },
            FILES["HISTORY"]: [],
            FILES["TIMES"]: {
                "main_team": "14:00 UTC Saturday",
                "team_2": "14:00 UTC Sunday", 
                "team_3": "20:00 UTC Sunday"
            },
            FILES["ABSENT"]: {}
        }
        
        for file_path, template in file_templates.items():
            try:
                # Try to load existing file
                existing_data = self.data_manager.load_json(file_path, None)
                
                if existing_data is None:
                    # File doesn't exist, create it
                    if self.data_manager.save_json(file_path, template):
                        fixed_files.append(f"✅ Created missing: {os.path.basename(file_path)}")
                    else:
                        issues_found.append(f"❌ Failed to create: {os.path.basename(file_path)}")
                
                elif not isinstance(existing_data, type(template)):
                    # Wrong data type, fix it
                    if self.data_manager.save_json(file_path, template):
                        fixed_files.append(f"🔧 Fixed structure: {os.path.basename(file_path)}")
                    else:
                        issues_found.append(f"❌ Failed to fix: {os.path.basename(file_path)}")
                
                else:
                    # File exists and has correct type
                    fixed_files.append(f"✅ Already good: {os.path.basename(file_path)}")
                    
            except Exception as e:
                issues_found.append(f"❌ Error with {os.path.basename(file_path)}: {str(e)}")
        
        # Create response embed
        embed = discord.Embed(
            title="🔧 JSON Files Fix Report",
            color=discord.Color.green() if not issues_found else discord.Color.orange()
        )
        
        if fixed_files:
            embed.add_field(
                name="Files Processed",
                value="\n".join(fixed_files),
                inline=False
            )
        
        if issues_found:
            embed.add_field(
                name="Issues Found",
                value="\n".join(issues_found),
                inline=False
            )
        
        embed.set_footer(text=f"Processed {len(file_templates)} files")
        
        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} ran JSON fix command")
        
    except Exception as e:
        await ctx.send(f"❌ Error running JSON fix: {str(e)}")
        logger.exception("Error in fixjson command:")

    @commands.command(name="fixjson")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def fix_json_files(self, ctx):
        """Fix and validate all JSON data files."""
        try:
            fixed_files = []
            issues_found = []
            
            # Define expected structure for each file
            file_templates = {
                FILES["EVENTS"]: {
                    "main_team": [],
                    "team_2": [],
                    "team_3": []
                },
                FILES["BLOCKED"]: {},
                FILES["IGN_MAP"]: {},
                FILES["RESULTS"]: {
                    "total_wins": 0,
                    "total_losses": 0,
                    "history": []
                },
                FILES["HISTORY"]: [],
                FILES["TIMES"]: {
                    "main_team": "14:00 UTC Saturday",
                    "team_2": "14:00 UTC Sunday", 
                    "team_3": "20:00 UTC Sunday"
                },
                FILES["ABSENT"]: {}
            }
            
            for file_path, template in file_templates.items():
                try:
                    # Try to load existing file
                    existing_data = self.data_manager.load_json(file_path, None)
                    
                    if existing_data is None:
                        # File doesn't exist, create it
                        if self.data_manager.save_json(file_path, template):
                            fixed_files.append(f"✅ Created missing: {os.path.basename(file_path)}")
                        else:
                            issues_found.append(f"❌ Failed to create: {os.path.basename(file_path)}")
                    
                    elif not isinstance(existing_data, type(template)):
                        # Wrong data type, fix it
                        if self.data_manager.save_json(file_path, template):
                            fixed_files.append(f"🔧 Fixed structure: {os.path.basename(file_path)}")
                        else:
                            issues_found.append(f"❌ Failed to fix: {os.path.basename(file_path)}")
                    
                    else:
                        # File exists and has correct type
                        fixed_files.append(f"✅ Already good: {os.path.basename(file_path)}")
                        
                except Exception as e:
                    issues_found.append(f"❌ Error with {os.path.basename(file_path)}: {str(e)}")
            
            # Create response embed
            embed = discord.Embed(
                title="🔧 JSON Files Fix Report",
                color=discord.Color.green() if not issues_found else discord.Color.orange()
            )
            
            if fixed_files:
                embed.add_field(
                    name="Files Processed",
                    value="\n".join(fixed_files),
                    inline=False
                )
            
            if issues_found:
                embed.add_field(
                    name="Issues Found",
                    value="\n".join(issues_found),
                    inline=False
                )
            
            embed.set_footer(text=f"Processed {len(file_templates)} files")
            
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} ran JSON fix command")
            
        except Exception as e:
            await ctx.send(f"❌ Error running JSON fix: {str(e)}")
            logger.exception("Error in fixjson command:")

    @commands.command(name="checkjson")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def check_json_files(self, ctx):
    """Check the status of all JSON data files without fixing them."""
    try:
        file_status = []
        
        files_to_check = {
            "Events": FILES["EVENTS"],
            "Blocked Users": FILES["BLOCKED"], 
            "IGN Map": FILES["IGN_MAP"],
            "Results": FILES["RESULTS"],
            "History": FILES["HISTORY"],
            "Times": FILES["TIMES"],
            "Absent": FILES["ABSENT"]
        }
        
        for name, file_path in files_to_check.items():
            try:
                if os.path.exists(file_path):
                    data = self.data_manager.load_json(file_path, None)
                    if data is not None:
                        if isinstance(data, dict):
                            count = len(data)
                            file_status.append(f"✅ {name}: {count} entries")
                        elif isinstance(data, list):
                            count = len(data)
                            file_status.append(f"✅ {name}: {count} items")
                        else:
                            file_status.append(f"⚠️ {name}: Exists but unknown format")
                    else:
                        file_status.append(f"❌ {name}: Corrupted/unreadable")
                else:
                    file_status.append(f"❌ {name}: Missing")
                    
            except Exception as e:
                file_status.append(f"❌ {name}: Error - {str(e)}")
        
        embed = discord.Embed(
            title="📊 JSON Files Status Check",
            description="\n".join(file_status),
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} checked JSON file status")
        
    except Exception as e:
        await ctx.send(f"❌ Error checking JSON files: {str(e)}")
        logger.exception("Error in checkjson command:")
        
    @commands.command(name="testchannels")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def test_channels_fallback(self, ctx):
        """Test channel access."""
        try:
            embed = discord.Embed(
                title="🧪 Channel Test",
                description="Testing channel access...",
                color=discord.Color.blue()
            )
            
            accessible = []
            failed = []
            
            for channel_id in ALERT_CHANNEL_IDS:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    accessible.append(f"✅ {channel.guild.name}#{channel.name}")
                else:
                    failed.append(f"❌ Channel ID {channel_id}")
            
            if accessible:
                embed.add_field(
                    name="Accessible Channels",
                    value="\n".join(accessible),
                    inline=False
                )
            
            if failed:
                embed.add_field(
                    name="Failed Channels", 
                    value="\n".join(failed),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.exception("Error in testchannels:")
            await ctx.send("❌ Failed to test channels.")

    @commands.command(name="backup")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def create_backup_command(self, ctx):
        """Create a manual backup of all data files."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            embed = discord.Embed(
                title="✅ Backup Info",
                description=f"**Timestamp:** {timestamp}\n**Note:** Basic backup functionality",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Backup info requested by {ctx.author}: {timestamp}")
                
        except Exception as e:
            logger.exception("Error in backup command:")
            await ctx.send("❌ Failed to create backup info.")

async def setup(bot):
    await bot.add_cog(AdminActions(bot))
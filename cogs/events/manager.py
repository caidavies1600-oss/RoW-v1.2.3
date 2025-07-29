# cogs/events/manager.py

import discord
from discord.ext import commands
from datetime import datetime, timedelta

from utils.data_manager import DataManager
from utils.logger import setup_logger
from utils.helpers import Helpers
from utils.validators import Validators
from config.constants import (
    FILES, EMOJIS, TEAM_DISPLAY, COLORS, ALERT_CHANNEL_ID, DEFAULT_TIMES
)
from config.settings import (
    ADMIN_ROLE_IDS, MAIN_TEAM_ROLE_ID, ROW_NOTIFICATION_ROLE_ID,
    MAX_TEAM_SIZE
)

from cogs.events.signup_view import EventSignupView

logger = setup_logger("event_manager")

class EventManager(commands.Cog, name="EventManager"):
    """Core event management functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

        self.events = self.data_manager.load_json(FILES["EVENTS"], self._default_events())
        self.blocked_users = self.data_manager.load_json(FILES["BLOCKED"], {})
        
        # FORCE reload times from constants to pick up code changes
        self.event_times = DEFAULT_TIMES.copy()
        self.data_manager.save_json(FILES["TIMES"], self.event_times)
        logger.info("✅ Event times loaded from DEFAULT_TIMES constants")

    def _default_events(self):
        return {"main_team": [], "team_2": [], "team_3": []}

    def save_events(self):
        if not self.data_manager.save_json(FILES["EVENTS"], self.events):
            logger.error("❌ Failed to save events.json")

    def save_blocked_users(self):
        if not self.data_manager.save_json(FILES["BLOCKED"], self.blocked_users):
            logger.error("❌ Failed to save blocked_users.json")

    def save_times(self):
        if not self.data_manager.save_json(FILES["TIMES"], self.event_times):
            logger.error("❌ Failed to save row_times.json")

    def save_history(self):
        history = self.data_manager.load_json(FILES["HISTORY"], [])
        if not isinstance(history, list):
            logger.warning("⚠️ Event history file was not a list. Resetting.")
            history = []

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "teams": self.events.copy()
        }
        history.append(entry)

        if len(history) > 50:
            history = history[-50:]

        if self.data_manager.save_json(FILES["HISTORY"], history):
            logger.info("✅ Event history updated")
        else:
            logger.error("❌ Failed to save events_history.json")

    def is_user_blocked(self, user_id: int) -> bool:
        entry = self.blocked_users.get(str(user_id))
        if not entry:
            return False

        blocked_at = entry.get("blocked_at")
        duration = entry.get("ban_duration_days", 7)

        if not blocked_at:
            return False

        try:
            expiry = datetime.fromisoformat(blocked_at) + timedelta(days=duration)
            if datetime.utcnow() >= expiry:
                del self.blocked_users[str(user_id)]
                self.save_blocked_users()
                return False
            return True
        except Exception as e:
            logger.warning(f"⚠️ Malformed block entry for {user_id}: {e}")
            return False

    def block_user(self, user_id: int, blocked_by: int, days: int):
        self.blocked_users[str(user_id)] = {
            "blocked_by": str(blocked_by),
            "blocked_at": datetime.utcnow().isoformat(),
            "ban_duration_days": days
        }
        self.save_blocked_users()
        logger.info(f"🚫 User {user_id} blocked by {blocked_by} for {days} days")

    def unblock_user(self, user_id: int):
        if str(user_id) in self.blocked_users:
            del self.blocked_users[str(user_id)]
            self.save_blocked_users()
            logger.info(f"✅ User {user_id} unblocked")

    async def get_user_display_name(self, user: discord.User) -> str:
        profile_cog = self.bot.get_cog("Profile")
        return profile_cog.get_ign(user) if profile_cog else user.display_name

    @commands.command(name="forceupdatetimes")
    @commands.check(lambda ctx: Validators.is_admin(ctx.author))
    async def force_update_times(self, ctx):
        """Force update times from constants"""
        import os
        times_file = FILES["TIMES"]
        if os.path.exists(times_file):
            os.remove(times_file)
        self.event_times = DEFAULT_TIMES.copy()
        self.data_manager.save_json(FILES["TIMES"], self.event_times)
        await ctx.send("✅ Times force updated from constants!")
        logger.info(f"{ctx.author} force updated event times")

    @commands.command(name="startevent")
    @commands.check(lambda ctx: Validators.is_admin(ctx.author))
    async def start_event(self, ctx):
        try:
            self.save_history()
            self.events = self._default_events()
            self.save_events()

            logger.info(f"{ctx.author} started new event")

            embed = discord.Embed(
                title="📢 Weekly RoW Sign-Up",
                description=self._create_event_description(),
                color=COLORS["PRIMARY"]
            )
            embed.set_footer(text="First come, first served – choose wisely!")

            view = EventSignupView(self)
            alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)

            if not alert_channel:
                await ctx.send(f"{EMOJIS['ERROR']} Could not find the alert channel.")
                return

            await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>",
                embed=embed,
                view=view
            )

            await ctx.send("✅ Event posted in the alert channel.")

        except Exception as e:
            logger.exception("Failed to start event")
            await ctx.send(f"{EMOJIS['ERROR']} Failed to start event.")

    def _create_event_description(self) -> str:
        lines = [
            f"Hey! Pick your team for this week's **RoW Event**.\n",
            f"{EMOJIS['CALENDAR']} **Schedule**:"
        ]
        for team_key, display_name in TEAM_DISPLAY.items():
            time_str = self.event_times.get(team_key, "TBD")
            lines.append(f"{display_name} → {EMOJIS['CLOCK']} `{time_str}`")

        lines.append(f"\n{EMOJIS['SUCCESS']} Use the buttons below to join!")
        return "\n".join(lines)

    @commands.command(name="showteams")
    async def show_teams(self, ctx):
        """Show this week's teams"""
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and not profile_cog.has_ign(ctx.author):
            embed = discord.Embed(
                title="⚠️ IGN Not Set",
                description="You haven't set your IGN yet. Use `!setign YourName` to set it.",
                color=COLORS["WARNING"]
            )
            await ctx.send(embed=embed)

        embed = discord.Embed(
            title="📋 Current RoW Team Signups",
            color=COLORS["INFO"]
        )

        for team_key in ["main_team", "team_2", "team_3"]:
            members = self.events.get(team_key, [])
            display_name = TEAM_DISPLAY.get(team_key, team_key)
            
            # Handle user ID to display name conversion
            member_displays = []
            for i, member in enumerate(members):
                try:
                    # Convert to int if it's a string
                    user_id = int(member)
                    
                    # Try to get the user object
                    user = ctx.guild.get_member(user_id) or self.bot.get_user(user_id)
                    
                    if user:
                        # Get IGN if available, otherwise use display name
                        if profile_cog and profile_cog.has_ign(user):
                            display_name_str = profile_cog.get_ign(user)
                        else:
                            display_name_str = user.display_name
                        member_displays.append(f"{i+1}. {display_name_str}")
                    else:
                        # User not found, use mention as fallback
                        member_displays.append(f"{i+1}. <@{user_id}>")
                        
                except (ValueError, TypeError):
                    # If member is already a string (IGN), use it directly
                    member_displays.append(f"{i+1}. {member}")
                except Exception as e:
                    # Log error and use fallback
                    logger.warning(f"Error processing member {member}: {e}")
                    member_displays.append(f"{i+1}. Unknown User")

            member_list = "\n".join(member_displays) if member_displays else "*No signups yet.*"

            embed.add_field(
                name=f"{display_name} ({len(members)}/{MAX_TEAM_SIZE})",
                value=member_list,
                inline=False
            )

        total_signups = sum(len(members) for members in self.events.values())
        embed.set_footer(text=f"Total signups: {total_signups}")

        await ctx.send(embed=embed)

    @commands.command(name="debugtimes")
    @commands.check(lambda ctx: Validators.is_admin(ctx.author))
    async def debug_times(self, ctx):
        """Debug command to show current times and constants"""
        from config.constants import DEFAULT_TIMES as CONST_TIMES
        
        embed = discord.Embed(title="🔧 Time Debug Info", color=COLORS["INFO"])
        embed.add_field(
            name="Current Event Times (self.event_times)",
            value="\n".join([f"{k}: {v}" for k, v in self.event_times.items()]),
            inline=False
        )
        embed.add_field(
            name="Constants DEFAULT_TIMES",
            value="\n".join([f"{k}: {v}" for k, v in CONST_TIMES.items()]),
            inline=False
        )
        
        times_file_exists = self.data_manager.load_json(FILES["TIMES"], None)
        embed.add_field(
            name="Times File Contents",
            value=str(times_file_exists) if times_file_exists else "File not found",
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def auto_post_signup(self, ctx):
        """Used by scheduler to auto-post a signup message."""
        try:
            embed = discord.Embed(
                title="📢 Weekly RoW Sign-Up",
                description=self._create_event_description(),
                color=COLORS["PRIMARY"]
            )
            embed.set_footer(text="First come, first served – choose wisely!")
            view = EventSignupView(self)

            alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
            if not alert_channel:
                logger.error("⚠️ ALERT_CHANNEL_ID does not match any channel in this guild.")
                return

            await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>",
                embed=embed,
                view=view
            )
            logger.info("✅ Auto-posted weekly signup")
        except Exception as e:
            logger.exception("❌ Failed to auto-post signup")

    async def reset_event_state(self):
        self.bot.event_active = False
        self.bot.event_team = None
        self.bot.attendance = {}
        self.bot.checked_in = set()

async def setup(bot):
    await bot.add_cog(EventManager(bot))
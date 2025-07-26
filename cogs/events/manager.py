# cogs/events/manager.py

import discord
from discord.ext import commands
from datetime import datetime, timedelta

from utils.data_manager import DataManager
from utils.logger import setup_logger
from utils.helpers import Helpers
from utils.validators import Validators
from config.constants import (
    FILES, EMOJIS, TEAM_DISPLAY, COLORS, ALERT_CHANNEL_IDS, ALERT_CHANNEL_ID
)
from config.settings import (
    ADMIN_ROLE_IDS, MAIN_TEAM_ROLE_ID, ROW_NOTIFICATION_ROLE_ID,
    MAX_TEAM_SIZE, DEFAULT_TIMES
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
        self.event_times = self.data_manager.load_json(FILES["TIMES"], DEFAULT_TIMES)

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

    async def post_to_all_channels(self, content=None, embed=None, view=None):
        """Post a message to all configured alert channels"""
        posted_channels = []
        failed_channels = []
        
        for channel_id in ALERT_CHANNEL_IDS:
            try:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(content=content, embed=embed, view=view)
                    posted_channels.append(f"{channel.guild.name}#{channel.name}")
                    logger.info(f"✅ Posted to {channel.guild.name}#{channel.name}")
                else:
                    failed_channels.append(f"Channel ID {channel_id} (not found)")
                    logger.warning(f"⚠️ Channel {channel_id} not found")
            except Exception as e:
                failed_channels.append(f"Channel ID {channel_id} (error: {e})")
                logger.error(f"❌ Failed to post to channel {channel_id}: {e}")
        
        return posted_channels, failed_channels

    @commands.command(name="startevent")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
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
            
            # Post to all configured channels
            posted, failed = await self.post_to_all_channels(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>",
                embed=embed,
                view=view
            )

            # Send response to command channel
            response_parts = []
            if posted:
                response_parts.append(f"✅ Event posted to: {', '.join(posted)}")
            if failed:
                response_parts.append(f"⚠️ Failed to post to: {', '.join(failed)}")
            
            await ctx.send("\n".join(response_parts) if response_parts else "❌ Failed to post to any channels")

        except Exception as e:
            logger.exception("Failed to start event")
            await ctx.send(f"{EMOJIS['ERROR']} Failed to start event: {e}")

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

    @commands.command(name="testchannels")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def test_channels(self, ctx):
        """Test posting to all configured channels"""
        test_embed = discord.Embed(
            title="🧪 Channel Test",
            description="Testing multi-channel posting functionality",
            color=COLORS["INFO"]
        )
        
        posted, failed = await self.post_to_all_channels(
            content="🧪 **Test Message**",
            embed=test_embed
        )
        
        response_parts = [f"**Multi-Channel Test Results:**"]
        if posted:
            response_parts.append(f"✅ **Successfully posted to:**\n• {chr(10).join(posted)}")
        if failed:
            response_parts.append(f"❌ **Failed to post to:**\n• {chr(10).join(failed)}")
            
        await ctx.send("\n\n".join(response_parts))

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

            posted, failed = await self.post_to_all_channels(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>",
                embed=embed,
                view=view
            )
            
            if posted:
                logger.info(f"✅ Auto-posted weekly signup to: {', '.join(posted)}")
            if failed:
                logger.warning(f"⚠️ Failed to auto-post to: {', '.join(failed)}")
                
        except Exception as e:
            logger.exception("❌ Failed to auto-post signup")

    async def reset_event_state(self):
        self.bot.event_active = False
        self.bot.event_team = None
        self.bot.attendance = {}
        self.bot.checked_in = set()

async def setup(bot):
    await bot.add_cog(EventManager(bot))
# cogs/events/manager.py

from datetime import datetime, timedelta

import discord
from discord.ext import commands

from cogs.events.signup_view import EventSignupView
from config.constants import ALERT_CHANNEL_ID, COLORS, EMOJIS, FILES, TEAM_DISPLAY
from config.settings import (
    DEFAULT_TIMES,
    MAIN_TEAM_ROLE_ID,
    MAX_TEAM_SIZE,
    RESTRICT_MAIN_TEAM,
    ROW_NOTIFICATION_ROLE_ID,
)
from utils.helpers import Helpers
from utils.integrated_data_manager import data_manager
from utils.logger import setup_logger
from utils.validators import Validators

logger = setup_logger("event_manager")


class EventManager(commands.Cog, name="EventManager"):
    """
    Core event management functionality.

    Features:
    - Event creation and signup management
    - Team roster tracking and display
    - User blocking system
    - Signup locking controls
    - Auto-posting and scheduling
    - Event history tracking
    """

    def __init__(self, bot):
        self.bot = bot
        self.events = {"main_team": [], "team_2": [], "team_3": []}
        self.data_manager = data_manager
        self.blocked_users = {}
        self.event_times = DEFAULT_TIMES
        self.signup_locked = False

    async def load_events(self):
        """Load events with new integrated manager."""
        data = await self.data_manager.load_data(
            FILES["EVENTS"],
            default={"main_team": [], "team_2": [], "team_3": []},
        )
        self.events = data

    async def save_events(self) -> bool:
        """Save events with atomic operations."""
        return await self.data_manager.save_data(
            FILES["EVENTS"], self.events, sync_to_sheets=True
        )

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_events()
        # Load signup lock state
        lock_data = await self.data_manager.load_data(FILES["SIGNUP_LOCK"], default=False)
        self.signup_locked = bool(lock_data)
        
        # Load blocked users
        blocked_data = await self.data_manager.load_data(FILES["BLOCKED"], default={})
        self.blocked_users = blocked_data

    def _default_events(self):
        """
        Create default empty event structure.

        Returns:
            dict: Default event structure with empty teams
        """
        return {"main_team": [], "team_2": [], "team_3": []}

    async def save_blocked_users(self):
        """Save blocked users data to file and sync to Google Sheets."""
        if not await self.data_manager.save_data(
            FILES["BLOCKED"], self.blocked_users, sync_to_sheets=True
        ):
            logger.error("❌ Failed to save blocked_users.json")
        else:
            logger.info("✅ Blocked users saved and synced to Sheets")

    def save_times(self):
        """Save event times configuration to file."""
        if not self.data_manager.save_data(FILES["TIMES"], self.event_times):
            logger.error("❌ Failed to save row_times.json")

    async def save_signup_lock(self):
        """Save signup lock state."""
        try:
            await self.data_manager.save_data(FILES["SIGNUP_LOCK"], self.signup_locked)
        except Exception as e:
            logger.error(f"Failed to save signup lock: {e}")

    async def lock_signups(self):
        """Lock signups and save state."""
        self.signup_locked = True
        await self.save_signup_lock()
        logger.info("🔒 Signups have been locked")

    async def unlock_signups(self):
        """Unlock signups and save state."""
        self.signup_locked = False
        await self.save_signup_lock()
        logger.info("🔓 Signups have been unlocked")

    def is_signup_locked(self) -> bool:
        """Check if signups are currently locked."""
        return self.signup_locked

    async def save_history(self):
        """
        Save current event state to history.

        Maintains a rolling history of the last 50 events.
        Each entry contains timestamp and team compositions.
        """
        history = await self.data_manager.load_data(FILES["HISTORY"], default=[])
        if not isinstance(history, list):
            logger.warning("⚠️ Event history file was not a list. Resetting.")
            history = []

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "teams": self.events.copy(),
        }
        history.append(entry)

        if len(history) > 50:
            history = history[-50:]

        if await self.data_manager.save_data(FILES["HISTORY"], history):
            logger.info("✅ Event history updated")
        else:
            logger.error("❌ Failed to save events_history.json")

    async def is_user_blocked(self, user_id: int) -> bool:
        """
        Check if a user is currently blocked from signups.

        Args:
            user_id: Discord user ID to check

        Returns:
            bool: True if user is blocked and block hasn't expired
        """
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
                await self.save_blocked_users()
                return False
            return True
        except Exception as e:
            logger.warning(f"⚠️ Malformed block entry for {user_id}: {e}")
            return False

    async def block_user(self, user_id: int, blocked_by: int, days: int):
        """
        Block a user from signing up for events.

        Args:
            user_id: Discord ID of user to block
            blocked_by: Discord ID of admin who blocked
            days: Number of days to block for
        """
        self.blocked_users[str(user_id)] = {
            "blocked_by": str(blocked_by),
            "blocked_at": datetime.utcnow().isoformat(),
            "ban_duration_days": days,
        }
        await self.save_blocked_users()
        logger.info(f"🚫 User {user_id} blocked by {blocked_by} for {days} days")

    async def unblock_user(self, user_id: int):
        """Unblock a user, allowing them to sign up again."""
        if str(user_id) in self.blocked_users:
            del self.blocked_users[str(user_id)]
            await self.save_blocked_users()
            logger.info(f"✅ User {user_id} unblocked")

    async def get_user_display_name(self, user: discord.User) -> str:
        profile_cog = self.bot.get_cog("Profile")
        return profile_cog.get_ign(user) if profile_cog else user.display_name

    @commands.command(name="startevent")
    @commands.check(
        lambda ctx: isinstance(ctx.author, discord.Member)
        and Validators.is_admin(ctx.author)
    )
    async def start_event(self, ctx):
        """
        Start a new event, resetting signups and notifying users.

        Args:
            ctx: Command context
        """
        try:
            await self.save_history()
            self.events = self._default_events()
            await self.unlock_signups()  # Reset signup lock when starting new event
            await self.save_events()

            logger.info(f"{ctx.author} started new event")

            embed = discord.Embed(
                title="📢 Weekly RoW Sign-Up",
                description=self._create_event_description(),
                color=COLORS["PRIMARY"],
            )
            embed.set_footer(text="First come, first served – choose wisely!")

            view = EventSignupView(self)

            await ctx.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>", embed=embed, view=view
            )

            logger.info("✅ Event posted in current channel")

        except Exception:
            logger.exception("Failed to start event")
            await ctx.send(f"{EMOJIS['ERROR']} Failed to start event.")

    def _create_event_description(self) -> str:
        """
        Create formatted event description with schedules.

        Returns:
            str: Formatted event description with times and status
        """
        lines = [
            "Hey! Pick your team for this week's **RoW Event**.\n",
            f"{EMOJIS['CALENDAR']} **Schedule**:",
        ]
        for team_key, display_name in TEAM_DISPLAY.items():
            time_str = self.event_times.get(team_key, "TBD")
            lines.append(f"{display_name} → {EMOJIS['CLOCK']} `{time_str}`")

        lines.append(f"\n{EMOJIS['SUCCESS']} Use the buttons below to join!")

        # Add signup lock warning if locked
        if self.is_signup_locked():
            lines.append("\n🔒 **SIGNUPS ARE CURRENTLY LOCKED**")

        return "\n".join(lines)

    @commands.command(name="showteams")
    async def show_teams(self, ctx):
        """
        Display current team signups to the user.

        If the user hasn't set their IGN, prompt them to do so.

        Args:
            ctx: Command context
        """
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and not profile_cog.has_ign(ctx.author):
            embed = discord.Embed(
                title="⚠️ IGN Not Set",
                description="You haven't set your IGN yet. Use `!setign YourName` to set it.",
                color=COLORS["WARNING"],
            )
            await ctx.send(embed=embed)

        embed = discord.Embed(title="📋 Current RoW Team Signups", color=COLORS["INFO"])

        # Add signup lock status to title if locked
        if self.is_signup_locked():
            embed.title = "📋 Current RoW Team Signups 🔒 [LOCKED]"
            embed.color = COLORS["WARNING"]

        for team_key in ["main_team", "team_2", "team_3"]:
            members = self.events.get(team_key, [])
            display_name = TEAM_DISPLAY.get(team_key, team_key)
            member_list = Helpers.format_user_list(members)

            embed.add_field(
                name=f"{display_name} ({len(members)}/{MAX_TEAM_SIZE})",
                value=member_list or "*No signups yet.*",
                inline=False,
            )

        total_signups = sum(len(members) for members in self.events.values())
        footer_text = f"Total signups: {total_signups}"

        if self.is_signup_locked():
            footer_text += " | Signups are locked until next event"

        embed.set_footer(text=footer_text)

        await ctx.send(embed=embed)

    @commands.command(name="locksignups")
    @commands.check(
        lambda ctx: isinstance(ctx.author, discord.Member)
        and Validators.is_admin(ctx.author)
    )
    async def lock_signups_command(self, ctx):
        """
        Manually lock signups.

        Sends an alert to the designated channel.

        Args:
            ctx: Command context
        """
        if self.is_signup_locked():
            await ctx.send("🔒 Signups are already locked.")
            return

        await self.lock_signups()

        embed = discord.Embed(
            title="🔒 Signups Locked",
            description="Signups have been manually locked by an admin.",
            color=COLORS["WARNING"],
        )

        alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            await alert_channel.send(embed=embed)

        await ctx.send("✅ Signups have been locked.")

    @commands.command(name="unlocksignups")
    @commands.check(
        lambda ctx: isinstance(ctx.author, discord.Member)
        and Validators.is_admin(ctx.author)
    )
    async def unlock_signups_command(self, ctx):
        """
        Manually unlock signups.

        Sends an alert to the designated channel.

        Args:
            ctx: Command context
        """
        if not self.is_signup_locked():
            await ctx.send("🔓 Signups are already unlocked.")
            return

        await self.unlock_signups()

        embed = discord.Embed(
            title="🔓 Signups Unlocked",
            description="Signups have been manually unlocked by an admin.",
            color=COLORS["SUCCESS"],
        )

        alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            await alert_channel.send(embed=embed)

        await ctx.send("✅ Signups have been unlocked.")

    async def auto_post_signup(self, ctx):
        """
        Automatically post signup message in specified channel.

        Used by scheduler for automated event creation.

        Args:
            ctx: Context for message posting
        """
        try:
            embed = discord.Embed(
                title="📢 Weekly RoW Sign-Up",
                description=self._create_event_description(),
                color=COLORS["PRIMARY"],
            )
            embed.set_footer(text="First come, first served – choose wisely!")
            view = EventSignupView(self)

            await ctx.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>", embed=embed, view=view
            )
            logger.info("✅ Auto-posted weekly signup")
        except Exception:
            logger.exception("❌ Failed to auto-post signup")

    async def auto_show_teams_and_lock(self):
        """
        Automatically display final teams and lock signups.

        Used by scheduler for Thursday night lockout.
        Posts final roster to alert channel and locks further changes.
        """
        try:
            # Lock signups first
            await self.lock_signups()

            # Get alert channel
            alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
            if not alert_channel:
                logger.error(
                    "⚠️ ALERT_CHANNEL_ID does not match any channel in this guild."
                )
                return

            # Create teams display embed
            embed = discord.Embed(
                title="📋 Final Team Rosters 🔒 [SIGNUPS LOCKED]",
                description="Signups are now locked until next week's event!",
                color=COLORS["WARNING"],
            )

            total_signups = 0
            for team_key in ["main_team", "team_2", "team_3"]:
                members = self.events.get(team_key, [])
                display_name = TEAM_DISPLAY.get(team_key, team_key)
                member_list = Helpers.format_user_list(members)
                total_signups += len(members)

                embed.add_field(
                    name=f"{display_name} ({len(members)}/{MAX_TEAM_SIZE})",
                    value=member_list or "*No signups.*",
                    inline=False,
                )

            embed.set_footer(
                text=f"Total signups: {total_signups} | Locked at Thursday 23:59 UTC"
            )

            # Post with role mention
            await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>", embed=embed
            )

            logger.info(
                f"✅ Auto-posted final team rosters and locked signups ({total_signups} total)"
            )

        except Exception:
            logger.exception("❌ Failed to auto-show teams and lock signups")

    async def reset_event_state(self):
        """Reset all event-related state variables to defaults."""
        self.bot.event_active = False
        self.bot.event_team = None
        self.bot.attendance = {}
        self.bot.checked_in = set()

    async def clear_all_signups(self) -> bool:
        """
        Clear all event signups from storage.
        Used for testing and emergency resets.

        Returns:
            bool: Success status of clearing operation
        """
        try:
            # Reset all team signups to empty lists
            self.events = {"main_team": [], "team_2": [], "team_3": []}

            # Save the cleared state
            success = await self.data_manager.save_data(
                FILES["EVENTS"], self.events, sync_to_sheets=True
            )

            if success:
                logger.info("✅ Test signups cleared successfully")
            return success

        except Exception as e:
            logger.error(f"Failed to clear signups: {e}")
            return False

    def can_join_team(self, member: discord.Member, team: str) -> bool:
        """Check if member can join specific team."""
        if team == "main_team" and RESTRICT_MAIN_TEAM:
            return any(role.id == MAIN_TEAM_ROLE_ID for role in member.roles)
        return True  # Allow anyone to join any team if no restrictions


async def setup(bot):
    await bot.add_cog(EventManager(bot))

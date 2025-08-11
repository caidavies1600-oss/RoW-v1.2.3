"""
Admin notification system for real-time bot monitoring.

Features:
- Real-time startup progress tracking
- Error alerts and tracebacks
- Activity monitoring
- Health status updates
- Rich embed formatting
- Queue system for delayed notifications
- Activity type classification

This module provides direct communication with the bot owner
for critical events and monitoring.
"""

import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import discord

from utils.logger import setup_logger

logger = setup_logger("admin_notifier")


class AdminNotifier:
    """
    Real-time notification system for bot owner.

    Features:
    - Startup progress tracking
    - Error monitoring
    - Activity notifications
    - Health alerts
    - Message queueing
    - Rich embed formatting

    Attributes:
        bot: Discord bot instance
        admin_user_id: ID of bot owner
        admin_user: Discord user object of owner
        startup_embed: Tracking embed for startup
        notification_queue: Queue for delayed notifications
        is_ready: Initialization status
    """

    def __init__(self, bot, admin_user_id: int):
        self.bot = bot
        self.admin_user_id = admin_user_id
        self.admin_user = None
        self.startup_embed = None
        self.startup_message = None
        self.notification_queue = []
        self.is_ready = False

    async def initialize(self):
        """Initialize the notifier and get admin user."""
        try:
            if self.bot and self.bot.is_ready():
                self.admin_user = await self.bot.fetch_user(self.admin_user_id)
                self.is_ready = True
                logger.info(f"✅ Admin notifier initialized for {self.admin_user}")
            else:
                # Queue for later when bot is ready
                self.is_ready = False
        except Exception as e:
            logger.error(f"Failed to initialize admin notifier: {e}")

    async def send_startup_notification(self):
        """Send initial startup notification with tracking embed."""
        if not await self._ensure_ready():
            return

        try:
            embed = discord.Embed(
                title="🚀 Bot Starting Up",
                description="**RoW Bot is initializing...**",
                color=0x5865F2,
                timestamp=datetime.utcnow(),
            )

            embed.add_field(
                name="📊 Startup Progress", value="🔄 Initializing...", inline=False
            )

            embed.add_field(
                name="⏱️ Started At",
                value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
                inline=True,
            )

            embed.set_footer(text="Real-time startup monitoring")

            self.startup_message = await self.admin_user.send(embed=embed)
            self.startup_embed = embed

            logger.info("📤 Sent startup notification to admin")

        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")

    async def update_startup_progress(
        self, milestone: str, status: str = "✅", details: str = None
    ):
        """Update startup progress in real-time."""
        if not self.startup_embed or not self.startup_message:
            return

        try:
            # Update progress field
            progress_field = None
            for i, field in enumerate(self.startup_embed.fields):
                if field.name == "📊 Startup Progress":
                    progress_field = i
                    break

            if progress_field is not None:
                current_progress = self.startup_embed.fields[progress_field].value
                if current_progress == "🔄 Initializing...":
                    new_progress = f"{status} {milestone}"
                else:
                    new_progress = f"{current_progress}\n{status} {milestone}"

                # Keep only last 8 lines to avoid embed limits
                lines = new_progress.split("\n")
                if len(lines) > 8:
                    new_progress = "\n".join(lines[-8:])

                self.startup_embed.set_field_at(
                    progress_field,
                    name="📊 Startup Progress",
                    value=new_progress,
                    inline=False,
                )

            # Add details if provided
            if details:
                # Add or update details field
                details_field = None
                for i, field in enumerate(self.startup_embed.fields):
                    if field.name == "🔍 Details":
                        details_field = i
                        break

                if details_field is not None:
                    self.startup_embed.set_field_at(
                        details_field,
                        name="🔍 Details",
                        value=details[:1024],  # Discord field limit
                        inline=False,
                    )
                else:
                    self.startup_embed.add_field(
                        name="🔍 Details", value=details[:1024], inline=False
                    )

            await self.startup_message.edit(embed=self.startup_embed)

        except Exception as e:
            logger.error(f"Failed to update startup progress: {e}")

    async def send_startup_complete(
        self, success: bool, total_time: float, stats: Dict[str, Any]
    ):
        """Send startup completion notification."""
        if not await self._ensure_ready():
            return

        try:
            color = 0x57F287 if success else 0xED4245
            title = (
                "✅ Bot Started Successfully!" if success else "❌ Bot Startup Failed"
            )

            embed = discord.Embed(title=title, color=color, timestamp=datetime.utcnow())

            # Add timing info
            embed.add_field(
                name="⏱️ Startup Time", value=f"{total_time:.2f} seconds", inline=True
            )

            # Add stats
            if stats:
                embed.add_field(
                    name="📊 Statistics",
                    value=f"**Guilds:** {stats.get('guilds', 0)}\n**Cogs:** {stats.get('cogs', 0)}\n**Commands:** {stats.get('commands', 0)}",
                    inline=True,
                )

                if stats.get("data_fixes"):
                    embed.add_field(
                        name="🔧 Data Fixes",
                        value=f"{stats['data_fixes']} fixes applied",
                        inline=True,
                    )

            # Add final status
            if success:
                embed.add_field(
                    name="🎯 Status",
                    value="Bot is online and ready to serve!",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="🚨 Status",
                    value="Bot startup encountered critical errors. Check logs.",
                    inline=False,
                )

            await self.admin_user.send(embed=embed)

            # Clear startup tracking
            self.startup_embed = None
            self.startup_message = None

        except Exception as e:
            logger.error(f"Failed to send startup complete notification: {e}")

    async def send_error_alert(
        self,
        error_type: str,
        error: Exception,
        context: str = None,
        traceback_str: str = None,
    ):
        """Send immediate error alert."""
        if not await self._ensure_ready():
            return

        try:
            embed = discord.Embed(
                title="🚨 Bot Error Alert",
                description=f"**Error Type:** {error_type}",
                color=0xED4245,
                timestamp=datetime.utcnow(),
            )

            # Error details
            error_text = str(error)
            if len(error_text) > 1000:
                error_text = error_text[:1000] + "..."

            embed.add_field(
                name="❌ Error Message", value=f"```\n{error_text}\n```", inline=False
            )

            if context:
                embed.add_field(name="📍 Context", value=context[:1024], inline=False)

            # Add short traceback
            if traceback_str:
                short_traceback = "\n".join(
                    traceback_str.split("\n")[-5:]
                )  # Last 5 lines
                if len(short_traceback) > 1000:
                    short_traceback = "..." + short_traceback[-1000:]

                embed.add_field(
                    name="🔍 Traceback (Last 5 lines)",
                    value=f"```python\n{short_traceback}\n```",
                    inline=False,
                )

            embed.set_footer(text="Check logs for full details")

            await self.admin_user.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to send error alert: {e}")

    async def send_activity_notification(
        self, activity_type: str, details: Dict[str, Any]
    ):
        """Send runtime activity notifications."""
        if not await self._ensure_ready():
            return

        try:
            # Map activity types to colors and emojis
            activity_config = {
                "command_executed": {
                    "color": 0x5DADE2,
                    "emoji": "⚡",
                    "title": "Command Executed",
                },
                "user_blocked": {
                    "color": 0xED4245,
                    "emoji": "🚫",
                    "title": "User Blocked",
                },
                "user_unblocked": {
                    "color": 0x57F287,
                    "emoji": "✅",
                    "title": "User Unblocked",
                },
                "event_started": {
                    "color": 0x5865F2,
                    "emoji": "📢",
                    "title": "Event Started",
                },
                "result_recorded": {
                    "color": 0xFEE75C,
                    "emoji": "🏆",
                    "title": "Result Recorded",
                },
                "auto_task": {
                    "color": 0x6C757D,
                    "emoji": "🤖",
                    "title": "Automated Task",
                },
                "data_sync": {"color": 0x17A2B8, "emoji": "🔄", "title": "Data Sync"},
                "critical_error": {
                    "color": 0xED4245,
                    "emoji": "🚨",
                    "title": "Critical Error",
                },
            }

            config = activity_config.get(
                activity_type,
                {"color": 0x6C757D, "emoji": "ℹ️", "title": "Bot Activity"},
            )

            embed = discord.Embed(
                title=f"{config['emoji']} {config['title']}",
                color=config["color"],
                timestamp=datetime.utcnow(),
            )

            # Add details dynamically
            for key, value in details.items():
                if key == "user" and isinstance(value, discord.User):
                    embed.add_field(
                        name="👤 User", value=f"{value.mention} ({value})", inline=True
                    )
                elif key == "command":
                    embed.add_field(name="⚡ Command", value=f"`{value}`", inline=True)
                elif key == "duration" and isinstance(value, (int, float)):
                    embed.add_field(
                        name="⏱️ Duration",
                        value=f"{value} days"
                        if activity_type == "user_blocked"
                        else f"{value:.2f}s",
                        inline=True,
                    )
                elif isinstance(value, str) and len(value) < 1024:
                    # Format key nicely
                    formatted_key = key.replace("_", " ").title()
                    embed.add_field(
                        name=formatted_key, value=value, inline=len(value) < 50
                    )

            await self.admin_user.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to send activity notification: {e}")

    async def send_health_alert(self, health_status: Dict[str, Any]):
        """Send periodic health status alerts."""
        if not await self._ensure_ready():
            return

        try:
            status = health_status.get("status", "unknown")
            score = health_status.get("health_score", 0)

            # Determine color based on health
            if status == "healthy":
                color = 0x57F287
                emoji = "💚"
            elif status == "warning":
                color = 0xFEE75C
                emoji = "💛"
            else:
                color = 0xED4245
                emoji = "❤️"

            embed = discord.Embed(
                title=f"{emoji} Bot Health Check",
                description=f"**Status:** {status.title()}\n**Score:** {score}/100",
                color=color,
                timestamp=datetime.utcnow(),
            )

            # Add component status
            if "cog_status" in health_status:
                cog_issues = [
                    name
                    for name, status in health_status["cog_status"].items()
                    if status.get("critical") and not status.get("loaded")
                ]
                if cog_issues:
                    embed.add_field(
                        name="🔧 Critical Cogs Down",
                        value="\n".join(cog_issues),
                        inline=True,
                    )

            # Add basic stats
            uptime = health_status.get("uptime")
            if uptime:
                days = uptime.days
                hours = uptime.seconds // 3600
                embed.add_field(name="⏱️ Uptime", value=f"{days}d {hours}h", inline=True)

            embed.add_field(
                name="📊 Commands",
                value=f"{health_status.get('command_count', 0)} executed",
                inline=True,
            )

            await self.admin_user.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")

    async def _ensure_ready(self) -> bool:
        """
        Ensure notifier is ready to send messages.

        Returns:
            bool: True if ready to send notifications

        Performs:
        - Bot readiness check
        - Admin user validation
        - Initialization if needed
        """
        if self.is_ready and self.admin_user:
            return True

        if not self.bot or not self.bot.is_ready():
            return False

        try:
            await self.initialize()
            return self.is_ready
        except:
            return False


# Global notifier instance
admin_notifier: Optional[AdminNotifier] = None


def setup_admin_notifier(bot, admin_user_id: int):
    """
    Setup the global admin notifier.

    Args:
        bot: Discord bot instance
        admin_user_id: User ID of bot owner

    Creates global notifier instance for bot-wide use.
    """
    global admin_notifier
    admin_notifier = AdminNotifier(bot, admin_user_id)
    logger.info(f"🔔 Admin notifier configured for user {admin_user_id}")


async def notify_startup_begin():
    """
    Notify admin that startup is beginning.

    Sends initial startup message with:
    - Timestamp
    - Progress tracking
    - Status indicators
    """
    if admin_notifier:
        await admin_notifier.send_startup_notification()


async def notify_startup_milestone(
    milestone: str, status: str = "✅", details: str = None
):
    """
    Notify admin of startup milestone.

    Args:
        milestone: Description of milestone reached
        status: Emoji indicator of status
        details: Optional additional information

    Updates startup tracking embed in real-time.
    """
    if admin_notifier:
        await admin_notifier.update_startup_progress(milestone, status, details)


async def notify_startup_complete(
    success: bool, total_time: float, stats: Dict[str, Any]
):
    """Notify admin that startup is complete."""
    if admin_notifier:
        await admin_notifier.send_startup_complete(success, total_time, stats)


async def notify_error(error_type: str, error: Exception, context: str = None):
    """
    Notify admin of an error.

    Args:
        error_type: Classification of error
        error: Exception object
        context: Additional context about error

    Features:
    - Error formatting
    - Traceback inclusion
    - Context preservation
    - Embed formatting
    """
    if admin_notifier:
        tb_str = traceback.format_exc() if hasattr(traceback, "format_exc") else None
        await admin_notifier.send_error_alert(error_type, error, context, tb_str)


async def notify_activity(activity_type: str, **details):
    """
    Notify admin of bot activity.

    Args:
        activity_type: Type of activity (command_executed, user_blocked, etc)
        **details: Activity-specific details

    Activities:
    - Command executions
    - User management
    - Event operations
    - System tasks
    - Data operations
    """
    if admin_notifier:
        await admin_notifier.send_activity_notification(activity_type, details)


async def notify_health_status(health_status: Dict[str, Any]):
    """
    Notify admin of health status.

    Args:
        health_status: Dictionary containing health metrics

    Monitors:
    - Overall bot health
    - Critical cog status
    - Command statistics
    - System uptime
    - Performance metrics
    """
    if admin_notifier and health_status.get("status") in ["warning", "critical"]:
        await admin_notifier.send_health_alert(health_status)

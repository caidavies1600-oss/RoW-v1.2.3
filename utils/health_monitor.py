"""
Health monitoring system for the Discord bot.

Features:
- Real-time health monitoring
- Critical system checks
- Performance tracking
- Error rate monitoring
- Channel access validation
- Task status tracking
- Cog status monitoring
- Admin notifications
- Health score calculation

Components:
- HealthMonitor: Core monitoring system
- HealthCommands: Admin commands
- Automated health checks
- Alert system
"""

from datetime import datetime
from typing import Any, Dict

import discord
from discord.ext import commands, tasks

from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("health_monitor")


class HealthMonitor:
    """
    Monitors bot health and performance.

    Features:
    - Command tracking
    - Error monitoring
    - Channel accessibility checks
    - Cog status validation
    - Task monitoring
    - Health scoring

    Attributes:
        bot: Discord bot instance
        data_manager: Data management interface
        health_data: Current health metrics
    """

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()
        self.health_data = {
            "startup_time": datetime.utcnow(),
            "command_count": 0,
            "error_count": 0,
            "last_error": None,
            "guild_count": 0,
            "channel_access": {},
            "cog_status": {},
            "task_status": {},
        }

    def record_command(self, command_name: str, success: bool = True):
        """Record command execution."""
        self.health_data["command_count"] += 1
        if not success:
            self.health_data["error_count"] += 1
            self.health_data["last_error"] = {
                "command": command_name,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def test_channel_access(self) -> Dict[str, bool]:
        """
        Test access to configured channels.

        Checks:
        - Channel existence
        - Bot permissions
        - Message sending rights
        - Embed permissions

        Returns:
            dict: Channel access status by channel ID
        """
        from config.constants import ALERT_CHANNEL_IDS

        results = {}
        for channel_id in ALERT_CHANNEL_IDS:
            channel = self.bot.get_channel(channel_id)
            if channel:
                # Check permissions
                perms = channel.permissions_for(channel.guild.me)
                can_send = perms.send_messages and perms.embed_links
                results[str(channel_id)] = {
                    "accessible": True,
                    "can_send": can_send,
                    "guild": channel.guild.name,
                    "name": channel.name,
                }
            else:
                results[str(channel_id)] = {
                    "accessible": False,
                    "can_send": False,
                    "guild": None,
                    "name": None,
                }

        self.health_data["channel_access"] = results
        return results

    def check_cog_status(self) -> Dict[str, bool]:
        """
        Check status of critical cogs.

        Validates:
        - Critical cog availability
        - Optional cog status
        - Cog loading state

        Returns:
            dict: Cog status information
        """
        critical_cogs = ["EventManager", "Profile", "Results"]
        optional_cogs = ["AdminActions", "ButtonCog", "Attendance"]

        status = {}
        for cog_name in critical_cogs + optional_cogs:
            cog = self.bot.get_cog(cog_name)
            status[cog_name] = {
                "loaded": cog is not None,
                "critical": cog_name in critical_cogs,
            }

        self.health_data["cog_status"] = status
        return status

    def check_task_status(self) -> Dict[str, Any]:
        """Check status of background tasks."""
        from services.scheduler import post_event_signup, post_weekly_summary

        status = {
            "event_signup": {
                "running": post_event_signup.is_running(),
                "failed": post_event_signup.failed(),
                "next_iteration": None,
            },
            "weekly_summary": {
                "running": post_weekly_summary.is_running(),
                "failed": post_weekly_summary.failed(),
                "next_iteration": None,
            },
        }

        try:
            if post_event_signup.is_running():
                status["event_signup"]["next_iteration"] = (
                    post_event_signup.next_iteration
                )
        except:
            pass

        try:
            if post_weekly_summary.is_running():
                status["weekly_summary"]["next_iteration"] = (
                    post_weekly_summary.next_iteration
                )
        except:
            pass

        self.health_data["task_status"] = status
        return status

    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        # Update current stats
        self.health_data["guild_count"] = len(self.bot.guilds)
        self.health_data["uptime"] = (
            datetime.utcnow() - self.health_data["startup_time"]
        )

        # Run checks
        channel_status = self.test_channel_access()
        cog_status = self.check_cog_status()
        task_status = self.check_task_status()

        # Calculate health score (0-100)
        score = 100

        # Deduct for critical cogs not loaded
        critical_cogs_down = sum(
            1
            for name, status in cog_status.items()
            if status["critical"] and not status["loaded"]
        )
        score -= critical_cogs_down * 25

        # Deduct for inaccessible channels
        inaccessible_channels = sum(
            1 for status in channel_status.values() if not status["accessible"]
        )
        score -= inaccessible_channels * 15

        # Deduct for failed tasks
        failed_tasks = sum(1 for status in task_status.values() if status["failed"])
        score -= failed_tasks * 20

        # Deduct for high error rate
        if self.health_data["command_count"] > 0:
            error_rate = (
                self.health_data["error_count"] / self.health_data["command_count"]
            )
            if error_rate > 0.1:  # More than 10% error rate
                score -= int(error_rate * 100)

        score = max(0, score)  # Don't go below 0

        return {
            **self.health_data,
            "health_score": score,
            "status": "healthy"
            if score >= 80
            else "warning"
            if score >= 60
            else "critical",
        }


# Global health monitor instance
health_monitor = None


def setup_health_monitoring(bot):
    """Setup health monitoring for the bot."""
    global health_monitor
    health_monitor = HealthMonitor(bot)
    logger.info("✅ Health monitoring configured")


def record_command_execution(command_name: str, success: bool = True):
    """Record command execution for health monitoring."""
    if health_monitor:
        health_monitor.record_command(command_name, success)


class HealthCommands(commands.Cog):
    """
    Health monitoring commands and tasks.

    Features:
    - Health check commands
    - Automated monitoring
    - Status reporting
    - Admin alerts
    - Visual status display
    """

    def __init__(self, bot):
        self.bot = bot
        self.health_check_task.start()

    def cog_unload(self):
        self.health_check_task.cancel()

    @tasks.loop(minutes=30)
    async def health_check_task(self):
        """
        Periodic health check task.

        Performs:
        - Health score calculation
        - Status validation
        - Critical issue detection
        - Admin notifications
        - Performance monitoring
        """
        try:
            if health_monitor:
                report = health_monitor.get_health_report()

                # Log health status
                status = report["status"]
                score = report["health_score"]
                logger.info(f"🏥 Health check: {status.upper()} (score: {score}/100)")

                # Check log directory size and clean if needed
                try:
                    from utils.log_cleaner import get_log_stats, cleanup_logs

                    log_stats = get_log_stats()
                    if log_stats.get("total_size_mb", 0) > 100:  # If logs > 100MB
                        logger.info(f"🧹 Log directory large ({log_stats['total_size_mb']:.1f} MB), running cleanup...")
                        cleanup_result = cleanup_logs(force=False)
                        if cleanup_result.get("success"):
                            logger.info(f"✅ Auto log cleanup saved {cleanup_result.get('size_saved_mb', 0):.1f} MB")
                except Exception as e:
                    logger.debug(f"Auto log cleanup failed: {e}")

                # Alert on critical issues
                if status == "critical":
                    logger.error(f"🚨 Bot health critical! Score: {score}/100")

                    # Try to notify admin
                    try:
                        from config.settings import BOT_ADMIN_USER_ID

                        admin = self.bot.get_user(BOT_ADMIN_USER_ID)
                        if admin:
                            embed = discord.Embed(
                                title="🚨 Bot Health Alert",
                                description=f"Bot health is critical (score: {score}/100)",
                                color=0xED4245,
                            )

                            # Add problem details
                            problems = []
                            cog_issues = [
                                name
                                for name, status in report["cog_status"].items()
                                if status["critical"] and not status["loaded"]
                            ]
                            if cog_issues:
                                problems.append(
                                    f"Critical cogs down: {', '.join(cog_issues)}"
                                )

                            channel_issues = [
                                cid
                                for cid, status in report["channel_access"].items()
                                if not status["accessible"]
                            ]
                            if channel_issues:
                                problems.append(
                                    f"Channels inaccessible: {len(channel_issues)}"
                                )

                            task_issues = [
                                name
                                for name, status in report["task_status"].items()
                                if status["failed"]
                            ]
                            if task_issues:
                                problems.append(
                                    f"Tasks failed: {', '.join(task_issues)}"
                                )

                            if problems:
                                embed.add_field(
                                    name="Issues",
                                    value="\n".join(problems),
                                    inline=False,
                                )

                            await admin.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Failed to send health alert: {e}")

        except Exception as e:
            logger.exception(f"Error in health check task: {e}")

    @health_check_task.before_loop
    async def before_health_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="health")
    @commands.has_permissions(administrator=True)
    async def health_command(self, ctx):
        """Show bot health status (admin only)."""
        try:
            if not health_monitor:
                await ctx.send("❌ Health monitoring not configured.")
                return

            report = health_monitor.get_health_report()

            # Create health embed
            status = report["status"]
            score = report["health_score"]

            color_map = {"healthy": 0x57F287, "warning": 0xFEE75C, "critical": 0xED4245}
            emoji_map = {"healthy": "✅", "warning": "⚠️", "critical": "🚨"}

            embed = discord.Embed(
                title=f"{emoji_map[status]} Bot Health Report",
                description=f"**Status:** {status.title()}\n**Health Score:** {score}/100",
                color=color_map[status],
            )

            # Basic stats
            uptime = report["uptime"]
            uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

            embed.add_field(
                name="📊 Statistics",
                value=f"Uptime: {uptime_str}\nGuilds: {report['guild_count']}\nCommands: {report['command_count']}\nErrors: {report['error_count']}",
                inline=True,
            )

            # Cog status
            cog_lines = []
            for name, status in report["cog_status"].items():
                emoji = "✅" if status["loaded"] else "❌"
                critical = " (Critical)" if status["critical"] else ""
                cog_lines.append(f"{emoji} {name}{critical}")

            embed.add_field(
                name="🔧 Cogs",
                value="\n".join(cog_lines) if cog_lines else "None",
                inline=True,
            )

            # Channel access
            channel_lines = []
            for cid, status in report["channel_access"].items():
                emoji = "✅" if status["accessible"] and status["can_send"] else "❌"
                name = status["name"] or "Unknown"
                channel_lines.append(f"{emoji} {name}")

            embed.add_field(
                name="📡 Channels",
                value="\n".join(channel_lines) if channel_lines else "None",
                inline=True,
            )

            # Task status
            task_lines = []
            for name, status in report["task_status"].items():
                if status["running"]:
                    emoji = "🟢"
                elif status["failed"]:
                    emoji = "🔴"
                else:
                    emoji = "🟡"
                task_lines.append(f"{emoji} {name}")

            embed.add_field(
                name="⚙️ Tasks",
                value="\n".join(task_lines) if task_lines else "None",
                inline=True,
            )

            embed.set_footer(
                text=f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            await ctx.send(embed=embed)

        except Exception:
            logger.exception("Error in health command:")
            await ctx.send("❌ Failed to generate health report.")


async def setup(bot):
    await bot.add_cog(HealthCommands(bot))
# utils/automatic_monitor.py

import discord
from discord.ext import commands
from datetime import datetime
from utils.logger import setup_logger
from utils.admin_notifier import notify_activity, notify_error

logger = setup_logger("auto_monitor")

class AutomaticMonitor:
    """Automatically monitors all commands and activities without code changes."""

    def __init__(self, bot):
        self.bot = bot
        self.setup_global_monitoring()

    def setup_global_monitoring(self):
        """Setup automatic monitoring for all bot activities."""

        # Monitor important admin commands
        self.admin_commands = {
            "block": "user_blocked",
            "unblock": "user_unblocked", 
            "win": "result_recorded",
            "loss": "result_recorded",
            "startevent": "event_started",
            "absent": "user_marked_absent",
            "present": "user_marked_present"
        }

        # Monitor data file operations
        self.important_files = [
            "events.json", "blocked_users.json", "event_results.json", 
            "ign_map.json", "absent_users.json"
        ]

    async def monitor_command_execution(self, ctx):
        """Monitor command execution automatically."""
        try:
            command_name = ctx.command.name if ctx.command else "unknown"

            # Check if it's an admin command we care about
            if command_name in self.admin_commands:
                await self._notify_admin_command(ctx, command_name)

            # Log all commands for debugging
            logger.info(f"Command executed: {command_name} by {ctx.author} in {ctx.guild}")

        except Exception as e:
            logger.error(f"Error monitoring command: {e}")

    async def monitor_command_completion(self, ctx, success: bool = True, error: Exception = None):
        """Monitor command completion automatically."""
        try:
            command_name = ctx.command.name if ctx.command else "unknown"

            if not success and error:
                # Command failed - notify admin
                await notify_error(
                    f"Command Failure: {command_name}",
                    error,
                    f"User: {ctx.author}\nGuild: {ctx.guild.name if ctx.guild else 'DM'}\nCommand: {command_name}"
                )

            elif command_name in self.admin_commands and success:
                # Important command succeeded - send activity notification
                activity_type = self.admin_commands[command_name]
                await self._send_command_success_notification(ctx, command_name, activity_type)

        except Exception as e:
            logger.error(f"Error monitoring command completion: {e}")

    async def _notify_admin_command(self, ctx, command_name: str):
        """Send notification for admin command execution."""
        try:
            # Get command arguments for context
            args = ctx.message.content.split()[1:] if ctx.message else []

            # Basic notification data
            notification_data = {
                "command": command_name,
                "executed_by": ctx.author,
                "guild": ctx.guild.name if ctx.guild else "DM",
                "timestamp": datetime.utcnow().strftime("%H:%M:%S UTC")
            }

            # Add command-specific context
            if command_name in ["block", "unblock"] and len(args) >= 1:
                notification_data["target_user"] = args[0]
                if command_name == "block" and len(args) >= 2:
                    notification_data["duration"] = f"{args[1]} days"

            elif command_name in ["win", "loss"] and len(args) >= 1:
                notification_data["team"] = args[0]
                notification_data["result"] = command_name.upper()

            elif command_name in ["absent", "present"]:
                if len(args) >= 1 and command_name == "present":
                    notification_data["target_user"] = args[0]

            # Send the activity notification
            activity_type = self.admin_commands[command_name]
            await notify_activity(activity_type, **notification_data)

        except Exception as e:
            logger.error(f"Error notifying admin command: {e}")

    async def _send_command_success_notification(self, ctx, command_name: str, activity_type: str):
        """Send success notification for completed admin commands."""
        try:
            success_data = {
                "command": command_name,
                "completed_by": ctx.author,
                "guild": ctx.guild.name if ctx.guild else "DM",
                "status": "✅ Completed successfully"
            }

            # Add command-specific success details
            if command_name == "startevent":
                success_data["event_type"] = "Weekly RoW Sign-Up"
                success_data["signups_status"] = "Unlocked"

            elif command_name in ["win", "loss"]:
                success_data["result_type"] = command_name.upper()
                success_data["recorded_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            await notify_activity(f"{activity_type}_completed", **success_data)

        except Exception as e:
            logger.error(f"Error sending success notification: {e}")

    async def monitor_file_operation(self, file_path: str, operation: str, success: bool):
        """Monitor important file operations."""
        try:
            import os
            file_name = os.path.basename(file_path)

            if file_name in self.important_files:
                if not success:
                    await notify_error(
                        f"File Operation Failed",
                        Exception(f"Failed to {operation} {file_name}"),
                        f"File: {file_name}\nOperation: {operation}"
                    )
                else:
                    # Only notify for critical file operations
                    if operation in ["save", "create"] and file_name in ["events.json", "blocked_users.json"]:
                        await notify_activity(
                            "data_sync",
                            file=file_name,
                            operation=operation,
                            status="Success"
                        )

        except Exception as e:
            logger.error(f"Error monitoring file operation: {e}")

    async def monitor_scheduler_task(self, task_name: str, success: bool, details: dict = None):
        """Monitor scheduled task execution."""
        try:
            if success:
                await notify_activity(
                    "auto_task",
                    task=task_name,
                    status="✅ Completed successfully",
                    time=datetime.utcnow().strftime("%H:%M UTC"),
                    **(details or {})
                )
            else:
                await notify_error(
                    f"Scheduled Task Failed: {task_name}",
                    Exception(f"Task {task_name} failed to complete"),
                    f"Task: {task_name}\nTime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                )

        except Exception as e:
            logger.error(f"Error monitoring scheduler task: {e}")

# Global monitor instance
auto_monitor = None

def setup_automatic_monitoring(bot):
    """Setup automatic monitoring without changing existing code."""
    global auto_monitor
    auto_monitor = AutomaticMonitor(bot)

    # Hook into bot events automatically
    @bot.event
    async def on_command(ctx):
        """Automatically monitor all command executions."""
        if auto_monitor:
            await auto_monitor.monitor_command_execution(ctx)

    @bot.event  
    async def on_command_completion(ctx):
        """Automatically monitor successful command completions."""
        if auto_monitor:
            await auto_monitor.monitor_command_completion(ctx, success=True)

    @bot.event
    async def on_command_error(ctx, error):
        """Automatically monitor command errors."""
        if auto_monitor:
            await auto_monitor.monitor_command_completion(ctx, success=False, error=error)

        # Call original error handler
        await bot.get_cog('ErrorHandler').on_command_error(ctx, error) if bot.get_cog('ErrorHandler') else None

    logger.info("✅ Automatic command monitoring enabled")

# Convenience functions for manual monitoring
async def monitor_file_save(file_path: str, success: bool):
    """Monitor file save operations."""
    if auto_monitor:
        await auto_monitor.monitor_file_operation(file_path, "save", success)

async def monitor_scheduled_task(task_name: str, success: bool, **details):
    """Monitor scheduled task execution."""
    if auto_monitor:
        await auto_monitor.monitor_scheduler_task(task_name, success, details)

async def monitor_button_interaction(interaction: discord.Interaction, action: str, success: bool):
    """Monitor button interactions."""
    try:
        if auto_monitor and action in ["join_team", "leave_team"]:
            if success:
                await notify_activity(
                    "button_interaction",
                    action=action,
                    user=interaction.user,
                    guild=interaction.guild.name if interaction.guild else "DM"
                )
            else:
                await notify_error(
                    "Button Interaction Failed",
                    Exception(f"Button action {action} failed"),
                    f"User: {interaction.user}\nAction: {action}"
                )
    except Exception as e:
        logger.error(f"Error monitoring button interaction: {e}")
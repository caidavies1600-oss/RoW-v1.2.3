"""
Automated task scheduler for RoW events.

This module manages recurring tasks:
- Tuesday signup posts (10:00 UTC, bi-weekly)
- Thursday team lock (23:59 UTC, bi-weekly)
- Sunday summaries (23:30 UTC, bi-weekly)
- Smart event reminders (continuous)

All tasks run on even weeks only to match bi-weekly event schedule.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from discord.ext import tasks

from config.constants import ALERT_CHANNEL_ID, DEFAULT_TIMES, FILES, TEAM_DISPLAY
from config.settings import ROW_NOTIFICATION_ROLE_ID
from utils.data_manager import DataManager
from utils.helpers import Helpers

logger = logging.getLogger("scheduler")


def start_scheduler(bot):
    """
    Initialize and start all scheduled tasks.

    Args:
        bot: Discord bot instance

    Tasks started:
    - Event signup posting
    - Weekly summary
    - Thursday teams lock
    - Smart event reminders
    """

    @bot.event
    async def on_ready():
        logger.info("✅ Scheduler is active")
        post_event_signup.start(bot)
        post_weekly_summary.start(bot)
        thursday_teams_and_lock.start(bot)  # NEW: Thursday task
        smart_event_reminders.start(bot)  # NEW: Smart notification reminders


# Tuesday at 10:00 UTC - Auto-post weekly signups (bi-weekly)
@tasks.loop(hours=24)
async def post_event_signup(bot):
    """
    Auto-post weekly signup message every other Tuesday.

    Posts at 10:00 UTC on even weeks only.
    Creates new event and resets team rosters.
    """
    now = datetime.utcnow()
    # Only run on Tuesdays at 10:00 UTC
    if now.weekday() == 1 and now.hour == 10 and now.minute < 5:
        # Only run on even weeks to match the bi-weekly event schedule
        week_number = now.isocalendar()[1]
        if week_number % 2 != 0:  # Skip odd weeks, same as summary
            logger.info(f"⏭️ Skipping Tuesday signup post (odd week {week_number})")
            return

        try:
            ctx = await Helpers.create_fake_context(bot)
            manager = bot.get_cog("EventManager")

            if not manager:
                logger.warning("⚠️ EventManager cog not loaded.")
                return

            await manager.start_event(ctx)
            logger.info(
                f"✅ Auto-posted weekly signup event (Tuesday 10:00 UTC, week {week_number})"
            )
        except Exception as e:
            logger.error("❌ Failed to auto-post event\n" + str(e))


# Thursday at 23:59 UTC - Show final teams and lock signups (bi-weekly)
@tasks.loop(minutes=1)
async def thursday_teams_and_lock(bot):
    """
    Show final teams and lock signups on Thursday nights.

    Runs at 23:59 UTC on even weeks only.
    Posts final roster and prevents further changes.
    """
    now = datetime.utcnow()
    # Only run on Thursdays at 23:59 UTC (within 1-minute window)
    if now.weekday() == 3 and now.hour == 23 and now.minute == 59:
        # Only run on even weeks to match the bi-weekly event schedule
        week_number = now.isocalendar()[1]
        if week_number % 2 != 0:  # Skip odd weeks, same as summary
            logger.info(f"⏭️ Skipping Thursday lock task (odd week {week_number})")
            return

        try:
            manager = bot.get_cog("EventManager")
            if not manager:
                logger.warning("⚠️ EventManager cog not loaded.")
                return

            await manager.auto_show_teams_and_lock()
            logger.info(
                f"✅ Auto-posted final teams and locked signups (Thursday 23:59 UTC, week {week_number})"
            )
        except Exception:
            logger.exception("❌ Failed to auto-post teams and lock signups")


# Every other Sunday at 23:30 UTC - Weekly summary
@tasks.loop(hours=24)
async def post_weekly_summary(bot):
    """
    Post bi-weekly RoW event summary.

    Posts Sunday at 23:30 UTC on even weeks.
    Includes:
    - Win/loss statistics
    - Team-specific results
    - Blocked user status
    - Signup summary
    - Absence records
    """
    now = datetime.utcnow()
    # Only run on Sundays at 23:30 UTC, every other week
    if now.weekday() == 6 and now.hour == 23 and 30 <= now.minute <= 35:
        # Simple bi-weekly check: only run on even weeks of the year
        week_number = now.isocalendar()[1]
        if week_number % 2 != 0:  # Skip odd weeks
            return

        try:
            # Initialize DataManager once at the beginning
            data_manager = DataManager()

            # Get results from the Results cog
            results_cog = bot.get_cog("Results")
            if results_cog:
                results = results_cog.results
            else:
                # Fallback to loading directly using DataManager and FILES constant
                results = data_manager.load_json(
                    FILES["RESULTS"],
                    {"total_wins": 0, "total_losses": 0, "history": []},
                )

            manager = bot.get_cog("EventManager")
            if not manager:
                logger.warning("⚠️ EventManager cog not loaded.")
                return

            alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
            if not alert_channel:
                logger.error(
                    "⚠️ ALERT_CHANNEL_ID does not match any channel in this guild."
                )
                return

            summary = []

            # 📈 Total win/loss stats
            total_wins = results.get("total_wins", 0)
            total_losses = results.get("total_losses", 0)
            total_games = total_wins + total_losses
            win_rate = (
                round((total_wins / total_games) * 100, 1) if total_games else 0.0
            )
            summary.append(
                f"📈 **Total Results**: {total_wins}W / {total_losses}L ({win_rate}% win rate)\n"
            )

            # 📊 Weekly team-specific stats
            one_week_ago = datetime.utcnow() - timedelta(days=7)
            team_weekly = {team: {"W": 0, "L": 0} for team in TEAM_DISPLAY}

            for result in results.get("history", []):
                try:
                    event_time = datetime.fromisoformat(result["timestamp"])
                    if event_time < one_week_ago:
                        continue

                    for team, outcome in result["teams"].items():
                        if outcome == "win":
                            team_weekly[team]["W"] += 1
                        elif outcome == "loss":
                            team_weekly[team]["L"] += 1
                except Exception:
                    continue

            summary.append("📊 **This Week's Team Results:**")
            for team, stats in team_weekly.items():
                display = TEAM_DISPLAY.get(team, team)
                summary.append(f"• {display}: {stats['W']}W / {stats['L']}L")
            summary.append("")

            # ⛔ Blocked users - get from manager but could also load via DataManager if needed
            blocked_users_data = (
                data_manager.load_json(FILES["BLOCKED"], {})
                if not hasattr(manager, "blocked_users")
                else manager.blocked_users
            )

            blocked = []
            for user_id, info in blocked_users_data.items():
                expiry = info.get("blocked_at")
                duration = info.get("ban_duration_days", 0)
                blocked_by = info.get("blocked_by", "Unknown")
                if expiry:
                    remaining = Helpers.days_until_expiry(expiry, duration)
                    blocked.append(
                        f"<@{user_id}> — {remaining} days left (blocked by {blocked_by})"
                    )

            if blocked:
                summary.append("⛔ **Blocked Users:**")
                summary += blocked
                summary.append("")

            # 📥 Signup summary - get from manager but could also load via DataManager if needed
            events_data = (
                data_manager.load_json(
                    FILES["EVENTS"], {"main_team": [], "team_2": [], "team_3": []}
                )
                if not hasattr(manager, "events")
                else manager.events
            )

            summary.append("📥 **Final Signup Summary:**")
            for team_key in TEAM_DISPLAY:
                members = events_data.get(team_key, [])
                team_name = TEAM_DISPLAY.get(team_key, team_key)
                summary.append(f"• {team_name}: {len(members)} signed up")
            summary.append("")

            # 🔁 Absence summary
            absent_data = data_manager.load_json(FILES["ABSENT"], {})
            if absent_data:
                summary.append("🔁 **Absent Users:**")
                for user_id, info in absent_data.items():
                    marked_by = info.get("marked_by", "Unknown")
                    summary.append(f"<@{user_id}> (marked by {marked_by})")
            else:
                summary.append("🔁 **Absent Users:** None")

            await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>\n📊 **Bi-Weekly RoW Summary**\n\n"
                + "\n".join(summary)
            )
            logger.info("✅ Posted bi-weekly RoW summary")
        except Exception:
            logger.exception("❌ Failed to post weekly summary")


@post_event_signup.before_loop
async def before_post_event_signup():
    """Ensure bot is ready before starting signup task."""
    # Wait for bot to be ready and align to the hour
    await asyncio.sleep(60)  # Small delay to ensure bot is fully ready


@post_weekly_summary.before_loop
async def before_post_weekly_summary():
    """Ensure bot is ready before starting summary task."""
    # Wait for bot to be ready and align to the hour
    await asyncio.sleep(60)  # Small delay to ensure bot is fully ready


@thursday_teams_and_lock.before_loop
async def before_thursday_teams_and_lock():
    """Ensure bot is ready before starting lock task."""
    # Wait for bot to be ready
    await asyncio.sleep(30)  # Small delay to ensure bot is fully ready


# Every minute - Check for smart event reminders
@tasks.loop(minutes=1)
async def smart_event_reminders(bot):
    """
    Send smart notifications for upcoming events.

    Features:
    - Configurable reminder intervals (60, 15, 5 minutes)
    - Team-specific timing
    - User preference based delivery
    - Fallback time handling
    """
    try:
        now = datetime.utcnow()

        # Get actual event times from EventManager
        event_manager = bot.get_cog("EventManager")
        if not event_manager:
            return

        # Parse the actual event times from the loaded data
        upcoming = {}
        for team_key in ["main_team", "team_2", "team_3"]:
            team_time_str = event_manager.event_times.get(
                team_key, DEFAULT_TIMES.get(team_key, "17:30 UTC Tuesday")
            )

            # Parse "17:30 UTC Tuesday" format
            try:
                parts = team_time_str.split()
                time_part = parts[0]  # "17:30"
                day_part = parts[2]  # "Tuesday"

                hour, minute = map(int, time_part.split(":"))

                # Map day names to weekday numbers (Monday=0, Sunday=6)
                day_map = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                target_day = day_map.get(day_part.lower(), 1)  # Default to Tuesday

                # Calculate next occurrence of this day at this time
                days_ahead = target_day - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7

                from datetime import time

                event_datetime = datetime.combine(
                    now.date(), time(hour, minute)
                ) + timedelta(days=days_ahead)
                upcoming[team_key] = event_datetime

            except Exception as e:
                logger.error(
                    f"Failed to parse event time for {team_key}: {team_time_str}, error: {e}"
                )
                # Fallback to Tuesday 17:30 UTC
                from datetime import time

                days_ahead = 1 - now.weekday()  # Tuesday
                if days_ahead <= 0:
                    days_ahead += 7
                upcoming[team_key] = datetime.combine(
                    now.date(), time(17, 30)
                ) + timedelta(days=days_ahead)

        # Get smart notifications service
        smart_notifications_cog = bot.get_cog("NotificationsCog")
        if not smart_notifications_cog:
            return

        smart_notifications = smart_notifications_cog.smart_notifications

        # Check each team for upcoming events
        for team_key, event_time in upcoming.items():
            delta = event_time - now
            minutes_until = delta.total_seconds() / 60

            # Send reminders at different intervals (60 minutes, 15 minutes, 5 minutes)
            reminder_times = [60, 15, 5]

            for reminder_minutes in reminder_times:
                # Check if we're within 1 minute of the reminder time
                if abs(minutes_until - reminder_minutes) <= 0.5:
                    logger.info(
                        f"Sending {reminder_minutes}-minute reminder for {team_key}"
                    )

                    # Get team members
                    event_manager = bot.get_cog("EventManager")
                    if not event_manager:
                        continue

                    team_members = event_manager.events.get(team_key, [])
                    if not team_members:
                        continue

                    # Send smart notifications to each team member
                    team_display = TEAM_DISPLAY.get(
                        team_key, team_key.replace("_", " ").title()
                    )
                    team_time = event_manager.event_times.get(
                        team_key, DEFAULT_TIMES.get(team_key, "TBD")
                    )

                    for member_id in team_members:
                        try:
                            content = {
                                "message": f"Event starting in {reminder_minutes} minutes!",
                                "details": f"**Team:** {team_display}\n**Time:** {team_time}\n**Starting in:** {reminder_minutes} minutes",
                            }

                            await smart_notifications.send_smart_notification(
                                str(member_id), "event_reminders", content
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to send smart reminder to {member_id}: {e}"
                            )

    except Exception as e:
        logger.exception(f"Error in smart_event_reminders: {e}")


@smart_event_reminders.before_loop
async def before_smart_event_reminders():
    """Ensure bot is ready before starting reminders."""
    # Wait for bot to be ready
    await asyncio.sleep(45)  # Small delay to ensure bot is fully ready

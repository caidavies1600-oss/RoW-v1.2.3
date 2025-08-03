import asyncio
import logging
from datetime import datetime, timedelta
from discord.ext import tasks

from utils.helpers import Helpers
from config.constants import ALERT_CHANNEL_ID, FILES, TEAM_DISPLAY, EMOJIS, COLORS
from config.settings import ROW_NOTIFICATION_ROLE_ID

from cogs.events.results import load_results
from cogs.admin.attendance import load_absent_data

logger = logging.getLogger("scheduler")

def start_scheduler(bot):
    @bot.event
    async def on_ready():
        logger.info("✅ Scheduler is active")
        post_event_signup.start(bot)
        post_weekly_summary.start(bot)
        thursday_teams_and_lock.start(bot)  # NEW: Thursday task

# Tuesday at 10:00 UTC - Auto-post weekly signups (bi-weekly)
@tasks.loop(hours=24)
async def post_event_signup(bot):
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
            logger.info(f"✅ Auto-posted weekly signup event (Tuesday 10:00 UTC, week {week_number})")
        except Exception as e:
            logger.error("❌ Failed to auto-post event\n" + str(e))

# Thursday at 23:59 UTC - Show final teams and lock signups (bi-weekly)
@tasks.loop(minutes=1)
async def thursday_teams_and_lock(bot):
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
            logger.info(f"✅ Auto-posted final teams and locked signups (Thursday 23:59 UTC, week {week_number})")
        except Exception as e:
            logger.exception("❌ Failed to auto-post teams and lock signups")

# Every other Sunday at 23:30 UTC - Weekly summary
@tasks.loop(hours=24)
async def post_weekly_summary(bot):
    now = datetime.utcnow()
    # Only run on Sundays at 23:30 UTC, every other week
    if now.weekday() == 6 and now.hour == 23 and 30 <= now.minute <= 35:
        # Simple bi-weekly check: only run on even weeks of the year
        week_number = now.isocalendar()[1]
        if week_number % 2 != 0:  # Skip odd weeks
            return

        try:
            results = load_results()
            manager = bot.get_cog("EventManager")
            if not manager:
                logger.warning("⚠️ EventManager cog not loaded.")
                return

            alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
            if not alert_channel:
                logger.error("⚠️ ALERT_CHANNEL_ID does not match any channel in this guild.")
                return

            summary = []

            # 📈 Total win/loss stats
            total_wins = results.get("total_wins", 0)
            total_losses = results.get("total_losses", 0)
            total_games = total_wins + total_losses
            win_rate = round((total_wins / total_games) * 100, 1) if total_games else 0.0
            summary.append(f"📈 **Total Results**: {total_wins}W / {total_losses}L ({win_rate}% win rate)\n")

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

            # ⛔ Blocked users
            blocked = []
            for user_id, info in manager.blocked_users.items():
                expiry = info.get("blocked_at")
                duration = info.get("ban_duration_days", 0)
                blocked_by = info.get("blocked_by", "Unknown")
                if expiry:
                    remaining = Helpers.days_until_expiry(expiry, duration)
                    blocked.append(f"<@{user_id}> — {remaining} days left (blocked by {blocked_by})")

            if blocked:
                summary.append("⛔ **Blocked Users:**")
                summary += blocked
                summary.append("")

            # 📥 Signup summary
            summary.append("📥 **Final Signup Summary:**")
            for team_key in TEAM_DISPLAY:
                members = manager.events.get(team_key, [])
                team_name = TEAM_DISPLAY.get(team_key, team_key)
                summary.append(f"• {team_name}: {len(members)} signed up")
            summary.append("")

            # 🔁 Absence summary
            absent_data = load_absent_data()
            if absent_data:
                summary.append("🔁 **Absent Users:**")
                for user_id, info in absent_data.items():
                    marked_by = info.get("marked_by", "Unknown")
                    summary.append(f"<@{user_id}> (marked by {marked_by})")
            else:
                summary.append("🔁 **Absent Users:** None")

            await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>\n📊 **Bi-Weekly RoW Summary**\n\n" + "\n".join(summary)
            )
            logger.info("✅ Posted bi-weekly RoW summary")
        except Exception as e:
            logger.exception("❌ Failed to post weekly summary")

@post_event_signup.before_loop
async def before_post_event_signup():
    # Wait for bot to be ready and align to the hour
    await asyncio.sleep(60)  # Small delay to ensure bot is fully ready

@post_weekly_summary.before_loop
async def before_post_weekly_summary():
    # Wait for bot to be ready and align to the hour
    await asyncio.sleep(60)  # Small delay to ensure bot is fully ready

@thursday_teams_and_lock.before_loop
async def before_thursday_teams_and_lock():
    # Wait for bot to be ready
    await asyncio.sleep(30)  # Small delay to ensure bot is fully ready
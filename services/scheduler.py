import asyncio
import logging
from datetime import datetime, timedelta
from discord.ext import tasks

from utils.helpers import Helpers
from utils.data_manager import DataManager
from config.constants import ALERT_CHANNEL_ID, FILES, TEAM_DISPLAY, EMOJIS, COLORS
from config.settings import ROW_NOTIFICATION_ROLE_ID

logger = logging.getLogger("scheduler")

def start_scheduler(bot):
    @bot.event
    async def on_ready():
        logger.info("✅ Scheduler is active (PRODUCTION MODE)")
        post_event_signup.start(bot)
        post_weekly_summary.start(bot)

# Every 2 weeks on Tuesday at 14:00 UTC
@tasks.loop(minutes=1)  # Check every minute for precise timing
async def post_event_signup(bot):
    now = datetime.utcnow()
    
    # Check if it's Tuesday (weekday 1) at 14:00 UTC
    if now.weekday() == 1 and now.hour == 14 and now.minute == 0:
        
        # Calculate weeks since August 5, 2025 (first event Tuesday)
        start_date = datetime(2025, 8, 5, 14, 0, 0)  # First Tuesday at 14:00 UTC
        weeks_since_start = (now - start_date).days // 7
        
        # Only run every 2 weeks (even week numbers)
        if weeks_since_start >= 0 and weeks_since_start % 2 == 0:
            try:
                ctx = await Helpers.create_fake_context(bot)
                manager = bot.get_cog("EventManager")

                if not manager:
                    logger.warning("⚠️ EventManager cog not loaded.")
                    return

                await manager.start_event(ctx)
                logger.info(f"✅ Auto-posted bi-weekly signup event (Week {weeks_since_start // 2 + 1})")
            except Exception as e:
                logger.error(f"❌ Failed to auto-post event: {e}")

# Every Sunday at 22:00 UTC (after events end)
@tasks.loop(minutes=1)  # Check every minute for precise timing
async def post_weekly_summary(bot):
    now = datetime.utcnow()
    
    # Check if it's Sunday (weekday 6) at 22:00 UTC
    if now.weekday() == 6 and now.hour == 22 and now.minute == 0:
        try:
            ctx = await Helpers.create_fake_context(bot)
            data_manager = DataManager()
            
            # Load data using the existing data manager
            results = data_manager.load_json(FILES["RESULTS"], {"total_wins": 0, "total_losses": 0, "history": []})
            absent_data = data_manager.load_json(FILES["ABSENT"], {})
            
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

            # 📊 Weekly team-specific stats (last 2 weeks)
            two_weeks_ago = datetime.utcnow() - timedelta(days=14)
            team_weekly = {team: {"W": 0, "L": 0} for team in TEAM_DISPLAY}

            for result in results.get("history", []):
                try:
                    event_time = datetime.fromisoformat(result["timestamp"])
                    if event_time < two_weeks_ago:
                        continue

                    for team, outcome in result["teams"].items():
                        if outcome == "win":
                            team_weekly[team]["W"] += 1
                        elif outcome == "loss":
                            team_weekly[team]["L"] += 1
                except Exception:
                    continue

            summary.append("📊 **This Period's Team Results:**")
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

            # 📥 Signup summary for current period
            summary.append("📥 **Current Signup Summary:**")
            for team_key in TEAM_DISPLAY:
                members = manager.events.get(team_key, [])
                team_name = TEAM_DISPLAY.get(team_key, team_key)
                summary.append(f"• {team_name}: {len(members)} signed up")
            summary.append("")

            # 🔁 Absence summary
            if absent_data:
                summary.append("🔁 **Absent Users:**")
                for user_id, info in absent_data.items():
                    marked_by = info.get("marked_by", "Unknown")
                    summary.append(f"<@{user_id}> (marked by {marked_by})")
            else:
                summary.append("🔁 **Absent Users:** None")

            # Calculate next event date
            next_tuesday = now + timedelta(days=(1 - now.weekday()) % 7)
            if next_tuesday.date() == now.date():  # If today is Tuesday
                next_tuesday += timedelta(days=7)
            
            # Check if it's an event week (bi-weekly)
            start_date = datetime(2025, 8, 5, 14, 0, 0)
            weeks_until_next = (next_tuesday - start_date).days // 7
            
            if weeks_until_next % 2 == 0:
                summary.append(f"\n🗓️ **Next Event**: {next_tuesday.strftime('%A, %B %d')} at 14:00 UTC")
            else:
                next_event_tuesday = next_tuesday + timedelta(days=7)
                summary.append(f"\n🗓️ **Next Event**: {next_event_tuesday.strftime('%A, %B %d')} at 14:00 UTC (Following week)")

            await alert_channel.send(
                content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>\n📊 **Weekly RoW Summary**\n\n" + "\n".join(summary)
            )
            logger.info("✅ Posted weekly RoW summary")
        except Exception as e:
            logger.exception("❌ Failed to post weekly summary")

# Load results function (preserved from original)
def load_results():
    """Load result data from file."""
    data_manager = DataManager()
    return data_manager.load_json(FILES["RESULTS"], {"total_wins": 0, "total_losses": 0, "history": []})

# Load absent data function (preserved from original)  
def load_absent_data():
    """Load absent data from file."""
    data_manager = DataManager()
    return data_manager.load_json(FILES["ABSENT"], {})

# Stop scheduler function (if needed for shutdown)
def stop_scheduler():
    """Stop all scheduled tasks."""
    try:
        post_event_signup.cancel()
        post_weekly_summary.cancel()
        logger.info("✅ Scheduler tasks stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping scheduler: {e}")
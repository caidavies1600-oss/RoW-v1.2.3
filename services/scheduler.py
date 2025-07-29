import asyncio
import logging
from datetime import datetime, timedelta
from discord.ext import tasks

from utils.helpers import Helpers
from config.constants import ALERT_CHANNEL_ID, FILES, TEAM_DISPLAY, EMOJIS, COLORS
from config.settings import ROW_NOTIFICATION_ROLE_ID
from utils.data_manager import DataManager

logger = logging.getLogger(“scheduler”)

def load_results():
“”“Load result data from file.”””
data_manager = DataManager()
return data_manager.load_json(FILES[“RESULTS”], {“total_wins”: 0, “total_losses”: 0, “history”: []})

def load_absent_data():
“”“Load absent user data from file.”””
data_manager = DataManager()
return data_manager.load_json(FILES[“ABSENT”], {})

def start_scheduler(bot):
@bot.event
async def on_ready():
logger.info(“✅ Scheduler is active (TEST MODE)”)
post_event_signup.start(bot)
post_weekly_summary.start(bot)

# 🧪 Every 2 mins starting at 10:52 UTC

@tasks.loop(minutes=2)
async def post_event_signup(bot):
now = datetime.utcnow()
if now.hour == 10 and now.minute % 2 == 0 and now.minute >= 52:
try:
ctx = await Helpers.create_fake_context(bot)
manager = bot.get_cog(“EventManager”)

```
        if not manager:
            logger.warning("⚠️ EventManager cog not loaded.")
            return

        await manager.start_event(ctx)
        logger.info("✅ Auto-posted weekly signup event (TEST)")
    except Exception as e:
        logger.error("❌ Failed to auto-post event\n" + str(e))
```

# 🧪 Every 3 mins starting at 10:52 UTC

@tasks.loop(minutes=3)
async def post_weekly_summary(bot):
now = datetime.utcnow()
if now.hour == 10 and now.minute % 3 == 0 and now.minute >= 52:
try:
ctx = await Helpers.create_fake_context(bot)
results = load_results()
manager = bot.get_cog(“EventManager”)
if not manager:
logger.warning(“⚠️ EventManager cog not loaded.”)
return

```
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
        summary.append("📥 **Signup Summary:**")
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
            content=f"<@&{ROW_NOTIFICATION_ROLE_ID}>\n📊 **Weekly RoW Summary (Test)**\n\n" + "\n".join(summary)
        )
        logger.info("✅ Posted weekly RoW summary (TEST)")
    except Exception as e:
        logger.exception("❌ Failed to post weekly summary (TEST)")
```
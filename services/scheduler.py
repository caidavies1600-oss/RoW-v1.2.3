import asyncio
import logging
from datetime import datetime, timedelta
from discord.ext import tasks

from utils.helpers import Helpers
from config.constants import ALERT_CHANNEL_IDS, FILES, TEAM_DISPLAY, EMOJIS, COLORS
from config.settings import ROW_NOTIFICATION_ROLE_ID
from utils.data_manager import DataManager

logger = logging.getLogger("scheduler")

def start_scheduler(bot):
    @bot.event
    async def on_ready():
        logger.info("✅ Scheduler is active (TEST MODE)")
        post_event_signup.start(bot)
        post_weekly_summary.start(bot)

async def post_to_all_alert_channels(bot, content=None, embed=None):
    """Helper function to post to all alert channels."""
    posted_channels = []
    failed_channels = []
    
    for channel_id in ALERT_CHANNEL_IDS:
        try:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(content=content, embed=embed)
                posted_channels.append(f"{channel.guild.name}#{channel.name}")
                logger.info(f"✅ Posted summary to {channel.guild.name}#{channel.name}")
            else:
                failed_channels.append(f"Channel ID {channel_id}")
                logger.warning(f"⚠️ Channel {channel_id} not found")
        except Exception as e:
            failed_channels.append(f"Channel ID {channel_id}")
            logger.error(f"❌ Failed to post summary to channel {channel_id}: {e}")
    
    return posted_channels, failed_channels

def load_results():
    """Load results data using DataManager."""
    data_manager = DataManager()
    return data_manager.load_json(FILES["RESULTS"], {
        "total_wins": 0,
        "total_losses": 0,
        "history": []
    })

def load_absent_data():
    """Load absent users data using DataManager."""
    data_manager = DataManager()
    return data_manager.load_json(FILES["ABSENT"], {})

@tasks.loop(minutes=2)
async def post_event_signup(bot):
    now = datetime.utcnow()
    if now.hour == 10 and now.minute % 2 == 0 and now.minute >= 52:
        try:
            ctx = await Helpers.create_fake_context(bot)
            manager = bot.get_cog("EventManager")

            if not manager:
                logger.warning("⚠️ EventManager cog not loaded.")
                return

            await manager.auto_post_signup(ctx)
            logger.info("✅ Auto-posted weekly signup event (TEST)")
        except Exception as e:
            logger.error("❌ Failed to auto-post event\n" + str(e))

@tasks.loop(minutes=3)
async def post_weekly_summary(bot):
    now = datetime.utcnow()
    if now.hour == 10 and now.minute % 3 == 0 and now.minute >= 52:
        try:
            results = load_results()
            absent_data = load_absent_data()
            
            manager = bot.get_cog("EventManager")
            if not manager:
                logger.warning("⚠️ EventManager cog not loaded.")
                return

            summary = []

            total_wins = results.get("total_wins", 0)
            total_losses = results.get("total_losses", 0)
            total_games = total_wins + total_losses
            win_rate = round((total_wins / total_games) * 100, 1) if total_games else 0.0
            summary.append(f"📈 **Total Results**: {total_wins}W / {total_losses}L ({win_rate}% win rate)\n")

            one_week_ago = datetime.utcnow() - timedelta(days=7)
            team_weekly = {team: {"W": 0, "L": 0} for team in TEAM_DISPLAY}

            for result in results.get("history", []):
                try:
                    event_time = datetime.fromisoformat(result["timestamp"])
                    if event_time < one_week_ago:
                        continue

                    team = result.get("team")
                    outcome = result.get("result")
                    if team in team_weekly:
                        if outcome == "win":
                            team_weekly[team]["W"] += 1
                        elif outcome == "loss":
                            team_weekly[team]["L"] += 1
                except Exception as e:
                    logger.warning(f"Skipping invalid result entry: {e}")
                    continue

            summary.append("📊 **This Week's Team Results:**")
            for team, stats in team_weekly.items():
                display = TEAM_DISPLAY.get(team, team)
                summary.append(f"• {display}: {stats['W']}W / {stats['L']}L")
            summary.append("")

            blocked = []
            for user_id, info in manager.blocked_users.items():
                try:
                    blocked_at = info.get("blocked_at")
                    duration = info.get("ban_duration_days", 0)
                    blocked_by = info.get("blocked_by", "Unknown")
                    
                    if blocked_at:
                        expiry = datetime.fromisoformat(blocked_at) + timedelta(days=duration)
                        remaining = expiry - datetime.utcnow()
                        if remaining.total_seconds() > 0:
                            days = remaining.days
                            blocked.append(f"<@{user_id}> — {days} days left (blocked by {blocked_by})")
                except Exception as e:
                    logger.warning(f"Error processing blocked user {user_id}: {e}")

            if blocked:
                summary.append("⛔ **Blocked Users:**")
                summary += blocked
                summary.append("")

            summary.append("📥 **Signup Summary:**")
            for team_key in TEAM_DISPLAY:
                members = manager.events.get(team_key, [])
                team_name = TEAM_DISPLAY.get(team_key, team_key)
                summary.append(f"• {team_name}: {len(members)} signed up")
            summary.append("")

            if absent_data:
                summary.append("🔁 **Absent Users:**")
                for user_id, info in absent_data.items():
                    marked_by = info.get("marked_by", "Unknown")
                    summary.append(f"<@{user_id}> (marked by {marked_by})")
            else:
                summary.append("🔁 **Absent Users:** None")

            content = f"<@&{ROW_NOTIFICATION_ROLE_ID}>\n📊 **Weekly RoW Summary (Test)**\n\n" + "\n".join(summary)
            posted, failed = await post_to_all_alert_channels(bot, content=content)
            
            if posted:
                logger.info(f"✅ Posted weekly RoW summary to: {', '.join(posted)}")
            if failed:
                logger.warning(f"⚠️ Failed to post summary to: {', '.join(failed)}")
                
        except Exception as e:
            logger.exception("❌ Failed to post weekly summary (TEST)")
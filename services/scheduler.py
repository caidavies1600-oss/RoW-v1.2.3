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
    """Helper function to post to all alert channels with error handling."""
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
                failed_channels.append(f"Channel ID {channel_id} (not found)")
                logger.warning(f"⚠️ Channel {channel_id} not found")
        except Exception as e:
            failed_channels.append(f"Channel ID {channel_id} (error: {str(e)})")
            logger.error(f"❌ Failed to post summary to channel {channel_id}: {e}")
    
    return posted_channels, failed_channels

def load_results():
    """Load results data using DataManager with error handling."""
    try:
        data_manager = DataManager()
        return data_manager.load_json(FILES["RESULTS"], {
            "total_wins": 0,
            "total_losses": 0,
            "history": []
        })
    except Exception as e:
        logger.error(f"❌ Failed to load results data: {e}")
        return {"total_wins": 0, "total_losses": 0, "history": []}

def load_absent_data():
    """Load absent users data using DataManager with error handling."""
    try:
        data_manager = DataManager()
        return data_manager.load_json(FILES["ABSENT"], {})
    except Exception as e:
        logger.error(f"❌ Failed to load absent data: {e}")
        return {}

def safe_get_cog(bot, cog_name):
    """Safely get a cog with error handling."""
    try:
        cog = bot.get_cog(cog_name)
        if cog is None:
            logger.warning(f"⚠️ {cog_name} cog not loaded")
        return cog
    except Exception as e:
        logger.error(f"❌ Error getting {cog_name} cog: {e}")
        return None

def safe_calculate_time_remaining(blocked_at, duration_days):
    """Safely calculate time remaining with error handling."""
    try:
        if not blocked_at:
            return 0
        
        blocked_time = datetime.fromisoformat(blocked_at)
        expiry = blocked_time + timedelta(days=duration_days)
        remaining = expiry - datetime.utcnow()
        return max(remaining.days, 0)
    except Exception as e:
        logger.warning(f"Error calculating time remaining: {e}")
        return 0

@tasks.loop(minutes=2)
async def post_event_signup(bot):
    """Auto-post event signup with comprehensive error handling."""
    now = datetime.utcnow()
    if now.hour == 10 and now.minute % 2 == 0 and now.minute >= 52:
        try:
            logger.info("🔄 Attempting to auto-post event signup...")
            
            # Check if EventManager cog is loaded
            manager = safe_get_cog(bot, "EventManager")
            if not manager:
                logger.error("❌ EventManager cog not loaded - cannot auto-post event")
                return

            # Try to create fake context
            try:
                ctx = await Helpers.create_fake_context(bot)
            except Exception as e:
                logger.error(f"❌ Failed to create fake context: {e}")
                return

            # Check if manager has required methods
            if not hasattr(manager, 'auto_post_signup'):
                logger.error("❌ EventManager missing auto_post_signup method")
                return

            # Attempt to auto-post
            await manager.auto_post_signup(ctx)
            logger.info("✅ Auto-posted weekly signup event (TEST)")
            
        except Exception as e:
            logger.exception(f"❌ Critical error in auto-post event: {e}")

@tasks.loop(minutes=3)
async def post_weekly_summary(bot):
    """Post weekly summary with comprehensive error handling."""
    now = datetime.utcnow()
    if now.hour == 10 and now.minute % 3 == 0 and now.minute >= 52:
        try:
            logger.info("🔄 Attempting to post weekly summary...")
            
            # Load data with error handling
            results = load_results()
            absent_data = load_absent_data()
            
            # Check if EventManager cog is loaded
            manager = safe_get_cog(bot, "EventManager")
            if not manager:
                logger.error("❌ EventManager cog not loaded - cannot access event data")
                return

            # Check if manager has required attributes
            if not hasattr(manager, 'events') or not hasattr(manager, 'blocked_users'):
                logger.error("❌ EventManager missing required attributes")
                return

            summary = []

            # 📈 Total win/loss stats with error handling
            try:
                total_wins = results.get("total_wins", 0)
                total_losses = results.get("total_losses", 0)
                total_games = total_wins + total_losses
                win_rate = round((total_wins / total_games) * 100, 1) if total_games else 0.0
                summary.append(f"📈 **Total Results**: {total_wins}W / {total_losses}L ({win_rate}% win rate)\n")
            except Exception as e:
                logger.warning(f"Error calculating win/loss stats: {e}")
                summary.append("📈 **Total Results**: Error loading stats\n")

            # 📊 Weekly team-specific stats with error handling
            try:
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
                        logger.warning(f"Error processing result entry: {e}")
                        continue

                summary.append("📊 **This Week's Team Results:**")
                for team, stats in team_weekly.items():
                    display = TEAM_DISPLAY.get(team, team)
                    summary.append(f"• {display}: {stats['W']}W / {stats['L']}L")
                summary.append("")
            except Exception as e:
                logger.warning(f"Error calculating weekly stats: {e}")
                summary.append("📊 **This Week's Team Results:** Error loading weekly data\n")

            # ⛔ Blocked users with error handling
            try:
                blocked = []
                blocked_users = getattr(manager, 'blocked_users', {})
                
                for user_id, info in blocked_users.items():
                    try:
                        blocked_at = info.get("blocked_at")
                        duration = info.get("ban_duration_days", 0)
                        blocked_by = info.get("blocked_by", "Unknown")
                        
                        if blocked_at:
                            days_remaining = safe_calculate_time_remaining(blocked_at, duration)
                            if days_remaining > 0:
                                blocked.append(f"<@{user_id}> — {days_remaining} days left (blocked by {blocked_by})")
                    except Exception as e:
                        logger.warning(f"Error processing blocked user {user_id}: {e}")
                        blocked.append(f"<@{user_id}> — Error loading data")

                if blocked:
                    summary.append("⛔ **Blocked Users:**")
                    summary += blocked
                    summary.append("")
            except Exception as e:
                logger.warning(f"Error loading blocked users: {e}")
                summary.append("⛔ **Blocked Users:** Error loading data\n")

            # 📥 Signup summary with error handling
            try:
                summary.append("📥 **Signup Summary:**")
                events = getattr(manager, 'events', {})
                
                for team_key in TEAM_DISPLAY:
                    members = events.get(team_key, [])
                    team_name = TEAM_DISPLAY.get(team_key, team_key)
                    summary.append(f"• {team_name}: {len(members)} signed up")
                summary.append("")
            except Exception as e:
                logger.warning(f"Error loading signup data: {e}")
                summary.append("📥 **Signup Summary:** Error loading data\n")

            # 🔁 Absence summary with error handling
            try:
                if absent_data:
                    summary.append("🔁 **Absent Users:**")
                    for user_id, info in absent_data.items():
                        try:
                            marked_by = info.get("marked_by", "Unknown")
                            summary.append(f"<@{user_id}> (marked by {marked_by})")
                        except Exception as e:
                            logger.warning(f"Error processing absent user {user_id}: {e}")
                            summary.append(f"<@{user_id}> (error loading data)")
                else:
                    summary.append("🔁 **Absent Users:** None")
            except Exception as e:
                logger.warning(f"Error loading absent data: {e}")
                summary.append("🔁 **Absent Users:** Error loading data")

            # Post to all channels with error handling
            try:
                content = f"<@&{ROW_NOTIFICATION_ROLE_ID}>\n📊 **Weekly RoW Summary (Test)**\n\n" + "\n".join(summary)
                posted, failed = await post_to_all_alert_channels(bot, content=content)
                
                if posted:
                    logger.info(f"✅ Posted weekly RoW summary to: {', '.join(posted)}")
                if failed:
                    logger.warning(f"⚠️ Failed to post summary to: {', '.join(failed)}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to post weekly summary: {e}")
                
        except Exception as e:
            logger.exception(f"❌ Critical error in weekly summary: {e}")

# Error handling for task loops
@post_event_signup.before_loop
async def before_post_event_signup():
    """Wait for bot to be ready before starting event signup task."""
    try:
        logger.info("🔄 Waiting for bot to be ready (event signup task)...")
        await post_event_signup.bot.wait_until_ready()
        logger.info("✅ Bot ready - starting event signup task")
    except Exception as e:
        logger.error(f"❌ Error in before_post_event_signup: {e}")

@post_weekly_summary.before_loop
async def before_post_weekly_summary():
    """Wait for bot to be ready before starting weekly summary task."""
    try:
        logger.info("🔄 Waiting for bot to be ready (weekly summary task)...")
        await post_weekly_summary.bot.wait_until_ready()
        logger.info("✅ Bot ready - starting weekly summary task")
    except Exception as e:
        logger.error(f"❌ Error in before_post_weekly_summary: {e}")

# Error handling for task failures
@post_event_signup.error
async def post_event_signup_error(error):
    """Handle errors in event signup task."""
    logger.error(f"❌ Event signup task error: {error}")

@post_weekly_summary.error
async def post_weekly_summary_error(error):
    """Handle errors in weekly summary task."""
    logger.error(f"❌ Weekly summary task error: {error}")

# Health check function
async def scheduler_health_check(bot):
    """Check if scheduler tasks are running properly."""
    try:
        event_task_running = post_event_signup.is_running()
        summary_task_running = post_weekly_summary.is_running()
        
        logger.info(f"📊 Scheduler Health Check:")
        logger.info(f"  - Event signup task: {'✅ Running' if event_task_running else '❌ Stopped'}")
        logger.info(f"  - Weekly summary task: {'✅ Running' if summary_task_running else '❌ Stopped'}")
        
        # Try to restart stopped tasks
        if not event_task_running:
            logger.warning("🔄 Restarting event signup task...")
            post_event_signup.start(bot)
            
        if not summary_task_running:
            logger.warning("🔄 Restarting weekly summary task...")
            post_weekly_summary.start(bot)
            
    except Exception as e:
        logger.error(f"❌ Error in scheduler health check: {e}")

# Graceful shutdown function
def stop_scheduler():
    """Gracefully stop all scheduler tasks."""
    try:
        logger.info("🛑 Stopping scheduler tasks...")
        
        if post_event_signup.is_running():
            post_event_signup.cancel()
            logger.info("✅ Event signup task stopped")
            
        if post_weekly_summary.is_running():
            post_weekly_summary.cancel()
            logger.info("✅ Weekly summary task stopped")
            
    except Exception as e:
        logger.error(f"❌ Error stopping scheduler: {e}")
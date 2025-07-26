import os

# Base directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

# === Embed Colors ===
COLORS = {
    "PRIMARY": 0x5865F2,
    "SUCCESS": 0x57F287,
    "WARNING": 0xFEE75C,
    "DANGER": 0xED4245,
    "INFO": 0x5DADE2,
    "SECONDARY": 0x99AAB5,
    "BLURPLE": 0x5865F2,
    "GREEN": 0x57F287,
    "RED": 0xED4245,
    "YELLOW": 0xFEE75C,
    "ORANGE": 0xFF7A00,
    "PURPLE": 0x9932CC,
    "BLUE": 0x3498DB
}

# === Emojis ===
EMOJIS = {
    "SUCCESS": "✅",
    "ERROR": "❌", 
    "WARNING": "⚠️",
    "INFO": "ℹ️",
    "LOADING": "⏳",
    "TROPHY": "🏆",
    "CALENDAR": "🗓️",
    "CLOCK": "🕒",
    "DOT": "•",
    "BLOCKED": "🚫",
    "STATS": "📊",
    "WIN": "🏆",
    "LOSS": "💔",
    "TEAM": "👥",
    "USER": "👤",
    "ADMIN": "🛡️",
    "ALERT": "🔔",
    "FIRE": "🔥",
    "STAR": "⭐",
    "CHECK": "✅",
    "CROSS": "❌",
    "QUESTION": "❓",
    "EXCLAMATION": "❗",
    "THUMBS_UP": "👍",
    "THUMBS_DOWN": "👎"
}

# === Team Display Names ===
TEAM_DISPLAY = {
    "main_team": "🏆 Main Team",
    "team_2": "🔸 Team 2", 
    "team_3": "🔸 Team 3"
}

# === Multiple Channel Support ===
# The bot will post to ALL channels in this list
ALERT_CHANNEL_IDS = [
    1257673327032664145,  # Main server channel
    1311377465087885314   # Test server channel
]

# For backwards compatibility, keep the single channel ID as the first one
ALERT_CHANNEL_ID = ALERT_CHANNEL_IDS[0]

# === Role Config ===
ADMIN_ROLE_IDS = [1395129965405540452, 1258214711124688967]
MAIN_TEAM_ROLE_ID = 1346414253992574976
ROW_NOTIFICATION_ROLE_ID = 1235729244605120572

# === User Config ===
BOT_ADMIN_USER_ID = 1096858315826397354

# === Team Configuration ===
MAX_TEAM_SIZE = 35
TEAMS = ["main_team", "team_2", "team_3"]

# === Default Event Times ===
DEFAULT_TIMES = {
    "main_team": "14:00 UTC Saturday",
    "team_2": "14:00 UTC Sunday", 
    "team_3": "20:00 UTC Sunday"
}

# === File Paths ===
RESULTS_FILE = os.path.join(DATA_DIR, "event_results.json")
ABSENT_FILE = os.path.join(DATA_DIR, "absent_users.json")
IGN_MAP_FILE = os.path.join(DATA_DIR, "ign_map.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
BLOCKED_FILE = os.path.join(DATA_DIR, "blocked_users.json")
HISTORY_FILE = os.path.join(DATA_DIR, "events_history.json")
TIMES_FILE = os.path.join(DATA_DIR, "row_times.json")
LOG_FILE = os.path.join(DATA_DIR, "logs", "bot.log")

FILES = {
    "EVENTS": EVENTS_FILE,
    "BLOCKED": BLOCKED_FILE,
    "IGN_MAP": IGN_MAP_FILE,
    "RESULTS": RESULTS_FILE,
    "HISTORY": HISTORY_FILE,
    "TIMES": TIMES_FILE,
    "LOG": LOG_FILE,
    "ABSENT": ABSENT_FILE
}

# === Shortcuts ===
EVENT_FILE = FILES["EVENTS"]
HISTORY_FILE = FILES["HISTORY"]
BLOCKED_FILE = FILES["BLOCKED"]

# === Message Limits ===
MAX_MESSAGE_LENGTH = 2000
MAX_EMBED_DESCRIPTION = 4096
MAX_EMBED_FIELD_VALUE = 1024
MAX_EMBED_FIELD_NAME = 256
MAX_EMBED_TITLE = 256

# === Time Zones ===
TIMEZONE_UTC = "UTC"
TIMEZONE_EST = "US/Eastern"
TIMEZONE_PST = "US/Pacific"

# === Command Prefixes ===
COMMAND_PREFIX = "!"
ALTERNATIVE_PREFIXES = ["!", "?", "."]

# === Event Configuration ===
EVENT_DURATION_HOURS = 2
EVENT_REMINDER_MINUTES = [60, 30, 15, 5]  # Minutes before event to send reminders
AUTO_CLEANUP_DAYS = 30  # Days to keep old event data

# === Validation Limits ===
MIN_IGN_LENGTH = 2
MAX_IGN_LENGTH = 20
MIN_REASON_LENGTH = 1
MAX_REASON_LENGTH = 200
MAX_BLOCK_DAYS = 365
MIN_BLOCK_DAYS = 1

# === Status Messages ===
STATUS_MESSAGES = [
    "Managing RoW Events",
    "Type !commands for help",
    "Tracking team signups",
    "Recording match results"
]

# === API Endpoints (if needed) ===
API_BASE_URL = None  # Add if you use external APIs
WEBHOOK_URL = None   # Add if you use webhooks

# === Feature Flags ===
FEATURES = {
    "AUTO_POST_EVENTS": True,
    "WEEKLY_SUMMARIES": True,
    "ATTENDANCE_TRACKING": True,
    "RESULT_TRACKING": True,
    "MULTI_CHANNEL_SUPPORT": True,
    "AUTO_UNBLOCK_EXPIRED": True,
    "IGN_VALIDATION": True,
    "AUDIT_LOGGING": True
}

# === Logging Configuration ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# === Database Configuration (if using database instead of JSON) ===
DB_CONFIG = {
    "type": "json",  # Currently using JSON files
    "backup_enabled": False,
    "backup_interval_hours": 24
}

# === Security Configuration ===
SECURITY = {
    "max_command_rate_per_minute": 10,
    "max_button_clicks_per_minute": 5,
    "auto_ban_threshold": 3,
    "command_cooldown_seconds": 1
}

# === Event Schedule Configuration ===
SCHEDULE = {
    "auto_post_day": 1,      # Tuesday (0=Monday, 1=Tuesday, etc.)
    "auto_post_hour": 14,    # 14:00 UTC
    "auto_post_minute": 0,
    "summary_day": 6,        # Sunday
    "summary_hour": 23,      # 23:30 UTC
    "summary_minute": 30
}

# === Testing Configuration ===
TEST_MODE = True  # Set to False in production
TEST_SCHEDULE = {
    "post_interval_minutes": 2,
    "summary_interval_minutes": 3,
    "test_start_hour": 10,
    "test_start_minute": 52
}

# === Embed Templates ===
EMBED_TEMPLATES = {
    "success": {
        "color": COLORS["SUCCESS"],
        "emoji": EMOJIS["SUCCESS"]
    },
    "error": {
        "color": COLORS["DANGER"],
        "emoji": EMOJIS["ERROR"]
    },
    "warning": {
        "color": COLORS["WARNING"],
        "emoji": EMOJIS["WARNING"]
    },
    "info": {
        "color": COLORS["INFO"],
        "emoji": EMOJIS["INFO"]
    }
}

# === Team Statistics ===
TEAM_STATS = {
    "track_individual_performance": False,
    "track_attendance_rates": True,
    "track_win_loss_ratios": True,
    "generate_monthly_reports": False
}
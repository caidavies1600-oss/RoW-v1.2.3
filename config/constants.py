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
    "INFO": 0x5DADE2
}
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
    "INFO": 0x5DADE2
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
    "BLOCKED": "🚫",
    "STATS": "📊",
    "DOT": "•"
}

# === Team Display Names ===
TEAM_DISPLAY = {
    "main_team": "🏆 Main Team",
    "team_2": "🔸 Team 2", 
    "team_3": "🔸 Team 3"
}

# === Role Config ===
ADMIN_ROLE_IDS = [1395129965405540452, 1258214711124688967]
MAIN_TEAM_ROLE_ID = 1223358599187665017
ROW_NOTIFICATION_ROLE_ID = 1395129965405540452  # Filter members by this role to reduce API calls

# === Channel Config ===
ALERT_CHANNEL_ID = 1233171162599526470

# === User Config ===
BOT_ADMIN_USER_ID = 1096858315826397354

# === Default Event Times ===
DEFAULT_TIMES = {
    "main_team": "18:30 UTC Tuesday",
    "team_2": "18:30 UTC Tuesday", 
    "team_3": "18:30 UTC Tuesday"
}

# === File Paths ===
RESULTS_FILE = os.path.join(DATA_DIR, "event_results.json")
ABSENT_FILE = os.path.join(DATA_DIR, "absent_users.json")

FILES = {
    "EVENTS": os.path.join(DATA_DIR, "events.json"),
    "BLOCKED": os.path.join(DATA_DIR, "blocked_users.json"),
    "IGN_MAP": os.path.join(DATA_DIR, "ign_map.json"),
    "RESULTS": RESULTS_FILE,
    "HISTORY": os.path.join(DATA_DIR, "events_history.json"),
    "TIMES": os.path.join(DATA_DIR, "row_times.json"),
    "LOG": os.path.join(DATA_DIR, "logs", "bot.log"),
    "ABSENT": ABSENT_FILE,
    "SIGNUP_LOCK": os.path.join(DATA_DIR, "signup_lock.json"),
    "ROW_TIMES": os.path.join(DATA_DIR, "row_times.json"),
    "PLAYER_STATS": os.path.join(DATA_DIR, "player_stats.json")
}

# === Shortcuts ===
EVENT_FILE = FILES["EVENTS"]
HISTORY_FILE = FILES["HISTORY"]
BLOCKED_FILE = FILES["BLOCKED"]

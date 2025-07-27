"""Bot constants and configuration values."""

import os

# === Embed Colors ===
COLORS = {
    "PRIMARY": 0x5865F2,    # Discord blurple
    "SUCCESS": 0x57F287,    # Green
    "WARNING": 0xFEE75C,    # Yellow
    "DANGER": 0xED4245,     # Red
    "INFO": 0x5DADE2        # Light blue
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
    "DOT": "•",
    "ARROW": "➜",
    "CHECK": "✓",
    "CROSS": "✗"
}

# === Team Display Names ===
TEAM_DISPLAY = {
    "main_team": "🏆 Main Team",
    "team_2": "🔸 Team 2",
    "team_3": "🔸 Team 3"
}

# === File Paths ===
# Base directory setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "logs"), exist_ok=True)

# File paths dictionary
FILES = {
    "EVENTS": os.path.join(DATA_DIR, "events.json"),
    "BLOCKED": os.path.join(DATA_DIR, "blocked_users.json"),
    "IGN_MAP": os.path.join(DATA_DIR, "ign_map.json"),
    "RESULTS": os.path.join(DATA_DIR, "event_results.json"),
    "HISTORY": os.path.join(DATA_DIR, "events_history.json"),
    "TIMES": os.path.join(DATA_DIR, "row_times.json"),
    "ABSENT": os.path.join(DATA_DIR, "absent_users.json"),
    "LOG": os.path.join(DATA_DIR, "logs", "bot.log")
}

# === Shortcuts (for backwards compatibility) ===
RESULTS_FILE = FILES["RESULTS"]
ABSENT_FILE = FILES["ABSENT"]
EVENT_FILE = FILES["EVENTS"]
HISTORY_FILE = FILES["HISTORY"]
BLOCKED_FILE = FILES["BLOCKED"]
"""
Bot constants and static configuration.

This module contains all static configuration values that rarely change
and are not environment-dependent. Includes UI elements, file paths,
team configurations, and validation rules.

Note: Sensitive configuration should be stored in environment variables,
not in this file.
"""

import os
# config/settings.py exists but might need these critical imports in constants.py:
from config.settings import (
    DATA_DIR, ADMIN_ROLE_IDS, MAIN_TEAM_ROLE_ID, 
    ROW_NOTIFICATION_ROLE_ID, ALERT_CHANNEL_ID, 
    BOT_ADMIN_USER_ID, MAX_TEAM_SIZE, DEFAULT_TIMES
)
# Import settings for backward compatibility
try:
    from config.settings import (
        DATA_DIR, ADMIN_ROLE_IDS, MAIN_TEAM_ROLE_ID, 
        ROW_NOTIFICATION_ROLE_ID, ALERT_CHANNEL_ID, 
        BOT_ADMIN_USER_ID, MAX_TEAM_SIZE, DEFAULT_TIMES
    )
except ImportError:
    # Fallback values if settings not available
    DATA_DIR = "data"
    ADMIN_ROLE_IDS = []
    MAIN_TEAM_ROLE_ID = 0
    ROW_NOTIFICATION_ROLE_ID = 0
    ALERT_CHANNEL_ID = 0
    BOT_ADMIN_USER_ID = 0
    MAX_TEAM_SIZE = 40
    DEFAULT_TIMES = {}

# =============================================================================
# 🎨 UI & VISUAL CONSTANTS
# =============================================================================
"""Visual elements used throughout the bot for consistent styling.
Includes colors for embeds and standard emojis for message formatting."""

# Discord Embed Colors
COLORS = {
    "PRIMARY": 0x5865F2,     # Discord Blurple
    "SUCCESS": 0x57F287,     # Green
    "WARNING": 0xFEE75C,     # Yellow
    "DANGER": 0xED4245,      # Red
    "ERROR": 0xED4245,       # Red (alias)
    "INFO": 0x5DADE2,        # Light Blue
    "SECONDARY": 0x6C757D,   # Gray
    "DARK": 0x343A40,        # Dark Gray
}

# Emojis for consistent messaging
EMOJIS = {
    # Status indicators
    "SUCCESS": "✅",
    "ERROR": "❌", 
    "WARNING": "⚠️",
    "INFO": "ℹ️",
    "LOADING": "⏳",
    "BLOCKED": "🚫",

    # Activity icons
    "TROPHY": "🏆",
    "CALENDAR": "🗓️",
    "CLOCK": "🕒",
    "STATS": "📊",
    "GEAR": "⚙️",
    "SHIELD": "🛡️",

    # UI elements
    "DOT": "•",
    "ARROW_RIGHT": "➡️",
    "ARROW_LEFT": "⬅️",
    "UP_ARROW": "⬆️",
    "DOWN_ARROW": "⬇️",

    # Team/Game related
    "MAIN_TEAM": "🏆",
    "TEAM_2": "🔸",
    "TEAM_3": "🔸",
    "WIN": "🏆",
    "LOSS": "💔",
    "ABSENT": "📥",
}

# =============================================================================
# 🏆 TEAM CONFIGURATION
# =============================================================================
"""Team-related configuration including display names, colors, and descriptions.
Used for consistent team representation across all bot features."""

# Team display names with emojis
TEAM_DISPLAY = {
    "main_team": "🏆 Main Team",
    "team_2": "🔸 Team 2", 
    "team_3": "🔸 Team 3"
}

# Team colors for embeds
TEAM_COLORS = {
    "main_team": COLORS["PRIMARY"],
    "team_2": COLORS["INFO"],
    "team_3": COLORS["SECONDARY"]
}

# Team descriptions
TEAM_DESCRIPTIONS = {
    "main_team": "Competitive team for experienced players",
    "team_2": "Open to all skill levels",
    "team_3": "Open to all skill levels"
}

# =============================================================================
# 📁 FILE PATHS & DATA STRUCTURE
# =============================================================================
"""File path configurations for all data storage.
Includes paths for event data, user data, logs, and system files."""

# JSON data files
FILES = {
    # Core event data
    "EVENTS": os.path.join(DATA_DIR, "events.json"),
    "BLOCKED": os.path.join(DATA_DIR, "blocked_users.json"),
    "IGN_MAP": os.path.join(DATA_DIR, "ign_map.json"),
    "ABSENT": os.path.join(DATA_DIR, "absent_users.json"),

    # Results and history
    "RESULTS": os.path.join(DATA_DIR, "event_results.json"),
    "HISTORY": os.path.join(DATA_DIR, "events_history.json"),
    "PLAYER_STATS": os.path.join(DATA_DIR, "player_stats.json"),

    # Configuration
    "TIMES": os.path.join(DATA_DIR, "row_times.json"),
    "SIGNUP_LOCK": os.path.join(DATA_DIR, "signup_lock.json"),

    # System files
    "AUDIT_LOG": os.path.join(DATA_DIR, "audit_log.json"),
    "NOTIFICATION_PREFS": os.path.join(DATA_DIR, "notification_preferences.json"),
    "MATCH_STATS": os.path.join(DATA_DIR, "match_statistics.json"),

    # Logs
    "BOT_LOG": os.path.join(DATA_DIR, "logs", "bot.log"),
}

# Shortcut aliases for backward compatibility
EVENT_FILE = FILES["EVENTS"]
HISTORY_FILE = FILES["HISTORY"]
BLOCKED_FILE = FILES["BLOCKED"]
RESULTS_FILE = FILES["RESULTS"]
ABSENT_FILE = FILES["ABSENT"]

# =============================================================================
# 📅 TIME & SCHEDULING CONSTANTS
# =============================================================================
"""Time-related constants for event scheduling and automation.
Defines days, times, and configuration for automated tasks."""

# Day of week constants (for scheduler)
WEEKDAYS = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6
}

# Scheduler configuration
SCHEDULER_CONFIG = {
    "EVENT_POST_DAY": WEEKDAYS["TUESDAY"],
    "EVENT_POST_HOUR": 10,  # 10:00 UTC
    "TEAMS_LOCK_DAY": WEEKDAYS["THURSDAY"], 
    "TEAMS_LOCK_HOUR": 23,  # 23:59 UTC
    "SUMMARY_DAY": WEEKDAYS["SUNDAY"],
    "SUMMARY_HOUR": 23,  # 23:30 UTC
}

# =============================================================================
# 🎮 GAME MECHANICS CONSTANTS
# =============================================================================
"""Game-specific constants for player roles and match outcomes.
Includes specializations, result types, and moderation settings."""

# Player specializations
SPECIALIZATIONS = {
    "cavalry": "🐎 Cavalry",
    "mages": "🔮 Mages", 
    "archers": "🏹 Archers",
    "infantry": "⚔️ Infantry",
    "whale": "🐋 Whale"
}

# Match result types
RESULT_TYPES = ["win", "loss"]

# Ban duration options (in days)
BAN_DURATION_OPTIONS = [1, 3, 7, 14, 30]

# =============================================================================
# 📝 MESSAGE TEMPLATES
# =============================================================================
"""Standard message templates for consistent bot responses.
Includes error messages, command help, and common notifications."""

# Common message templates
MESSAGES = {
    "NO_PERMISSION": "❌ You don't have permission to use this command.",
    "EVENT_NOT_AVAILABLE": "❌ Event system not available.",
    "SIGNUPS_LOCKED": "🔒 Signups are currently locked! Teams have been finalized for this week.",
    "USER_BLOCKED": "🚫 You are currently blocked from signing up.",
    "TEAM_FULL": "❌ Team is full ({max_size}/{max_size}).",
    "ALREADY_IN_TEAM": "✅ You're already in that team!",
    "NOT_IN_ANY_TEAM": "ℹ️ You're not signed up for any team.",
    "IGN_NOT_SET": "⚠️ You haven't set your IGN yet. Use `!setign YourName`.",
}

# Command help descriptions
HELP_DESCRIPTIONS = {
    "setign": "Set your in-game name",
    "myign": "View your stored IGN", 
    "clearign": "Clear your stored IGN",
    "showteams": "Show current team signups",
    "startevent": "Start a new event (Admin only)",
    "win": "Record a win for a team (Admin only)",
    "loss": "Record a loss for a team (Admin only)",
    "block": "Block a user from signing up (Admin only)",
    "unblock": "Unblock a user (Admin only)",
    "absent": "Mark yourself as absent (Admin only)",
}

# =============================================================================
# 🔧 VALIDATION RULES
# =============================================================================
"""Validation rules and constraints for user input and data.
Defines acceptable formats for IGNs, user IDs, and team names."""

# IGN validation
IGN_RULES = {
    "MIN_LENGTH": 2,
    "MAX_LENGTH": 20,
    "ALLOWED_CHARS": r'^[a-zA-Z0-9\s_-]+$',
    "FORBIDDEN_WORDS": ["admin", "bot", "system", "everyone", "here"]
}

# User ID validation
USER_ID_RULES = {
    "MIN_ID": 17,  # Discord snowflake minimum length
    "MAX_ID": 19   # Discord snowflake maximum length
}

# Team name validation
TEAM_NAME_MAPPING = {
    "main": "main_team",
    "main_team": "main_team", 
    "team1": "main_team",
    "team_1": "main_team",
    "1": "main_team",

    "team2": "team_2",
    "team_2": "team_2",
    "2": "team_2",

    "team3": "team_3", 
    "team_3": "team_3",
    "3": "team_3"
}

# =============================================================================
# 🎯 FEATURE FLAGS
# =============================================================================
"""Feature toggles for enabling/disabling bot functionality.
Can be overridden by environment variables for deployment control."""

# Feature toggles (can be overridden by environment variables)
FEATURES = {
    "GOOGLE_SHEETS_SYNC": True,
    "SMART_NOTIFICATIONS": True,
    "ANALYTICS": True,
    "AUDIT_LOGGING": True,
    "AUTO_BACKUP": True,
    "RATE_LIMITING": True,
    "HEALTH_MONITORING": True,
}


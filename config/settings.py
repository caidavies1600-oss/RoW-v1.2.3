"""
Bot configuration settings.
Environment-dependent values that may change between deployments.
"""

import os
from typing import List

# =============================================================================
# 🔐 AUTHENTICATION & TOKENS
# =============================================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "❌ BOT_TOKEN environment variable is not set. "
        "Please set it in your environment or secrets."
    )

# Optional: Google Sheets integration
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# =============================================================================
# 🏛️ DISCORD SERVER CONFIGURATION
# =============================================================================

# Role IDs (these will be different per server)
ADMIN_ROLE_IDS: List[int] = [
    1395129965405540452,  # Role: Admin
    1258214711124688967   # Role: Moderator
]

MAIN_TEAM_ROLE_ID: int = 1346414253992574976
ROW_NOTIFICATION_ROLE_ID: int = 1235729244605120572

# Channel IDs (these will be different per server)
ALERT_CHANNEL_ID: int = 1311377465087885314

# User IDs
BOT_ADMIN_USER_ID: int = 1096858315826397354 # Discord User: ME

# =============================================================================
# ⚙️ BOT BEHAVIOR SETTINGS
# =============================================================================

# Team Configuration
MAX_TEAM_SIZE: int = 35
TEAMS = ["main_team", "team_2", "team_3"]

# Event Scheduling (UTC times)
DEFAULT_TIMES = {
    "main_team": "20:00 UTC Sunday",
    "team_2": "20:00 UTC Saturday", 
    "team_3": "14:00 UTC Sunday"
}

# Rate Limiting
RATE_LIMIT_COMMANDS_PER_MINUTE: int = 10
RATE_LIMIT_BUTTONS_PER_MINUTE: int = 5

# Backup Settings
MAX_BACKUPS_TO_KEEP: int = 30
AUTO_BACKUP_INTERVAL_HOURS: int = 6

# =============================================================================
# 📁 DIRECTORY CONFIGURATION
# =============================================================================

# Base directories
DATA_DIR = "data"
LOGS_DIR = f"{DATA_DIR}/logs"
BACKUP_DIR = f"{DATA_DIR}/backups"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# =============================================================================
# 🐛 DEBUG & DEVELOPMENT
# =============================================================================

# Debug settings (set via environment)
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Development server (for testing)
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0")) or None
"""Bot configuration settings."""

import os
from typing import List

# Discord Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "❌ BOT_TOKEN environment variable is not set. "
        "Please set it in your environment or secrets."
    )

# Role Configuration
ADMIN_ROLE_IDS: List[int] = [
    1395129965405540452,  # Role: Admin
    1258214711124688967   # Role: Moderator
]

MAIN_TEAM_ROLE_ID: int = 1346414253992574976
ROW_NOTIFICATION_ROLE_ID: int = 1235729244605120572

# Channel Configuration
ALERT_CHANNEL_ID: int = 1257673327032664145

# User Configuration
BOT_ADMIN_USER_ID: int = 1096858315826397354

# Team Configuration
MAX_TEAM_SIZE: int = 35
TEAMS = ["main_team", "team_2", "team_3"]

# Default Event Times
DEFAULT_TIMES = {
    "main_team": "14:00 UTC Saturday",
    "team_2": "14:00 UTC Sunday",
    "team_3": "20:00 UTC Sunday"
}

# File Paths
DATA_DIR = "data"
LOGS_DIR = f"{DATA_DIR}/logs"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
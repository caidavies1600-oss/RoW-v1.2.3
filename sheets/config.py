"""
Configuration for Google Sheets integration.
"""

# Team name mapping for display
TEAM_MAPPING = {
    "main_team": "Main Team",
    "team_2": "Team 2", 
    "team_3": "Team 3"
}

# Worksheet configurations
SHEET_CONFIGS = {
    "Current Teams": {
        "headers": ["Timestamp", "Team", "Player Count", "Players", "Status"],
        "rows": 100,
        "cols": 10
    },
    "Player Stats": {
        "headers": [
            "User ID", "Name", "Power Rating", "Main Team Wins", "Main Team Losses",
            "Team 2 Wins", "Team 2 Losses", "Team 3 Wins", "Team 3 Losses",
            "Total Events", "Last Active", "Notes"
        ],
        "rows": 500,
        "cols": 15
    },
    "Match Results": {
        "headers": [
            "Date", "Team", "Result", "Enemy Alliance", "Enemy Tag",
            "Our Power", "Enemy Power", "Recorded By", "Notes"
        ],
        "rows": 200,
        "cols": 12
    },
    "Event History": {
        "headers": [
            "Date", "Event Type", "Team", "Participants", "Results",
            "Duration", "Notes"
        ],
        "rows": 300,
        "cols": 10
    },
    "Alliance Tracking": {
        "headers": [
            "Alliance Name", "Tag", "Wins Against", "Losses Against", "Total Matches",
            "Win Rate", "Average Power", "Threat Level", "Strategy Notes",
            "Last Seen", "Kingdom", "Activity Level", "Difficulty", "Additional Notes"
        ],
        "rows": 100,
        "cols": 15
    },
    "Dashboard": {
        "headers": ["Metric", "Value", "Trend", "Notes"],
        "rows": 50,
        "cols": 8
    }
}

# Rate limiting settings
RATE_LIMIT_REQUESTS_PER_MINUTE = 100
RATE_LIMIT_BATCH_SIZE = 50

# Retry settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1
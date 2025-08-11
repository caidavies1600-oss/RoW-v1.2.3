"""
Configuration for Google Sheets integration.

This module contains:
- Team name mappings and display names
- Sheet configurations and layouts
- Default data structures
- Column mappings for data access
- Data validation rules

Each sheet's configuration defines:
- Header structure
- Initial dimensions
- Data types and formats
- Validation rules
"""

# Team mapping for display names
"""Team name mappings for consistent display and lookup."""
TEAM_MAPPING = {
    "main_team": "Main Team", 
    "team_2": "Team 2", 
    "team_3": "Team 3"
}

# Reverse mapping for loading data
"""Reverse mappings for converting display names back to internal names."""
TEAM_REVERSE_MAPPING = {
    "Main Team": "main_team",
    "Team 2": "team_2", 
    "Team 3": "team_3"
}

# Sheet configurations
"""
Configuration for each worksheet including headers and dimensions.
Each sheet has:
- Header columns defined
- Initial row count
- Initial column count
- Expected data structure
"""
SHEET_CONFIGS = {
    "Current Teams": {
        "headers": ["Timestamp", "Team", "Player Count", "Players", "Status"],
        "rows": 50,
        "cols": 10
    },
    "Player Stats": {
        "headers": [
            "User ID", "Display Name", "Main Team Role", 
            "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
            "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses", 
            "Win Rate", "Absents", "Blocked", "Power Rating", 
            "Cavalry", "Mages", "Archers", "Infantry", "Whale Status", "Last Updated"
        ],
        "rows": 300,
        "cols": 21
    },
    "Results History": {
        "headers": ["Date", "Team", "Result", "Players", "By", "Total Wins", "Total Losses"],
        "rows": 1000,
        "cols": 7
    },
    "Match Statistics": {
        "headers": [
            "Match ID", "Date", "Team", "Result", "Enemy Alliance Name", "Enemy Alliance Tag",
            "Our Matchmaking Power", "Our Lifestone Points", "Our Occupation Points",
            "Our Gathering Points", "Our Total Kills", "Our Total Wounded", "Our Total Healed",
            "Our Lifestone Obtained", "Enemy Matchmaking Power", "Enemy Lifestone Points", 
            "Enemy Occupation Points", "Enemy Gathering Points", "Enemy Total Kills", 
            "Enemy Total Wounded", "Enemy Total Healed", "Enemy Lifestone Obtained", 
            "Players Participated", "Recorded By", "Notes"
        ],
        "rows": 500,
        "cols": 25
    },
    "Alliance Tracking": {
        "headers": [
            "Alliance Name", "Alliance Tag", "Matches Against", "Wins Against Them", 
            "Losses Against Them", "Win Rate vs Them", "Average Enemy Power",
            "Difficulty Rating", "Strategy Notes", "Last Fought", "Server/Kingdom",
            "Alliance Level", "Activity Level", "Threat Level", "Additional Notes"
        ],
        "rows": 200,
        "cols": 15
    },
    "Notification Preferences": {
        "headers": [
            "User ID", "Method", "Event Reminders", "Result Notifications", "Team Updates",
            "Reminder Times", "Quiet Start", "Quiet End", "Timezone Offset", "Last Updated"
        ],
        "rows": 300,
        "cols": 10
    },
    "Dashboard": {
        "headers": ["Component", "Value", "Last Updated"],
        "rows": 50,
        "cols": 10
    }
}

# Default data structures for fallback
"""
Default data structures used when initializing new sheets
or when data cannot be loaded. Provides safe fallback values
and maintains data structure consistency.
"""
DEFAULT_DATA = {
    "events": {"main_team": [], "team_2": [], "team_3": []},
    "blocked": {},
    "results": {"total_wins": 0, "total_losses": 0, "history": []},
    "player_stats": {},
    "ign_map": {},
    "absent": {},
    "notification_preferences": {
        "users": {},
        "default_settings": {
            "method": "channel",
            "event_reminders": True,
            "result_notifications": True,
            "team_updates": True,
            "reminder_times": [60, 15],
            "quiet_hours": {"start": 22, "end": 8},
            "timezone_offset": 0
        }
    }
}

# Column mappings for easier data access
"""
Index mappings for player stats columns to provide
named access to columnar data. Used for consistent
data access and validation across the application.
"""
PLAYER_STATS_COLUMNS = {
    "user_id": 0,
    "display_name": 1,
    "main_team_role": 2,
    "main_wins": 3,
    "main_losses": 4,
    "team2_wins": 5,
    "team2_losses": 6,
    "team3_wins": 7,
    "team3_losses": 8,
    "total_wins": 9,
    "total_losses": 10,
    "win_rate": 11,
    "absents": 12,
    "blocked": 13,
    "power_rating": 14,
    "cavalry": 15,
    "mages": 16,
    "archers": 17,
    "infantry": 18,
    "whale_status": 19,
    "last_updated": 20
}

# Validation rules
"""
Data validation rules for sheet columns.
Defines:
- Data types and ranges
- Valid value sets
- Default values
- Format requirements
"""
VALIDATION_RULES = {
    "power_rating": {
        "type": "number",
        "min": 0,
        "max": 10000000000,  # 10 billion max power
        "default": 0
    },
    "specializations": {
        "type": "boolean_text",
        "valid_values": ["Yes", "No", "yes", "no", "YES", "NO"],
        "default": "No"
    },
    "main_team_role": {
        "type": "boolean_text", 
        "valid_values": ["Yes", "No", "yes", "no", "YES", "NO"],
        "default": "No"
    },
    "blocked": {
        "type": "boolean_text",
        "valid_values": ["Yes", "No", "yes", "no", "YES", "NO"],
        "default": "No"
    }
}
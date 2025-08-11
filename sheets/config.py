"""
Configuration for Google Sheets integration - FIXED VERSION.
"""

# Team name mapping for display
TEAM_MAPPING = {
    "main_team": "Main Team",
    "team_2": "Team 2", 
    "team_3": "Team 3"
}

# Worksheet configurations with proper sizing
SHEET_CONFIGS = {
    "Current Teams": {
        "headers": ["Timestamp", "Team", "Player Count", "Players", "Status"],
        "rows": 50,  # Reduced from 100
        "cols": 8    # Extra columns for expansion
    },
    "Player Stats": {
        "headers": [
            "User ID", "Name", "Power Rating", "Main Team Wins", "Main Team Losses",
            "Team 2 Wins", "Team 2 Losses", "Team 3 Wins", "Team 3 Losses",
            "Total Events", "Last Active", "Notes"
        ],
        "rows": 200,  # Reduced from 500
        "cols": 15
    },
    "Match Results": {
        "headers": [
            "Date", "Team", "Result", "Enemy Alliance", "Enemy Tag",
            "Our Power", "Enemy Power", "Recorded By", "Notes"
        ],
        "rows": 100,  # Reduced from 200
        "cols": 12
    },
    "Event History": {
        "headers": [
            "Date", "Event Type", "Team", "Participants", "Results",
            "Duration", "Notes"
        ],
        "rows": 150,  # Reduced from 300
        "cols": 10
    },
    "Alliance Tracking": {
        "headers": [
            "Alliance Name", "Tag", "Wins Against", "Losses Against", "Total Matches",
            "Win Rate", "Average Power", "Threat Level", "Strategy Notes",
            "Last Seen", "Kingdom", "Activity Level", "Difficulty", "Additional Notes"
        ],
        "rows": 50,   # Reduced from 100
        "cols": 15
    },
    "Dashboard": {
        "headers": ["Metric", "Value", "Trend", "Notes"],
        "rows": 30,   # Reduced from 50
        "cols": 8
    }
}

# Enhanced rate limiting settings
RATE_LIMIT_SETTINGS = {
    "requests_per_minute": 60,        # Conservative limit
    "batch_size": 20,                 # Smaller batches
    "delay_between_operations": 2.0,  # Seconds
    "delay_between_batches": 5.0,     # Seconds
    "delay_between_rows": 0.5,        # Seconds
    "max_retries": 3,
    "retry_delay": 2.0
}

# Retry settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

# Template settings
TEMPLATE_SETTINGS = {
    "max_players_in_template": 50,    # Limit players in template creation
    "chunk_size": 15,                 # Process players in smaller chunks
    "enable_header_freezing": True,   # Enable row freezing
    "apply_formatting": True,         # Apply colors and formatting
    "create_example_rows": True       # Add example data
}

# Color schemes for different worksheets
COLOR_SCHEMES = {
    "Current Teams": "blue",
    "Player Stats": "blue", 
    "Match Results": "orange",
    "Alliance Tracking": "red",
    "Dashboard": "green",
    "Event History": "purple"
}

# Validation settings
VALIDATION_SETTINGS = {
    "max_sheet_size": 1000,          # Maximum rows per sheet
    "max_batch_update_size": 25,     # Maximum rows per batch update
    "validate_data_types": True,     # Validate data before sending
    "sanitize_strings": True         # Clean string data
}
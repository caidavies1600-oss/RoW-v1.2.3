"""Configuration for Google Sheets integration."""

# Sheet configurations
SHEET_CONFIGS = {
    "Current Teams": {
        "headers": ["Timestamp", "Team", "Player Count", "Players", "Status"],
        "rows": 10,
        "cols": 5
    },
    "Player Stats": {
        "headers": [
            "User ID", "Name", "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
            "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses", "Absents", "Blocked",
            "Power Rating", "Cavalry", "Mages", "Archers", "Infantry", "Whale Status"
        ],
        "rows": 300,
        "cols": 20
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

# Team mapping
TEAM_MAPPING = {
    "main_team": "Main Team", 
    "team_2": "Team 2", 
    "team_3": "Team 3"
}
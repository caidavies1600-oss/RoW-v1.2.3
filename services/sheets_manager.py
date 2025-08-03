
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
from utils.logger import setup_logger
import os
from typing import Dict, List, Any

logger = setup_logger("sheets_manager")

class SheetsManager:
    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.initialize_client()

    def initialize_client(self):
        """Initialize Google Sheets client with service account credentials."""
        try:
            # Define the scope
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # Load credentials from environment variable or file
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            else:
                creds = Credentials.from_service_account_file('credentials.json', scopes=scope)

            self.gc = gspread.authorize(creds)

            # Open the spreadsheet
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
            if spreadsheet_id:
                self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            else:
                self.spreadsheet = self.gc.create("Discord RoW Bot Data")
                logger.info(f"Created new spreadsheet: {self.spreadsheet.url}")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            self.gc = None
            self.spreadsheet = None

    def load_data_from_sheets(self):
        """Load all bot data from Google Sheets - primary data source."""
        if not self.spreadsheet:
            return None

        try:
            data = {
                "events": {"main_team": [], "team_2": [], "team_3": []},
                "blocked": {},
                "results": {"total_wins": 0, "total_losses": 0, "history": []},
                "player_stats": {},
                "ign_map": {},
                "absent": {}
            }

            # Load Current Teams
            try:
                worksheet = self.spreadsheet.worksheet("Current Teams")
                rows = worksheet.get_all_records()
                for row in rows:
                    team = row.get("Team", "").lower().replace(" ", "_")
                    players = row.get("Players", "")
                    if team in data["events"] and players:
                        player_list = [p.strip() for p in players.split(",") if p.strip()]
                        data["events"][team] = player_list
            except gspread.WorksheetNotFound:
                logger.info("Current Teams sheet not found, using defaults")

            # Load Player Stats
            try:
                worksheet = self.spreadsheet.worksheet("Player Stats")
                rows = worksheet.get_all_records()
                for row in rows:
                    user_id = str(row.get("User ID", ""))
                    if user_id:
                        data["player_stats"][user_id] = {
                            "name": row.get("Name", ""),
                            "team_results": {
                                "main_team": {
                                    "wins": int(row.get("Main Wins", 0) or 0),
                                    "losses": int(row.get("Main Losses", 0) or 0)
                                },
                                "team_2": {
                                    "wins": int(row.get("Team2 Wins", 0) or 0),
                                    "losses": int(row.get("Team2 Losses", 0) or 0)
                                },
                                "team_3": {
                                    "wins": int(row.get("Team3 Wins", 0) or 0),
                                    "losses": int(row.get("Team3 Losses", 0) or 0)
                                }
                            },
                            "absents": int(row.get("Absents", 0) or 0),
                            "blocked": row.get("Blocked", "No") == "Yes"
                        }
            except gspread.WorksheetNotFound:
                logger.info("Player Stats sheet not found, using defaults")

            # Load Results History
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
                rows = worksheet.get_all_records()
                for row in rows:
                    if row.get("Date"):
                        data["results"]["history"].append({
                            "date": row.get("Date"),
                            "team": row.get("Team"),
                            "result": row.get("Result").lower(),
                            "players": row.get("Players", "").split(",") if row.get("Players") else [],
                            "by": row.get("By"),
                            "timestamp": row.get("Date")  # Fallback
                        })
                
                # Calculate totals
                data["results"]["total_wins"] = sum(1 for r in data["results"]["history"] if r["result"] == "win")
                data["results"]["total_losses"] = sum(1 for r in data["results"]["history"] if r["result"] == "loss")

            except gspread.WorksheetNotFound:
                logger.info("Results History sheet not found, using defaults")

            logger.info("✅ Successfully loaded data from Google Sheets")
            return data

        except Exception as e:
            logger.error(f"Failed to load data from sheets: {e}")
            return None

    def sync_current_teams(self, events_data):
        """Sync current team signups to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Current Teams")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Current Teams", rows="10", cols="5")

            # Clear and add headers
            worksheet.clear()
            headers = ["Timestamp", "Team", "Player Count", "Players", "Status"]
            worksheet.append_row(headers)

            # Add current data
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            team_mapping = {"main_team": "Main Team", "team_2": "Team 2", "team_3": "Team 3"}
            
            for team_key, players in events_data.items():
                team_name = team_mapping.get(team_key, team_key)
                player_list = ", ".join(str(p) for p in players) if players else ""
                status = "Active"
                
                row = [timestamp, team_name, len(players), player_list, status]
                worksheet.append_row(row)

            logger.info("✅ Synced current teams to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync current teams: {e}")
            return False

    def sync_player_stats(self, player_stats):
        """Create player stats template with current players for manual data entry."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Player Stats")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Player Stats", rows="300", cols="20")

            # Only create template if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                # Clear and add headers
                worksheet.clear()
                headers = [
                    "User ID", "Name", "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
                    "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses", "Absents", "Blocked",
                    "Power Rating", "Cavalry", "Mages", "Archers", "Infantry", "Whale Status"
                ]
                worksheet.append_row(headers)

                # Add template rows for current players (empty data for manual entry)
                for user_id, stats in player_stats.items():
                    row = [
                        user_id,
                        stats.get("name", "Unknown"),
                        0,  # Main Wins - to be filled manually
                        0,  # Main Losses - to be filled manually
                        0,  # Team2 Wins - to be filled manually
                        0,  # Team2 Losses - to be filled manually
                        0,  # Team3 Wins - to be filled manually
                        0,  # Team3 Losses - to be filled manually
                        0,  # Total Wins - formula: =C2+E2+G2
                        0,  # Total Losses - formula: =D2+F2+H2
                        0,  # Absents - to be filled manually
                        "No",  # Blocked - to be filled manually
                        "",  # Power Rating - to be filled manually
                        "",  # Cavalry - to be filled manually (Yes/No)
                        "",  # Mages - to be filled manually (Yes/No)
                        "",  # Archers - to be filled manually (Yes/No)
                        "",  # Infantry - to be filled manually (Yes/No)
                        ""   # Whale Status - to be filled manually (Yes/No)
                    ]
                    worksheet.append_row(row)
                
                logger.info("✅ Created player stats template for manual entry")
            else:
                logger.info("✅ Player stats sheet already exists, skipping template creation")
            
            return True

        except Exception as e:
            logger.error(f"Failed to create player stats template: {e}")
            return False

    def sync_results_history(self, results_data):
        """Sync detailed results history to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Results History", rows="1000", cols="7")

            # Clear and add headers
            worksheet.clear()
            headers = ["Date", "Team", "Result", "Players", "By", "Total Wins", "Total Losses"]
            worksheet.append_row(headers)

            # Add results data
            for entry in results_data.get("history", []):
                try:
                    date = entry.get("date", entry.get("timestamp", "Unknown"))
                    if "T" in str(date):  # ISO format
                        date = datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
                except:
                    date = str(entry.get("date", "Unknown"))

                team = entry.get("team", "Unknown")
                result = entry.get("result", "Unknown").capitalize()
                players = ", ".join(entry.get("players", []))
                recorded_by = entry.get("by", entry.get("recorded_by", "Unknown"))

                row = [
                    date,
                    team.replace("_", " ").title(),
                    result,
                    players,
                    recorded_by,
                    results_data.get("total_wins", 0),
                    results_data.get("total_losses", 0)
                ]
                worksheet.append_row(row)

            logger.info("✅ Synced results history to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync results history: {e}")
            return False

    def create_dashboard(self):
        """Create an interactive dashboard with dropdowns and charts."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Dashboard")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Dashboard", rows="50", cols="10")

            # Clear and set up dashboard structure
            worksheet.clear()
            
            # Title and instructions
            worksheet.update('A1', 'RoW Bot Dashboard')
            worksheet.update('A2', 'Select Player:')
            worksheet.update('A3', 'Player Stats will appear below')
            
            # Format headers
            worksheet.format('A1', {
                'textFormat': {'bold': True, 'fontSize': 16},
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 1.0}
            })
            
            # Add dropdown for player selection (Note: Requires manual setup in Sheets)
            worksheet.update('B2', 'Please add Data Validation dropdown manually pointing to Player Stats column A')
            
            # Stats display area
            stats_headers = [
                'Team', 'Wins', 'Losses', 'Win Rate', 'Total Events'
            ]
            for i, header in enumerate(stats_headers):
                worksheet.update_cell(5, i+1, header)
            
            # Chart placeholder
            worksheet.update('A15', 'Charts can be added manually using Insert > Chart')
            worksheet.update('A16', 'Suggested: Bar chart showing wins/losses per team')
            worksheet.update('A17', 'Suggested: Pie chart showing team participation distribution')

            logger.info("✅ Created dashboard template")
            return True

        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return False

    def sync_notification_preferences(self, notification_prefs):
        """Sync notification preferences to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Notification Preferences")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Notification Preferences", rows="300", cols="10")

            # Clear and add headers
            worksheet.clear()
            headers = [
                "User ID", "Method", "Event Reminders", "Result Notifications", "Team Updates",
                "Reminder Times", "Quiet Start", "Quiet End", "Timezone Offset", "Last Updated"
            ]
            worksheet.append_row(headers)

            # Add user preferences
            for user_id, prefs in notification_prefs.get("users", {}).items():
                reminder_times = ",".join(map(str, prefs.get("reminder_times", [60, 15])))
                quiet_hours = prefs.get("quiet_hours", {"start": 22, "end": 8})
                
                row = [
                    user_id,
                    prefs.get("method", "channel"),
                    "Yes" if prefs.get("event_reminders", True) else "No",
                    "Yes" if prefs.get("result_notifications", True) else "No",
                    "Yes" if prefs.get("team_updates", True) else "No",
                    reminder_times,
                    quiet_hours["start"],
                    quiet_hours["end"],
                    prefs.get("timezone_offset", 0),
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                ]
                worksheet.append_row(row)

            logger.info("✅ Synced notification preferences to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync notification preferences: {e}")
            return False

    def load_notification_preferences_from_sheets(self):
        """Load notification preferences from Google Sheets."""
        if not self.spreadsheet:
            return None

        try:
            worksheet = self.spreadsheet.worksheet("Notification Preferences")
            rows = worksheet.get_all_records()
            
            preferences = {
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
            
            for row in rows:
                user_id = str(row.get("User ID", ""))
                if user_id:
                    reminder_times = []
                    try:
                        reminder_str = row.get("Reminder Times", "60,15")
                        reminder_times = [int(x.strip()) for x in reminder_str.split(",") if x.strip()]
                    except:
                        reminder_times = [60, 15]
                    
                    preferences["users"][user_id] = {
                        "method": row.get("Method", "channel"),
                        "event_reminders": row.get("Event Reminders", "Yes") == "Yes",
                        "result_notifications": row.get("Result Notifications", "Yes") == "Yes",
                        "team_updates": row.get("Team Updates", "Yes") == "Yes",
                        "reminder_times": reminder_times,
                        "quiet_hours": {
                            "start": int(row.get("Quiet Start", 22) or 22),
                            "end": int(row.get("Quiet End", 8) or 8)
                        },
                        "timezone_offset": int(row.get("Timezone Offset", 0) or 0)
                    }
            
            logger.info("✅ Loaded notification preferences from Google Sheets")
            return preferences

        except gspread.WorksheetNotFound:
            logger.info("Notification Preferences sheet not found, using defaults")
            return None
        except Exception as e:
            logger.error(f"Failed to load notification preferences from sheets: {e}")
            return None

    def create_match_statistics_template(self):
        """Create match statistics template for manual data entry."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Match Statistics")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Match Statistics", rows="500", cols="25")

            # Create template only if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                worksheet.clear()
                headers = [
                    "Match ID", "Date", "Team", "Result", "Enemy Alliance Name", "Enemy Alliance Tag",
                    "Our Matchmaking Power", "Our Lifestone Points", "Our Occupation Points",
                    "Our Gathering Points", "Our Total Kills", "Our Total Wounded", "Our Total Healed",
                    "Our Lifestone Obtained", "Enemy Matchmaking Power", "Enemy Lifestone Points", 
                    "Enemy Occupation Points", "Enemy Gathering Points", "Enemy Total Kills", 
                    "Enemy Total Wounded", "Enemy Total Healed", "Enemy Lifestone Obtained", 
                    "Players Participated", "Recorded By", "Notes"
                ]
                worksheet.append_row(headers)
                
                # Add formatting instructions
                worksheet.update('A2', 'Enter match data manually here')
                worksheet.update('B2', 'YYYY-MM-DD format')
                worksheet.update('C2', 'Main Team/Team 2/Team 3')
                worksheet.update('D2', 'Win/Loss')
                worksheet.update('E2', 'Enemy alliance name')
                worksheet.update('F2', 'Enemy alliance tag')
                
                logger.info("✅ Created match statistics template for manual entry")
            else:
                logger.info("✅ Match statistics sheet already exists, skipping template creation")
            
            return True

        except Exception as e:
            logger.error(f"Failed to create match statistics template: {e}")
            return False

    def create_alliance_tracking_sheet(self):
        """Create alliance tracking sheet for enemy alliance performance."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Alliance Tracking")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Alliance Tracking", rows="200", cols="15")

            # Create template only if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                worksheet.clear()
                headers = [
                    "Alliance Name", "Alliance Tag", "Matches Against", "Wins Against Them", 
                    "Losses Against Them", "Win Rate vs Them", "Average Enemy Power",
                    "Difficulty Rating", "Strategy Notes", "Last Fought", "Server/Kingdom",
                    "Alliance Level", "Activity Level", "Threat Level", "Additional Notes"
                ]
                worksheet.append_row(headers)
                
                # Add example row
                example_row = [
                    "Example Alliance", "EX", 0, 0, 0, "0%", 0,
                    "Medium", "They focus on cavalry", "Never", "K123",
                    "High", "Very Active", "High", "Strong in KvK events"
                ]
                worksheet.append_row(example_row)
                
                logger.info("✅ Created alliance tracking template")
            else:
                logger.info("✅ Alliance tracking sheet already exists, skipping template creation")
            
            return True

        except Exception as e:
            logger.error(f"Failed to create alliance tracking sheet: {e}")
            return False

    def create_error_summary(self, error_data=None):
        """Create error summary sheet for monitoring."""
        if not self.spreadsheet:
            return False

        try:
            # Get or create the worksheet
            try:
                worksheet = self.spreadsheet.worksheet("Error Summary")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Error Summary", rows="100", cols="6")

            # Clear and add headers
            worksheet.clear()
            headers = ["Timestamp", "Cog", "Function", "Error Type", "Count", "Last Occurrence"]
            worksheet.append_row(headers)

            # Add sample error data if provided
            if error_data:
                for error in error_data:
                    row = [
                        error.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
                        error.get("cog", "Unknown"),
                        error.get("function", "Unknown"),
                        error.get("error_type", "Unknown"),
                        error.get("count", 1),
                        error.get("last_occurrence", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
                    ]
                    worksheet.append_row(row)

            logger.info("✅ Created error summary sheet")
            return True

        except Exception as e:
            logger.error(f"Failed to create error summary: {e}")
            return False

    def create_all_templates(self, all_data):
        """Create all sheet templates for manual data entry."""
        if not self.spreadsheet:
            logger.warning("Google Sheets not initialized, skipping template creation")
            return False

        try:
            success_count = 0
            
            # Create current teams template
            if self.sync_current_teams(all_data.get("events", {})):
                success_count += 1
            
            # Create player stats template
            if self.sync_player_stats(all_data.get("player_stats", {})):
                success_count += 1
            
            # Create results history template
            if self.sync_results_history(all_data.get("results", {})):
                success_count += 1
            
            # Create match statistics template
            if self.create_match_statistics_template():
                success_count += 1
            
            # Create alliance tracking template
            if self.create_alliance_tracking_sheet():
                success_count += 1
            
            # Create notification preferences template
            if self.sync_notification_preferences(all_data.get("notification_preferences", {})):
                success_count += 1
            
            # Create dashboard
            if self.create_dashboard():
                success_count += 1
            
            # Create error summary
            if self.create_error_summary():
                success_count += 1

            logger.info(f"✅ Template creation completed: {success_count}/8 operations successful")
            return success_count >= 6  # Consider successful if most operations work

        except Exception as e:
            logger.error(f"Failed to create templates: {e}")
            return False

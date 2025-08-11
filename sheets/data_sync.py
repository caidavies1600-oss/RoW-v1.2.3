
import gspread
import time
from datetime import datetime
from .base_connection import BaseSheetsConnection
from .error_handler import SheetsErrorHandler
from .template_creator import SheetsTemplateCreator as TemplateCreator
from utils.logger import setup_logger

logger = setup_logger("data_sync")

class DataSync(BaseSheetsConnection, TemplateCreator):
    """Handles data loading and syncing operations with complete method coverage."""

    def __init__(self):
        """Initialize data sync with connection and template capabilities."""
        super().__init__()  # Initialize connection
        # TemplateCreator will be available through multiple inheritance

    @SheetsErrorHandler.handle_rate_limit
    def sync_player_stats(self, player_stats_data):
        """Sync player statistics to Google Sheets with proper formatting."""
        if not SheetsErrorHandler.validate_data(player_stats_data, dict):
            return False

        if not self.is_connected():
            logger.error("❌ Cannot sync player stats - not connected")
            return False

        try:
            from .config import SHEET_CONFIGS
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])
            
            if not worksheet:
                return False

            # Clear and add headers
            worksheet.clear()
            worksheet.append_row(config["headers"])

            # Format header
            worksheet.format("A1:R1", {
                "backgroundColor": {"red": 0.1, "green": 0.4, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 11,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header row
            worksheet.freeze(rows=1)

            # Add player data
            if player_stats_data:
                for i, (user_id, stats) in enumerate(player_stats_data.items()):
                    # Rate limiting: pause every 15 players
                    if i > 0 and i % 15 == 0:
                        logger.info(f"Processed {i} players, pausing 3s for rate limit...")
                        time.sleep(3)

                    try:
                        # Calculate derived stats safely
                        team_results = stats.get("team_results", {})
                        main_results = team_results.get("main_team", {})
                        team2_results = team_results.get("team_2", {})
                        team3_results = team_results.get("team_3", {})
                        
                        main_wins = main_results.get("wins", 0) if isinstance(main_results, dict) else 0
                        main_losses = main_results.get("losses", 0) if isinstance(main_results, dict) else 0
                        team2_wins = team2_results.get("wins", 0) if isinstance(team2_results, dict) else 0
                        team2_losses = team2_results.get("losses", 0) if isinstance(team2_results, dict) else 0
                        team3_wins = team3_results.get("wins", 0) if isinstance(team3_results, dict) else 0
                        team3_losses = team3_results.get("losses", 0) if isinstance(team3_results, dict) else 0
                        
                        total_wins = main_wins + team2_wins + team3_wins
                        total_losses = main_losses + team2_losses + team3_losses

                        # Get specializations safely
                        specs = stats.get("specializations", {})
                        if not isinstance(specs, dict):
                            specs = {}
                        
                        row_data = [
                            str(user_id),
                            stats.get("name", f"Player_{user_id}"),
                            stats.get("display_name", "Unknown"),
                            "Yes" if stats.get("has_main_role", False) else "No",
                            main_wins, main_losses,
                            team2_wins, team2_losses, 
                            team3_wins, team3_losses,
                            total_wins, total_losses,
                            stats.get("absents", 0),
                            "Yes" if stats.get("blocked", False) else "No",
                            stats.get("power_rating", 0),
                            "Yes" if specs.get("cavalry", False) else "No",
                            "Yes" if specs.get("mages", False) else "No",
                            "Yes" if specs.get("archers", False) else "No",
                            "Yes" if specs.get("infantry", False) else "No",
                            "Yes" if specs.get("whale", False) else "No"
                        ]
                        
                        worksheet.append_row(row_data)

                    except Exception as e:
                        logger.warning(f"Failed to sync player {user_id}: {e}")
                        continue

            SheetsErrorHandler.log_sync_operation(
                "Player Stats", True, len(player_stats_data) if player_stats_data else 0
            )
            return True

        except Exception as e:
            SheetsErrorHandler.log_sync_operation("Player Stats", False, error=str(e))
            return False

    @SheetsErrorHandler.handle_rate_limit  
    def sync_results_history(self, results_data):
        """Sync results history to Google Sheets."""
        if not SheetsErrorHandler.validate_data(results_data, dict):
            return False

        if not self.is_connected():
            logger.error("❌ Cannot sync results - not connected")
            return False

        try:
            from .config import SHEET_CONFIGS
            config = SHEET_CONFIGS["Results History"]
            worksheet = self.get_or_create_worksheet("Results History", config["rows"], config["cols"])
            
            if not worksheet:
                return False

            # Clear and add headers
            worksheet.clear()
            worksheet.append_row(config["headers"])

            # Format header
            worksheet.format("A1:G1", {
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Add results data with proper rate limiting
            history = results_data.get("history", []) if isinstance(results_data, dict) else []
            for i, entry in enumerate(history):
                # Rate limiting: pause every 10 entries
                if i > 0 and i % 10 == 0:
                    logger.info(f"Processed {i} results, pausing 2s for rate limit...")
                    time.sleep(2)

                try:
                    # Handle date formatting
                    date = entry.get("date", entry.get("timestamp", "Unknown"))
                    if isinstance(date, str) and "T" in date:  # ISO format
                        try:
                            date = datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
                        except:
                            date = str(date)
                    
                    team = entry.get("team", "Unknown")
                    from .config import TEAM_MAPPING
                    team_display = TEAM_MAPPING.get(team, team)
                    
                    result = entry.get("result", "Unknown").capitalize()
                    players = ", ".join(entry.get("players", [])) if entry.get("players") else ""
                    recorded_by = entry.get("by", entry.get("recorded_by", "Unknown"))

                    row_data = [
                        date,
                        team_display,
                        result,
                        players,
                        recorded_by,
                        results_data.get("total_wins", 0),
                        results_data.get("total_losses", 0)
                    ]
                    
                    worksheet.append_row(row_data)

                except Exception as e:
                    logger.warning(f"Failed to sync result entry {i}: {e}")
                    continue

            SheetsErrorHandler.log_sync_operation("Results History", True, len(history))
            return True

        except Exception as e:
            SheetsErrorHandler.log_sync_operation("Results History", False, error=str(e))
            return False

    @SheetsErrorHandler.handle_rate_limit
    def sync_notification_preferences(self, notification_prefs):
        """Sync notification preferences to Google Sheets."""
        if not SheetsErrorHandler.validate_data(notification_prefs, dict):
            return False

        if not self.is_connected():
            logger.error("❌ Cannot sync notifications - not connected")
            return False

        try:
            from .config import SHEET_CONFIGS
            config = SHEET_CONFIGS["Notification Preferences"] 
            worksheet = self.get_or_create_worksheet("Notification Preferences", config["rows"], config["cols"])
            
            if not worksheet:
                return False

            # Clear and add headers
            worksheet.clear()
            worksheet.append_row(config["headers"])

            # Format header
            worksheet.format("A1:J1", {
                "backgroundColor": {"red": 0.6, "green": 0.2, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Add data
            users_data = notification_prefs.get("users", {}) if isinstance(notification_prefs, dict) else {}
            for i, (user_id, prefs) in enumerate(users_data.items()):
                # Rate limiting
                if i > 0 and i % 20 == 0:
                    time.sleep(2)

                try:
                    row_data = [
                        str(user_id),
                        prefs.get("display_name", f"User_{user_id}"),
                        prefs.get("method", "Discord DM"),
                        "Yes" if prefs.get("event_reminders", True) else "No",
                        "Yes" if prefs.get("result_notifications", True) else "No",
                        "Yes" if prefs.get("team_updates", True) else "No",
                        prefs.get("reminder_times", [60])[0] if prefs.get("reminder_times") else 60,
                        prefs.get("quiet_hours", {}).get("start", "22:00"),
                        prefs.get("quiet_hours", {}).get("end", "08:00"),
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    ]
                    worksheet.append_row(row_data)
                except Exception as e:
                    logger.warning(f"Failed to sync notification prefs for user {user_id}: {e}")
                    continue

            SheetsErrorHandler.log_sync_operation("Notification Preferences", True, len(users_data))
            return True

        except Exception as e:
            SheetsErrorHandler.log_sync_operation("Notification Preferences", False, error=str(e))
            return False

    def load_data_from_sheets(self):
        """Load all bot data from Google Sheets - primary data source."""
        if not self.is_connected():
            logger.warning("❌ Sheets not connected - cannot load data")
            return None

        try:
            data = {
                "events": {"main_team": [], "team_2": [], "team_3": []},
                "blocked": {},
                "results": {"total_wins": 0, "total_losses": 0, "history": []},
                "player_stats": {},
                "ign_map": {},
                "absent": {},
                "notification_preferences": {"users": {}, "default_settings": {}}
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
                logger.info("✅ Loaded current teams from sheets")
            except gspread.WorksheetNotFound:
                logger.info("⚠️ Current Teams sheet not found, using defaults")

            # Load Player Stats
            try:
                worksheet = self.spreadsheet.worksheet("Player Stats")
                rows = worksheet.get_all_records()
                for row in rows:
                    user_id = str(row.get("User ID", ""))
                    if user_id and user_id != "User ID":  # Skip header
                        data["player_stats"][user_id] = {
                            "name": row.get("Name", ""),
                            "display_name": row.get("Display Name", ""),
                            "has_main_role": row.get("Main Team Role", "No") == "Yes",
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
                            "power_rating": int(row.get("Power Rating", 0) or 0),
                            "absents": int(row.get("Absents", 0) or 0),
                            "blocked": row.get("Blocked", "No") == "Yes",
                            "specializations": {
                                "cavalry": row.get("Cavalry", "No") == "Yes",
                                "mages": row.get("Mages", "No") == "Yes",
                                "archers": row.get("Archers", "No") == "Yes",
                                "infantry": row.get("Infantry", "No") == "Yes",
                                "whale": row.get("Whale", "No") == "Yes"
                            }
                        }
                logger.info(f"✅ Loaded {len(data['player_stats'])} player stats from sheets")
            except gspread.WorksheetNotFound:
                logger.info("⚠️ Player Stats sheet not found, using defaults")

            # Load Results History
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
                rows = worksheet.get_all_records()
                for row in rows:
                    if row.get("Date") and row.get("Date") != "Date":  # Skip header
                        data["results"]["history"].append({
                            "date": row.get("Date"),
                            "team": row.get("Team", "").lower().replace(" ", "_"),
                            "result": row.get("Result", "").lower(),
                            "players": row.get("Players", "").split(",") if row.get("Players") else [],
                            "by": row.get("Recorded By", ""),
                            "timestamp": row.get("Date")
                        })

                # Calculate totals
                data["results"]["total_wins"] = sum(1 for r in data["results"]["history"] if r["result"] == "win")
                data["results"]["total_losses"] = sum(1 for r in data["results"]["history"] if r["result"] == "loss")
                logger.info(f"✅ Loaded {len(data['results']['history'])} results from sheets")

            except gspread.WorksheetNotFound:
                logger.info("⚠️ Results History sheet not found, using defaults")

            logger.info("✅ Successfully loaded all data from Google Sheets")
            return data

        except Exception as e:
            logger.error(f"❌ Failed to load data from sheets: {e}")
            return None

# sheets/worksheet_handlers.py
from datetime import datetime
from .base_manager import BaseSheetsManager
from .config import SHEET_CONFIGS, TEAM_MAPPING
from utils.logger import setup_logger

logger = setup_logger("worksheet_handlers")

class WorksheetHandlers(BaseSheetsManager):
    """Handles individual worksheet operations."""

    def sync_current_teams(self, events_data):
        """Sync current team signups to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Current Teams"]
            worksheet = self.get_or_create_worksheet("Current Teams", config["rows"], config["cols"])

            # Clear and add headers
            worksheet.clear()
            worksheet.append_row(config["headers"])

            # Add current data
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            for team_key, players in events_data.items():
                team_name = TEAM_MAPPING.get(team_key, team_key)
                player_list = ", ".join(str(p) for p in players) if players else ""
                status = "Active"

                row = [timestamp, team_name, len(players), player_list, status]
                worksheet.append_row(row)

            logger.info("✅ Synced current teams to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def create_player_stats_template(self, player_stats):
        """Create player stats template with current players for manual data entry."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Player Stats", 300, 21)

            # Correct headers that match our needs
            headers = [
                "User ID", "Display Name", "Main Team Role", 
                "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
                "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses", 
                "Win Rate", "Absents", "Blocked", "Power Rating", 
                "Cavalry", "Mages", "Archers", "Infantry", "Whale Status", "Last Updated"
            ]

            # Only create template if sheet is empty or has wrong headers
            existing_data = worksheet.get_all_values()
            if len(existing_data) <= 1 or (existing_data and existing_data[0] != headers):
                logger.info("Creating new player stats template with correct headers")

                # Clear and add correct headers
                worksheet.clear()
                worksheet.append_row(headers)

                # Add template rows for current players
                if player_stats:
                    row_num = 2  # Start from row 2 (after headers)
                    for user_id, stats in player_stats.items():
                        # Create properly aligned row
                        row = [
                            user_id,                                    # A: User ID
                            stats.get("name", "Unknown"),              # B: Display Name  
                            "No",                                       # C: Main Team Role (manual entry)
                            0,                                          # D: Main Wins (manual entry)
                            0,                                          # E: Main Losses (manual entry)
                            0,                                          # F: Team2 Wins (manual entry)
                            0,                                          # G: Team2 Losses (manual entry)
                            0,                                          # H: Team3 Wins (manual entry)
                            0,                                          # I: Team3 Losses (manual entry)
                            f"=D{row_num}+F{row_num}+H{row_num}",      # J: Total Wins (formula)
                            f"=E{row_num}+G{row_num}+I{row_num}",      # K: Total Losses (formula)
                            f"=IF(K{row_num}+J{row_num}=0,0,J{row_num}/(J{row_num}+K{row_num}))",  # L: Win Rate (formula)
                            0,                                          # M: Absents (manual entry)
                            "No",                                       # N: Blocked (manual entry)
                            "",                                         # O: Power Rating (manual entry)
                            "No",                                       # P: Cavalry (manual entry)
                            "No",                                       # Q: Mages (manual entry)
                            "No",                                       # R: Archers (manual entry)
                            "No",                                       # S: Infantry (manual entry)
                            "No",                                       # T: Whale Status (manual entry)
                            datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")  # U: Last Updated
                        ]
                        worksheet.append_row(row)
                        row_num += 1
                else:
                    # Add one example row if no player stats
                    example_row = [
                        "123456789012345678",                          # A: User ID
                        "Example Player",                              # B: Display Name
                        "Yes",                                         # C: Main Team Role
                        5,                                             # D: Main Wins
                        3,                                             # E: Main Losses
                        2,                                             # F: Team2 Wins
                        1,                                             # G: Team2 Losses
                        0,                                             # H: Team3 Wins
                        0,                                             # I: Team3 Losses
                        "=D2+F2+H2",                                  # J: Total Wins
                        "=E2+G2+I2",                                  # K: Total Losses
                        "=IF(K2+J2=0,0,J2/(J2+K2))",                 # L: Win Rate
                        1,                                             # M: Absents
                        "No",                                          # N: Blocked
                        "125000000",                                   # O: Power Rating
                        "Yes",                                         # P: Cavalry
                        "No",                                          # Q: Mages
                        "Yes",                                         # R: Archers
                        "No",                                          # S: Infantry
                        "Yes",                                         # T: Whale Status
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")  # U: Last Updated
                    ]
                    worksheet.append_row(example_row)

                # Format headers (bold, background color)
                try:
                    worksheet.format("A1:U1", {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
                    })

                    # Freeze header row
                    worksheet.freeze(rows=1)
                except Exception as format_error:
                    logger.warning(f"Failed to format headers: {format_error}")

                logger.info("✅ Created player stats template with correct alignment")
            else:
                logger.info("✅ Player stats sheet already has correct format")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create player stats template: {e}")
            return False

    def sync_results_history(self, results_data):
        """Sync detailed results history to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Results History"]
            worksheet = self.get_or_create_worksheet("Results History", config["rows"], config["cols"])

            worksheet.clear()
            worksheet.append_row(config["headers"])

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
                    TEAM_MAPPING.get(team, team.replace("_", " ").title()),
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
            logger.error(f"❌ Failed to sync results history: {e}")
            return False

    def load_player_stats_from_sheets(self):
        """Load player stats specifically from sheets."""
        if not self.is_connected():
            return {}

        try:
            worksheet = self.spreadsheet.worksheet("Player Stats")
            rows = worksheet.get_all_records()

            player_stats = {}
            for row in rows:
                user_id = str(row.get("User ID", ""))
                if user_id and user_id != "User ID":  # Skip header row
                    player_stats[user_id] = {
                        "name": row.get("Display Name", ""),
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
                        "blocked": str(row.get("Blocked", "No")).lower() in ["yes", "true", "1"],
                        "power_rating": int(row.get("Power Rating", 0) or 0),
                        "specializations": {
                            "cavalry": str(row.get("Cavalry", "No")).lower() in ["yes", "true", "1"],
                            "mages": str(row.get("Mages", "No")).lower() in ["yes", "true", "1"],
                            "archers": str(row.get("Archers", "No")).lower() in ["yes", "true", "1"],
                            "infantry": str(row.get("Infantry", "No")).lower() in ["yes", "true", "1"],
                            "whale": str(row.get("Whale Status", "No")).lower() in ["yes", "true", "1"]
                        }
                    }

            logger.info(f"✅ Loaded {len(player_stats)} player stats from sheets")
            return player_stats

        except Exception as e:
            logger.error(f"❌ Failed to load player stats from sheets: {e}")
            return {}
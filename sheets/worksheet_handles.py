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
            worksheet = self.get_or_create_worksheet("Current Teams", **SHEET_CONFIGS["Current Teams"])

            # Clear and add headers
            worksheet.clear()
            worksheet.append_row(SHEET_CONFIGS["Current Teams"]["headers"])

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
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])

            # Only create template if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                worksheet.clear()
                worksheet.append_row(config["headers"])

                # Add template rows for current players (empty data for manual entry)
                for user_id, stats in player_stats.items():
                    row = [
                        user_id,
                        stats.get("name", "Unknown"),
                        0, 0, 0, 0, 0, 0, 0, 0, 0,  # Win/loss stats - to be filled manually
                        "No",  # Blocked
                        "",    # Power Rating
                        "", "", "", "", ""  # Specializations
                    ]
                    worksheet.append_row(row)

                logger.info("✅ Created player stats template for manual entry")
            else:
                logger.info("✅ Player stats sheet already exists, skipping template creation")

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

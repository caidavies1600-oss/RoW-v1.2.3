from datetime import datetime
from .template_creator import TemplateCreator
from utils.logger import setup_logger

logger = setup_logger("data_sync")

class DataSync(TemplateCreator):
    """Handles data loading and syncing operations."""

    def load_data_from_sheets(self):
        """Load all bot data from Google Sheets - primary data source."""
        if not self.is_connected():
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
                            "blocked": row.get("Blocked", "No") == "Yes",
                            "power_rating": int(row.get("Power Rating", 0) or 0),
                            "specializations": {
                                "cavalry": row.get("Cavalry", "").lower() == "yes",
                                "mages": row.get("Mages", "").lower() == "yes",
                                "archers": row.get("Archers", "").lower() == "yes",
                                "infantry": row.get("Infantry", "").lower() == "yes",
                                "whale": row.get("Whale Status", "").lower() == "yes"
                            }
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
                            "team": row.get("Team", "").lower().replace(" ", "_"),
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
            logger.error(f"❌ Failed to load data from sheets: {e}")
            return None

    def sync_notification_preferences(self, notification_prefs):
        """Sync notification preferences to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Notification Preferences"]
            worksheet = self.get_or_create_worksheet("Notification Preferences", config["rows"], config["cols"])

            worksheet.clear()
            worksheet.append_row(config["headers"])

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
            logger.error(f"❌ Failed to sync notification preferences: {e}")
            return False

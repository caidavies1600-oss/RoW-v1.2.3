"""
Google Sheets operations for bot data syncing.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import gspread
from .client import SheetsClient
from .config import SHEET_CONFIGS, TEAM_MAPPING
from utils.logger import setup_logger

logger = setup_logger("sheets_operations")

class SheetsOperations(SheetsClient):
    """Handles all Google Sheets operations for the bot."""

    def __init__(self):
        super().__init__()
        self.initialized = self.initialize()

    # ==========================================
    # DATA SYNCHRONIZATION METHODS
    # ==========================================

    def sync_current_teams(self, events_data: Dict[str, List]) -> bool:
        """Sync current team signups to Google Sheets with batching."""
        if not self.is_connected():
            logger.warning("Cannot sync teams - sheets not connected")
            return False

        try:
            import time
            config = SHEET_CONFIGS["Current Teams"]
            worksheet = self.get_or_create_worksheet("Current Teams", config["rows"], config["cols"])
            if not worksheet:
                return False

            # Prepare all data first, then batch update
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            all_rows = [config["headers"]]  # Start with headers

            for team_key, players in events_data.items():
                team_name = TEAM_MAPPING.get(team_key, team_key)
                player_list = ", ".join(str(p) for p in players) if players else ""
                status = "Active" if players else "No signups"

                row = [timestamp, team_name, len(players), player_list, status]
                all_rows.append(row)

            # Single batch update instead of multiple append_row calls
            time.sleep(1)
            clear_result = self.safe_worksheet_operation(worksheet, worksheet.clear)
            if clear_result is None:
                return False

            time.sleep(1)
            # Use update() for batch operation instead of multiple append_row()
            range_name = f"A1:{chr(ord('A') + len(config['headers']) - 1)}{len(all_rows)}"
            batch_result = self.safe_worksheet_operation(worksheet, worksheet.update, range_name, all_rows)

            if batch_result is None:
                logger.error("Failed to batch update Current Teams")
                return False

            # Apply formatting in one operation
            time.sleep(1)
            try:
                worksheet.format("A1:E1", {
                    "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                    "horizontalAlignment": "CENTER"
                })
            except Exception as format_error:
                logger.warning(f"Current Teams formatting failed (non-critical): {format_error}")

            logger.info(f"✅ Batch synced current teams ({len(all_rows)-1} teams) to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def sync_player_stats(self, player_stats: Dict[str, Dict]) -> bool:
        """Sync player statistics to Google Sheets with efficient batching."""
        if not self.is_connected():
            return False

        try:
            import time
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])
            if not worksheet:
                return False

            # Prepare all data for batch update
            all_rows = [config["headers"]]  # Start with headers

            # Process players in chunks to avoid huge batches
            player_items = list(player_stats.items())
            chunk_size = 50  # Process 50 players at a time

            for chunk_start in range(0, len(player_items), chunk_size):
                chunk = player_items[chunk_start:chunk_start + chunk_size]

                for user_id, stats in chunk:
                    team_results = stats.get("team_results", {})
                    main_wins = team_results.get("main_team", {}).get("wins", 0)
                    main_losses = team_results.get("main_team", {}).get("losses", 0)
                    team2_wins = team_results.get("team_2", {}).get("wins", 0)
                    team2_losses = team_results.get("team_2", {}).get("losses", 0)
                    team3_wins = team_results.get("team_3", {}).get("wins", 0)
                    team3_losses = team_results.get("team_3", {}).get("losses", 0)

                    total_events = stats.get("total_events", 0)
                    last_active = stats.get("last_active", "Never")

                    row = [
                        user_id,
                        stats.get("name", "Unknown"),
                        stats.get("power_rating", "ENTER_POWER_RATING_HERE"),
                        main_wins, main_losses,
                        team2_wins, team2_losses,
                        team3_wins, team3_losses,
                        total_events,
                        last_active,
                        ""  # Notes column
                    ]
                    all_rows.append(row)

            # Single batch update for all data
            logger.info(f"Batch updating {len(all_rows)} rows to Player Stats...")

            time.sleep(1)
            clear_result = self.safe_worksheet_operation(worksheet, worksheet.clear)
            if clear_result is None:
                return False

            # Calculate range for batch update
            if len(all_rows) > 0:
                time.sleep(2)  # Longer delay for large updates
                num_cols = len(config["headers"])
                num_rows = len(all_rows)
                range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"

                batch_result = self.safe_worksheet_operation(worksheet, worksheet.update, range_name, all_rows)
                if batch_result is None:
                    logger.error("Failed to batch update Player Stats")
                    return False

                # Apply header formatting
                time.sleep(1)
                try:
                    header_range = f"A1:{chr(ord('A') + num_cols - 1)}1"
                    worksheet.format(header_range, {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    })
                except Exception as format_error:
                    logger.warning(f"Player Stats formatting failed (non-critical): {format_error}")

            logger.info(f"✅ Batch synced {len(all_rows)-1} players to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync player stats: {e}")
            return False

    def sync_match_results(self, results_data: Dict) -> bool:
        """Sync match results to Google Sheets with batching."""
        if not self.is_connected():
            return False

        try:
            import time
            config = SHEET_CONFIGS["Match Results"]
            worksheet = self.get_or_create_worksheet("Match Results", config["rows"], config["cols"])
            if not worksheet:
                return False

            # Prepare batch data
            all_rows = [config["headers"]]  # Start with headers

            # Add recent results from history (limit to last 100 to avoid huge batches)
            history = results_data.get("history", [])
            recent_history = history[-100:] if len(history) > 100 else history

            for result in recent_history:
                date = result.get("date", "Unknown")
                team = result.get("team", "Unknown")
                outcome = result.get("result", "Unknown")
                recorded_by = result.get("recorded_by", "Bot")

                row = [
                    date, team, outcome, 
                    "", "",  # Enemy alliance info (manual entry)
                    "", "",  # Power info (manual entry)
                    recorded_by, 
                    ""  # Notes (manual entry)
                ]
                all_rows.append(row)

            # Batch update instead of individual append operations
            time.sleep(1)
            clear_result = self.safe_worksheet_operation(worksheet, worksheet.clear)
            if clear_result is None:
                return False

            if len(all_rows) > 1:  # Only update if we have data beyond headers
                time.sleep(1)
                num_cols = len(config["headers"])
                num_rows = len(all_rows)
                range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"

                batch_result = self.safe_worksheet_operation(worksheet, worksheet.update, range_name, all_rows)
                if batch_result is None:
                    logger.error("Failed to batch update Match Results")
                    return False

                # Apply header formatting
                time.sleep(1)
                try:
                    header_range = f"A1:{chr(ord('A') + num_cols - 1)}1"
                    worksheet.format(header_range, {
                        "backgroundColor": {"red": 0.8, "green": 0.4, "blue": 0.2},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    })
                except Exception as format_error:
                    logger.warning(f"Match Results formatting failed (non-critical): {format_error}")

            logger.info(f"✅ Batch synced {len(all_rows)-1} match results to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync match results: {e}")
            return False

    # ==========================================
    # TEMPLATE CREATION METHODS
    # ==========================================

    def create_player_stats_template(self, player_stats: Dict) -> bool:
        """Create player stats template with current players for manual data entry using batch updates."""
        if not self.is_connected():
            return False

        try:
            import time
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])
            if not worksheet:
                logger.error("Failed to create/get Player Stats worksheet")
                return False

            # Prepare all data for batch update
            all_rows = [config["headers"]]  # Start with headers

            # Limit to first 100 players to avoid huge batches during template creation
            player_items = list(player_stats.items())[:100]

            logger.info(f"Creating Player Stats template with {len(player_items)} players...")

            # Add current players with placeholder data
            for user_id, stats in player_items:
                row = [
                    user_id,
                    stats.get("name", "Unknown Player"),
                    "ENTER_POWER_RATING_HERE",  # Manual entry placeholder
                    0, 0, 0, 0, 0, 0,  # Team stats start at 0
                    0,  # Total events
                    datetime.utcnow().strftime("%Y-%m-%d"),
                    "ENTER_NOTES_HERE"
                ]
                all_rows.append(row)

            # Single batch operation instead of multiple append_row calls
            time.sleep(1)
            clear_result = self.safe_worksheet_operation(worksheet, worksheet.clear)
            if clear_result is None:
                logger.error("Failed to clear Player Stats worksheet")
                return False

            # Batch update all data at once
            if len(all_rows) > 0:
                time.sleep(2)  # Longer delay for batch operations
                num_cols = len(config["headers"])
                num_rows = len(all_rows)
                range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"

                logger.info(f"Batch updating Player Stats range {range_name} with {num_rows} rows...")
                batch_result = self.safe_worksheet_operation(worksheet, worksheet.update, range_name, all_rows)
                if batch_result is None:
                    logger.error("Failed to batch update Player Stats")
                    return False

                logger.info(f"✅ Batch updated Player Stats with {len(all_rows)} rows")

            # Apply formatting in single operation
            time.sleep(1)
            try:
                header_range = f"A1:{chr(ord('A') + num_cols - 1)}1"
                worksheet.format(header_range, {
                    "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 12,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER"
                })
                logger.info("✅ Applied Player Stats header formatting")
            except Exception as format_error:
                logger.warning(f"Header formatting failed (non-critical): {format_error}")

            logger.info(f"✅ Created player stats template with {len(player_items)} players using batch operations")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create player stats template: {e}")
            return False

    def create_alliance_tracking_template(self) -> bool:
        """Create alliance tracking template for enemy alliance performance."""
        if not self.is_connected():
            return False

        try:
            import time
            config = SHEET_CONFIGS["Alliance Tracking"]
            worksheet = self.get_or_create_worksheet("Alliance Tracking", config["rows"], config["cols"])
            if not worksheet:
                logger.error("Failed to create/get Alliance Tracking worksheet")
                return False

            # Check if template already exists (but only check row count to avoid API calls)
            logger.info("Creating Alliance Tracking template...")

            # Always recreate for consistency
            time.sleep(1)
            clear_result = self.safe_worksheet_operation(worksheet, worksheet.clear)
            if clear_result is None:
                logger.error("Failed to clear Alliance Tracking worksheet")
                return False

            time.sleep(1)
            header_result = self.safe_worksheet_operation(worksheet, worksheet.append_row, config["headers"])
            if header_result is None:
                logger.error("Failed to add Alliance Tracking headers")
                return False

            logger.info(f"✅ Added Alliance Tracking headers: {config['headers']}")

            # Format headers
            time.sleep(1)
            try:
                worksheet.format("A1:N1", {
                    "backgroundColor": {"red": 0.8, "green": 0.3, "blue": 0.3},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 12,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER"
                })
                logger.info("✅ Applied Alliance Tracking header formatting")
            except Exception as format_error:
                logger.warning(f"Alliance tracking formatting failed (non-critical): {format_error}")

            # Add example row
            time.sleep(1)
            example_row = [
                "Example Alliance", "EX", 0, 0, 0, "0%", 0,
                "MEDIUM", "Enter strategy notes here", "Never", "K000",
                "ACTIVE", "MEDIUM", "Enter additional notes here"
            ]
            example_result = self.safe_worksheet_operation(worksheet, worksheet.append_row, example_row)
            if example_result is None:
                logger.warning("Failed to add example row (non-critical)")

            logger.info("✅ Created alliance tracking template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create alliance tracking template: {e}")
            return False

    def create_dashboard_template(self) -> bool:
        """Create dashboard template for overview data."""
        if not self.is_connected():
            return False

        try:
            import time
            config = SHEET_CONFIGS["Dashboard"]
            worksheet = self.get_or_create_worksheet("Dashboard", config["rows"], config["cols"])
            if not worksheet:
                logger.error("Failed to create/get Dashboard worksheet")
                return False

            logger.info("Creating Dashboard template...")

            # Create dashboard layout
            time.sleep(1)
            clear_result = self.safe_worksheet_operation(worksheet, worksheet.clear)
            if clear_result is None:
                logger.error("Failed to clear Dashboard worksheet")
                return False

            # Title and basic structure
            title_data = [
                ["RoW Bot Dashboard", "", "", ""],
                ["Last Updated:", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "", ""],
                ["", "", "", ""],
                ["Team Performance Summary", "", "", ""],
                ["Team", "Active Players", "Recent Wins", "Recent Losses"]
            ]

            for i, row in enumerate(title_data):
                time.sleep(0.3)  # Small delay between rows
                row_result = self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
                if row_result is None:
                    logger.warning(f"Failed to add dashboard row {i}")

            # Format the title
            time.sleep(1)
            try:
                worksheet.format("A1:D1", {
                    "backgroundColor": {"red": 0.1, "green": 0.5, "blue": 0.2},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 16,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER"
                })

                # Format the team performance header
                worksheet.format("A5:D5", {
                    "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER"
                })
                logger.info("✅ Applied Dashboard formatting")
            except Exception as format_error:
                logger.warning(f"Dashboard formatting failed (non-critical): {format_error}")

            # Add team performance placeholders
            team_data = [
                ["Main Team", 0, 0, 0],
                ["Team 2", 0, 0, 0],
                ["Team 3", 0, 0, 0]
            ]

            for row in team_data:
                time.sleep(0.3)
                row_result = self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
                if row_result is None:
                    logger.warning("Failed to add team performance row")

            logger.info("✅ Created dashboard template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create dashboard template: {e}")
            return False

    # ==========================================
    # DATA LOADING METHODS
    # ==========================================

    def load_data_from_sheets(self) -> Optional[Dict[str, Any]]:
        """Load all bot data from Google Sheets as primary source."""
        if not self.is_connected():
            logger.info("Sheets not connected, falling back to JSON files")
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

            # Load Current Teams if available
            try:
                worksheet = self.spreadsheet.worksheet("Current Teams")
                rows = self.safe_worksheet_operation(worksheet, worksheet.get_all_records)
                if rows:
                    for row in rows:
                        team = row.get("Team", "").lower().replace(" ", "_")
                        players = row.get("Players", "")
                        if team in data["events"] and players:
                            player_list = [p.strip() for p in players.split(",") if p.strip()]
                            data["events"][team] = player_list
            except gspread.WorksheetNotFound:
                logger.info("Current Teams sheet not found, using defaults")

            # Load Player Stats if available
            try:
                worksheet = self.spreadsheet.worksheet("Player Stats")
                rows = self.safe_worksheet_operation(worksheet, worksheet.get_all_records)
                if rows:
                    for row in rows:
                        user_id = str(row.get("User ID", ""))
                        if user_id and user_id != "ENTER_POWER_RATING_HERE":
                            data["player_stats"][user_id] = {
                                "name": row.get("Name", ""),
                                "power_rating": row.get("Power Rating", 0),
                                "team_results": {
                                    "main_team": {
                                        "wins": int(row.get("Main Team Wins", 0)),
                                        "losses": int(row.get("Main Team Losses", 0))
                                    },
                                    "team_2": {
                                        "wins": int(row.get("Team 2 Wins", 0)),
                                        "losses": int(row.get("Team 2 Losses", 0))
                                    },
                                    "team_3": {
                                        "wins": int(row.get("Team 3 Wins", 0)),
                                        "losses": int(row.get("Team 3 Losses", 0))
                                    }
                                },
                                "total_events": int(row.get("Total Events", 0)),
                                "last_active": row.get("Last Active", "Never")
                            }
            except gspread.WorksheetNotFound:
                logger.info("Player Stats sheet not found, using defaults")

            logger.info("✅ Successfully loaded data from Google Sheets")
            return data

        except Exception as e:
            logger.error(f"❌ Error loading data from Sheets: {e}")
            return None

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def create_all_templates(self, bot_data: Dict[str, Any]) -> Dict[str, bool]:
        """Create all sheet templates for manual data entry with detailed results."""
        if not self.is_connected():
            logger.error("Cannot create templates - sheets not connected")
            return {"connected": False}

        logger.info("🔄 Starting template creation process...")
        results = {"connected": True}

        import time

        # Create each template with delays between operations
        templates = [
            ("player_stats", lambda: self.create_player_stats_template(bot_data.get("player_stats", {}))),
            ("alliance_tracking", lambda: self.create_alliance_tracking_template()),
            ("dashboard", lambda: self.create_dashboard_template()),
            ("current_teams", lambda: self.sync_current_teams(bot_data.get("events", {})))
        ]

        for template_name, create_func in templates:
            try:
                logger.info(f"Creating {template_name} template...")
                time.sleep(2)  # 2 second delay between major operations

                success = create_func()
                results[template_name] = success

                if success:
                    logger.info(f"✅ {template_name} template created successfully")
                else:
                    logger.error(f"❌ {template_name} template creation failed")

            except Exception as e:
                logger.error(f"❌ Error creating {template_name} template: {e}")
                results[template_name] = False

        # Count successes
        success_count = sum(1 for k, v in results.items() if k != "connected" and v)
        total_count = len(templates)

        logger.info(f"📊 Template creation complete: {success_count}/{total_count} successful")
        results["summary"] = {"success_count": success_count, "total_count": total_count}

        return results

    def get_spreadsheet_url(self) -> Optional[str]:
        """Get the URL of the connected spreadsheet."""
        if self.is_connected() and self.spreadsheet:
            return self.spreadsheet.url
        return None

    def get_worksheet_list(self) -> List[str]:
        """Get list of available worksheet names."""
        if not self.is_connected():
            return []

        try:
            worksheets = self.spreadsheet.worksheets()
            return [ws.title for ws in worksheets]
        except Exception as e:
            logger.error(f"Error getting worksheet list: {e}")
            return []
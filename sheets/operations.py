"""
Google Sheets operations for bot data syncing - FIXED VERSION.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import gspread
import time
from .client import SheetsClient
from .config import SHEET_CONFIGS, TEAM_MAPPING
from utils.logger import setup_logger

logger = setup_logger("sheets_operations")

class SheetsOperations(SheetsClient):
    """Handles all Google Sheets operations for the bot."""

    def __init__(self):
        super().__init__()
        self.initialized = self.initialize()

    def _safe_batch_operation(self, worksheet, operation_name: str, operation_func, *args, **kwargs):
        """Execute batch operations with enhanced error handling and rate limiting."""
        if not worksheet:
            logger.error(f"Cannot perform {operation_name} - worksheet is None")
            return False

        try:
            logger.info(f"Starting {operation_name}...")
            time.sleep(2)  # Rate limiting

            result = operation_func(*args, **kwargs)

            if result is None:
                logger.error(f"❌ {operation_name} returned None (likely failed)")
                return False

            logger.info(f"✅ {operation_name} completed successfully")
            return True

        except gspread.exceptions.APIError as e:
            logger.error(f"❌ Google Sheets API error in {operation_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error in {operation_name}: {e}")
            return False

    def _freeze_header_row(self, worksheet, num_rows: int = 1):
        """Freeze the top row(s) of a worksheet."""
        try:
            # Use batch_update to freeze rows
            requests = [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": worksheet.id,
                        "gridProperties": {
                            "frozenRowCount": num_rows
                        }
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            }]

            self.spreadsheet.batch_update({"requests": requests})
            logger.info(f"✅ Froze {num_rows} header row(s) in {worksheet.title}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Could not freeze rows in {worksheet.title}: {e}")
            return False

    def _apply_header_formatting(self, worksheet, num_cols: int, color_scheme: str = "blue"):
        """Apply consistent header formatting with freezing."""
        try:
            # Color schemes
            colors = {
                "blue": {"red": 0.2, "green": 0.6, "blue": 1.0},
                "orange": {"red": 0.8, "green": 0.4, "blue": 0.2},
                "red": {"red": 0.8, "green": 0.3, "blue": 0.3},
                "green": {"red": 0.1, "green": 0.5, "blue": 0.2}
            }

            bg_color = colors.get(color_scheme, colors["blue"])
            header_range = f"A1:{chr(ord('A') + num_cols - 1)}1"

            # Apply formatting
            worksheet.format(header_range, {
                "backgroundColor": bg_color,
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze the header row
            self._freeze_header_row(worksheet, 1)

            logger.info(f"✅ Applied {color_scheme} header formatting to {header_range}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Header formatting failed (non-critical): {e}")
            return False

    # ==========================================
    # DATA SYNCHRONIZATION METHODS - FIXED
    # ==========================================

    def sync_current_teams(self, events_data: Dict[str, List]) -> bool:
        """Sync current team signups to Google Sheets with improved batching."""
        if not self.is_connected():
            logger.warning("Cannot sync teams - sheets not connected")
            return False

        try:
            config = SHEET_CONFIGS["Current Teams"]
            worksheet = self.get_or_create_worksheet("Current Teams", config["rows"], config["cols"])
            if not worksheet:
                logger.error("Failed to get/create Current Teams worksheet")
                return False

            # Prepare batch data
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            all_rows = [config["headers"]]  # Start with headers

            for team_key, players in events_data.items():
                team_name = TEAM_MAPPING.get(team_key, team_key)
                player_list = ", ".join(str(p) for p in players) if players else ""
                status = "Active" if players else "No signups"

                row = [timestamp, team_name, len(players), player_list, status]
                all_rows.append(row)

            # Clear and update in separate operations
            if not self._safe_batch_operation(worksheet, "clear Current Teams", worksheet.clear):
                return False

            # Calculate range and update
            num_cols = len(config["headers"])
            num_rows = len(all_rows)
            range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"

            if not self._safe_batch_operation(worksheet, f"batch update Current Teams ({range_name})", 
                                            worksheet.update, range_name, all_rows):
                return False

            # Apply formatting with freezing
            time.sleep(1)
            self._apply_header_formatting(worksheet, num_cols, "blue")

            logger.info(f"✅ Successfully synced {len(all_rows)-1} teams to Current Teams")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def sync_player_stats(self, player_stats: Dict[str, Dict]) -> bool:
        """Sync player statistics with chunked processing and improved error handling."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])
            if not worksheet:
                return False

            # Process in smaller chunks to avoid API limits
            chunk_size = 25  # Reduced chunk size
            player_items = list(player_stats.items())

            logger.info(f"Processing {len(player_items)} players in chunks of {chunk_size}")

            # Clear worksheet first
            if not self._safe_batch_operation(worksheet, "clear Player Stats", worksheet.clear):
                return False

            # Add headers first
            if not self._safe_batch_operation(worksheet, "add Player Stats headers", 
                                            worksheet.append_row, config["headers"]):
                return False

            # Process players in chunks
            for chunk_start in range(0, len(player_items), chunk_size):
                chunk = player_items[chunk_start:chunk_start + chunk_size]
                chunk_rows = []

                for user_id, stats in chunk:
                    team_results = stats.get("team_results", {})
                    main_wins = team_results.get("main_team", {}).get("wins", 0)
                    main_losses = team_results.get("main_team", {}).get("losses", 0)
                    team2_wins = team_results.get("team_2", {}).get("wins", 0)
                    team2_losses = team_results.get("team_2", {}).get("losses", 0)
                    team3_wins = team_results.get("team_3", {}).get("wins", 0)
                    team3_losses = team_results.get("team_3", {}).get("losses", 0)

                    row = [
                        user_id,
                        stats.get("name", "Unknown"),
                        stats.get("power_rating", "ENTER_POWER_HERE"),
                        main_wins, main_losses,
                        team2_wins, team2_losses,
                        team3_wins, team3_losses,
                        stats.get("total_events", 0),
                        stats.get("last_active", "Never"),
                        ""  # Notes column
                    ]
                    chunk_rows.append(row)

                # Add chunk to worksheet
                if chunk_rows:
                    try:
                        time.sleep(3)  # Longer delay between chunks
                        for row in chunk_rows:
                            result = self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
                            if result is None:
                                logger.warning(f"Failed to add player row: {row[1]}")
                            time.sleep(0.5)  # Small delay between rows

                        logger.info(f"✅ Added chunk {chunk_start//chunk_size + 1}: {len(chunk_rows)} players")
                    except Exception as e:
                        logger.error(f"❌ Failed to add player chunk: {e}")
                        return False

            # Apply formatting with freezing
            time.sleep(2)
            self._apply_header_formatting(worksheet, len(config["headers"]), "blue")

            logger.info(f"✅ Successfully synced {len(player_items)} players to Player Stats")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync player stats: {e}")
            return False

    def sync_match_results(self, results_data: Dict) -> bool:
        """Sync match results with improved batching."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Match Results"]
            worksheet = self.get_or_create_worksheet("Match Results", config["rows"], config["cols"])
            if not worksheet:
                return False

            # Prepare data - limit to recent results
            all_rows = [config["headers"]]
            history = results_data.get("history", [])
            recent_history = history[-50:] if len(history) > 50 else history  # Reduced limit

            for result in recent_history:
                date = result.get("date", result.get("timestamp", "Unknown"))
                team = result.get("team", "Unknown")
                outcome = result.get("result", "Unknown")
                recorded_by = result.get("recorded_by", result.get("by", "Bot"))

                row = [
                    date, team, outcome,
                    "", "",  # Enemy alliance info (manual entry)
                    "", "",  # Power info (manual entry)
                    recorded_by,
                    ""  # Notes (manual entry)
                ]
                all_rows.append(row)

            # Clear and batch update
            if not self._safe_batch_operation(worksheet, "clear Match Results", worksheet.clear):
                return False

            if len(all_rows) > 1:
                num_cols = len(config["headers"])
                num_rows = len(all_rows)
                range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"

                if not self._safe_batch_operation(worksheet, f"update Match Results ({range_name})",
                                                worksheet.update, range_name, all_rows):
                    return False

            # Apply formatting
            time.sleep(1)
            self._apply_header_formatting(worksheet, len(config["headers"]), "orange")

            logger.info(f"✅ Successfully synced {len(all_rows)-1} match results")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync match results: {e}")
            return False

    # ==========================================
    # TEMPLATE CREATION METHODS - FIXED
    # ==========================================

    def create_player_stats_template(self, player_stats: Dict) -> bool:
        """Create player stats template with better error handling and freezing."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])
            if not worksheet:
                logger.error("Failed to create/get Player Stats worksheet")
                return False

            logger.info("Creating Player Stats template...")

            # Clear worksheet first
            if not self._safe_batch_operation(worksheet, "clear Player Stats template", worksheet.clear):
                return False

            # Add headers
            if not self._safe_batch_operation(worksheet, "add Player Stats template headers",
                                            worksheet.append_row, config["headers"]):
                return False

            # Add limited number of players to avoid quota issues
            player_items = list(player_stats.items())[:50]  # Limit to 50 players for template

            logger.info(f"Adding {len(player_items)} players to template...")

            # Add players one by one with delays
            for i, (user_id, stats) in enumerate(player_items):
                row = [
                    user_id,
                    stats.get("name", "Unknown Player"),
                    "ENTER_POWER_HERE",  # Manual entry placeholder
                    0, 0, 0, 0, 0, 0,  # Team stats start at 0
                    0,  # Total events
                    datetime.utcnow().strftime("%Y-%m-%d"),
                    "ENTER_NOTES_HERE"
                ]

                time.sleep(0.8)  # Delay between rows
                result = self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
                if result is None:
                    logger.warning(f"Failed to add player {stats.get('name', 'Unknown')}")

                # Progress update every 10 players
                if (i + 1) % 10 == 0:
                    logger.info(f"Added {i + 1}/{len(player_items)} players...")

            # Apply formatting with freezing
            time.sleep(2)
            self._apply_header_formatting(worksheet, len(config["headers"]), "blue")

            logger.info(f"✅ Created player stats template with {len(player_items)} players")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create player stats template: {e}")
            return False

    def create_alliance_tracking_template(self) -> bool:
        """Create alliance tracking template with freezing."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Alliance Tracking"]
            worksheet = self.get_or_create_worksheet("Alliance Tracking", config["rows"], config["cols"])
            if not worksheet:
                return False

            logger.info("Creating Alliance Tracking template...")

            # Clear and add headers
            if not self._safe_batch_operation(worksheet, "clear Alliance Tracking", worksheet.clear):
                return False

            if not self._safe_batch_operation(worksheet, "add Alliance headers",
                                            worksheet.append_row, config["headers"]):
                return False

            # Add example rows
            example_rows = [
                ["Example Alliance", "EX", 0, 0, 0, "0%", 0,
                 "MEDIUM", "Enter strategy notes here", "Never", "K000",
                 "ACTIVE", "MEDIUM", "Enter additional notes here"],
                ["", "", "", "", "", "", "",
                 "", "", "", "",
                 "", "", ""],  # Empty row for user entry
            ]

            for i, row in enumerate(example_rows):
                time.sleep(1)
                result = self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
                if result is None:
                    logger.warning(f"Failed to add example row {i}")

            # Apply formatting with freezing
            time.sleep(1)
            self._apply_header_formatting(worksheet, len(config["headers"]), "red")

            logger.info("✅ Created alliance tracking template with header freezing")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create alliance tracking template: {e}")
            return False

    def create_dashboard_template(self) -> bool:
        """Create dashboard template with proper structure and freezing."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Dashboard"]
            worksheet = self.get_or_create_worksheet("Dashboard", config["rows"], config["cols"])
            if not worksheet:
                return False

            logger.info("Creating Dashboard template...")

            # Clear worksheet
            if not self._safe_batch_operation(worksheet, "clear Dashboard", worksheet.clear):
                return False

            # Create dashboard structure
            dashboard_data = [
                ["RoW Bot Dashboard", "", "", ""],
                ["Last Updated:", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "", ""],
                ["", "", "", ""],
                ["Team Performance Summary", "", "", ""],
                ["Team", "Active Players", "Recent Wins", "Recent Losses"],
                ["Main Team", 0, 0, 0],
                ["Team 2", 0, 0, 0],
                ["Team 3", 0, 0, 0],
                ["", "", "", ""],
                ["Overall Statistics", "", "", ""],
                ["Metric", "Value", "Trend", "Notes"],
                ["Total Events", 0, "→", "Manual count"],
                ["Total Players", 0, "→", "Manual count"],
                ["Win Rate", "0%", "→", "Manual calculation"]
            ]

            # Add all rows
            for i, row in enumerate(dashboard_data):
                time.sleep(0.5)
                result = self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
                if result is None:
                    logger.warning(f"Failed to add dashboard row {i}")

            # Apply multiple formatting sections
            time.sleep(2)
            try:
                # Title formatting
                worksheet.format("A1:D1", {
                    "backgroundColor": {"red": 0.1, "green": 0.5, "blue": 0.2},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 16,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER"
                })

                # Team performance header
                worksheet.format("A5:D5", {
                    "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER"
                })

                # Statistics header
                worksheet.format("A11:D11", {
                    "backgroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6},
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER"
                })

                # Freeze title rows
                self._freeze_header_row(worksheet, 2)

                logger.info("✅ Applied Dashboard formatting with frozen rows")
            except Exception as format_error:
                logger.warning(f"Dashboard formatting failed: {format_error}")

            logger.info("✅ Created dashboard template with frozen header rows")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create dashboard template: {e}")
            return False

    # ==========================================
    # DATA LOADING METHODS
    # ==========================================

    def load_data_from_sheets(self) -> Optional[Dict[str, Any]]:
        """
        Load all bot data from Google Sheets.

        Returns:
            Dictionary containing bot data, or None if loading failed
        """
        if not self.is_connected():
            logger.warning("Cannot load data - sheets not connected")
            return None

        try:
            logger.info("🔍 Loading data from Google Sheets...")
            
            # Initialize data structure
            bot_data = {
                "events": {"main_team": [], "team_2": [], "team_3": []},
                "player_stats": {},
                "results": {"total_wins": 0, "total_losses": 0, "history": []},
                "blocked": {},
                "ign_map": {},
                "absent": {},
                "notification_preferences": {"users": {}, "default_settings": {}},
                "events_history": {"history": []}
            }

            # Try to load from each sheet
            self._load_current_teams_data(bot_data)
            self._load_player_stats_data(bot_data)
            self._load_results_data(bot_data)

            logger.info("✅ Successfully loaded data from Google Sheets")
            return bot_data

        except Exception as e:
            logger.error(f"❌ Failed to load data from sheets: {e}")
            return None

    def _load_current_teams_data(self, bot_data: Dict[str, Any]):
        """Load current teams data from sheets."""
        try:
            worksheet = self.get_or_create_worksheet("Current Teams", 50, 10)
            if not worksheet:
                return

            data = self.safe_worksheet_operation(worksheet, worksheet.get_all_values)
            if not data or len(data) < 2:  # Need at least headers + 1 row
                return

            # Parse team data (skip header row)
            for row in data[1:]:
                if len(row) >= 4:
                    team_name = row[1].strip()
                    players_str = row[3].strip()
                    
                    if players_str and players_str != "":
                        players = [p.strip() for p in players_str.split(",")]
                        
                        # Map team names back to keys
                        if "Main" in team_name:
                            bot_data["events"]["main_team"] = players
                        elif "Team 2" in team_name:
                            bot_data["events"]["team_2"] = players
                        elif "Team 3" in team_name:
                            bot_data["events"]["team_3"] = players

            logger.info("✅ Loaded current teams data from sheets")

        except Exception as e:
            logger.warning(f"Could not load current teams data: {e}")

    def _load_player_stats_data(self, bot_data: Dict[str, Any]):
        """Load player stats data from sheets."""
        try:
            worksheet = self.get_or_create_worksheet("Player Stats", 200, 15)
            if not worksheet:
                return

            data = self.safe_worksheet_operation(worksheet, worksheet.get_all_values)
            if not data or len(data) < 2:
                return

            # Parse player stats (skip header row)
            for row in data[1:]:
                if len(row) >= 12:
                    user_id = row[0].strip()
                    if not user_id or user_id == "":
                        continue

                    bot_data["player_stats"][user_id] = {
                        "name": row[1].strip() if len(row) > 1 else "Unknown",
                        "power_rating": row[2] if len(row) > 2 and row[2] != "ENTER_POWER_HERE" else 0,
                        "team_results": {
                            "main_team": {
                                "wins": int(row[3]) if len(row) > 3 and row[3].isdigit() else 0,
                                "losses": int(row[4]) if len(row) > 4 and row[4].isdigit() else 0
                            },
                            "team_2": {
                                "wins": int(row[5]) if len(row) > 5 and row[5].isdigit() else 0,
                                "losses": int(row[6]) if len(row) > 6 and row[6].isdigit() else 0
                            },
                            "team_3": {
                                "wins": int(row[7]) if len(row) > 7 and row[7].isdigit() else 0,
                                "losses": int(row[8]) if len(row) > 8 and row[8].isdigit() else 0
                            }
                        },
                        "total_events": int(row[9]) if len(row) > 9 and row[9].isdigit() else 0,
                        "last_active": row[10] if len(row) > 10 else "Never",
                        "specializations": {
                            "cavalry": False,
                            "mages": False,
                            "archers": False,
                            "infantry": False,
                            "whale": False
                        },
                        "absents": 0,
                        "blocked": False
                    }

            logger.info(f"✅ Loaded {len(bot_data['player_stats'])} player stats from sheets")

        except Exception as e:
            logger.warning(f"Could not load player stats data: {e}")

    def _load_results_data(self, bot_data: Dict[str, Any]):
        """Load results data from sheets."""
        try:
            worksheet = self.get_or_create_worksheet("Match Results", 200, 10)
            if not worksheet:
                return

            data = self.safe_worksheet_operation(worksheet, worksheet.get_all_values)
            if not data or len(data) < 2:
                return

            # Parse results data (skip header row)
            wins = 0
            losses = 0
            history = []

            for row in data[1:]:
                if len(row) >= 3:
                    result = {
                        "date": row[0] if len(row) > 0 else "",
                        "team": row[1] if len(row) > 1 else "",
                        "result": row[2] if len(row) > 2 else "",
                        "recorded_by": row[7] if len(row) > 7 else "Unknown"
                    }
                    
                    if "win" in result["result"].lower():
                        wins += 1
                    elif "loss" in result["result"].lower():
                        losses += 1
                    
                    history.append(result)

            bot_data["results"] = {
                "total_wins": wins,
                "total_losses": losses,
                "history": history
            }

            logger.info(f"✅ Loaded {len(history)} match results from sheets")

        except Exception as e:
            logger.warning(f"Could not load results data: {e}")

    # ==========================================
    # ENHANCED UTILITY METHODS
    # ==========================================

    def create_all_templates(self, bot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create all templates with enhanced error handling and progress tracking."""
        if not self.is_connected():
            return {"connected": False, "error": "Sheets not connected"}

        logger.info("🔄 Starting comprehensive template creation...")
        results = {"connected": True, "start_time": datetime.utcnow().isoformat()}

        templates = [
            ("current_teams", "Current Teams", 
             lambda: self.sync_current_teams(bot_data.get("events", {}))),
            ("player_stats", "Player Stats (all Discord members)", 
             lambda: self.create_player_stats_template(bot_data.get("player_stats", {}))),
            ("results_history", "Results History", 
             lambda: self.create_results_history_template(bot_data.get("results", {}))),
            ("match_statistics", "Match Statistics", 
             lambda: self.create_match_statistics_template()),
            ("alliance_tracking", "Alliance Tracking", 
             lambda: self.create_alliance_tracking_template()),
            ("dashboard", "Dashboard", 
             lambda: self.create_dashboard_template()),
            ("notification_preferences", "Notification Preferences", 
             lambda: self.create_notification_preferences_template()),
            ("error_summary", "Error Summary", 
             lambda: self.create_error_summary_template())
        ]

        for template_key, template_name, create_func in templates:
            try:
                logger.info(f"📋 Creating {template_name}...")
                start_time = time.time()

                # Longer delay between major template operations
                time.sleep(5)

                success = create_func()
                duration = time.time() - start_time

                results[template_key] = {
                    "success": success,
                    "duration_seconds": round(duration, 2),
                    "name": template_name
                }

                if success:
                    logger.info(f"✅ {template_name} created in {duration:.1f}s")
                else:
                    logger.error(f"❌ {template_name} creation failed")

            except Exception as e:
                logger.error(f"❌ Error creating {template_name}: {e}")
                results[template_key] = {
                    "success": False,
                    "error": str(e),
                    "name": template_name
                }

        # Calculate summary
        successes = sum(1 for k, v in results.items() 
                       if isinstance(v, dict) and v.get("success"))
        total = len(templates)

        results["summary"] = {
            "successful": successes,
            "total": total,
            "success_rate": f"{(successes/total)*100:.1f}%",
            "spreadsheet_url": self.get_spreadsheet_url()
        }

        logger.info(f"Template creation completed: {successes}/{total} successful")
        return results

    def create_match_statistics_template(self) -> bool:
        """Create match statistics template."""
        if not self.is_connected():
            return False

        try:
            # Create worksheet
            worksheet = self.get_or_create_worksheet("Match Statistics", 150, 10)
            if not worksheet:
                return False

            logger.info("Creating Match Statistics template...")

            # Clear worksheet first
            if not self._safe_batch_operation(worksheet, "clear Match Statistics", worksheet.clear):
                return False

            # Headers
            headers = ["📅 Date", "⚔️ Match Type", "👥 Our Team", "🏆 Result", "💪 Our Power", "🏰 Enemy Alliance", "⚡ Enemy Power", "📊 Power Difference", "🎯 Strategy Used", "📝 Notes"]
            
            if not self._safe_batch_operation(worksheet, "add Match Statistics headers",
                                            worksheet.append_row, headers):
                return False

            # Add sample data
            sample_matches = [
                [datetime.utcnow().strftime("%Y-%m-%d"), "Alliance War", "Main Team", "Win", "500M", "Enemy Alliance", "450M", "+50M", "Cavalry Rush", "Great coordination"],
                [datetime.utcnow().strftime("%Y-%m-%d"), "Alliance War", "Team 2", "Loss", "300M", "Strong Enemy", "400M", "-100M", "Defensive", "Need more power"],
            ]

            for i, match_data in enumerate(sample_matches):
                time.sleep(1)
                result = self.safe_worksheet_operation(worksheet, worksheet.append_row, match_data)
                if result is None:
                    logger.warning(f"Failed to add sample match {i}")

            # Apply formatting
            time.sleep(1)
            self._apply_header_formatting(worksheet, len(headers), "orange")

            logger.info("✅ Created Match Statistics template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create match statistics template: {e}")
            return False

    def create_error_summary_template(self) -> bool:
        """Create error summary template."""
        if not self.is_connected():
            return False

        try:
            # Create worksheet
            worksheet = self.get_or_create_worksheet("Error Summary", 100, 8)
            if not worksheet:
                return False

            logger.info("Creating Error Summary template...")

            # Clear worksheet first
            if not self._safe_batch_operation(worksheet, "clear Error Summary", worksheet.clear):
                return False

            # Headers
            headers = ["🕐 Timestamp", "⚠️ Error Type", "📍 Source", "💬 Message", "👤 User ID", "🔧 Status", "✅ Resolved", "📝 Notes"]
            
            if not self._safe_batch_operation(worksheet, "add Error Summary headers",
                                            worksheet.append_row, headers):
                return False

            # Add sample error
            sample_error = [datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "API Error", "Sheets Sync", "Rate limit exceeded", "Bot", "Resolved", "✅", "Implemented retry logic"]
            
            time.sleep(1)
            result = self.safe_worksheet_operation(worksheet, worksheet.append_row, sample_error)
            if result is None:
                logger.warning("Failed to add sample error")

            # Apply formatting
            time.sleep(1)
            self._apply_header_formatting(worksheet, len(headers), "red")

            logger.info("✅ Created Error Summary template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create error summary template: {e}")
            return False

    def create_results_history_template(self, results_data: Dict = None) -> bool:
        """Create Results History sheet template."""
        if not self.is_connected():
            return False

        try:
            # Create worksheet
            worksheet = self.get_or_create_worksheet("Results History", 200, 8)
            if not worksheet:
                return False

            logger.info("Creating Results History template...")

            # Clear worksheet first
            if not self._safe_batch_operation(worksheet, "clear Results History", worksheet.clear):
                return False

            # Headers with emojis
            headers = ["📅 Date", "👥 Team", "🎯 Result", "🎮 Players", "👤 Recorded By", "🏆 Match Score", "📊 Running Total", "💪 Performance"]
            
            if not self._safe_batch_operation(worksheet, "add Results History headers",
                                            worksheet.append_row, headers):
                return False

            # Add sample data
            sample_results = [
                ["2025-01-15", "Main Team", "Win", "Player1,Player2,Player3", "Admin", "🏆 WIN", "1W - 0L", "🔥 Great start!"],
                ["2025-01-14", "Team 2", "Loss", "Player4,Player5,Player6", "Admin", "❌ LOSS", "0W - 1L", "💪 Next time!"],
                ["2025-01-13", "Team 3", "Win", "Player7,Player8,Player9", "Admin", "🏆 WIN", "1W - 0L", "🎯 Excellent!"]
            ]

            for i, result_data in enumerate(sample_results):
                time.sleep(1)
                result = self.safe_worksheet_operation(worksheet, worksheet.append_row, result_data)
                if result is None:
                    logger.warning(f"Failed to add sample result {i}")

            # Apply formatting
            time.sleep(1)
            self._apply_header_formatting(worksheet, len(headers), "blue")

            logger.info("✅ Created Results History template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create results history template: {e}")
            return False

    def create_notification_preferences_template(self, notification_data: Dict = None) -> bool:
        """Create Notification Preferences sheet template."""
        if not self.is_connected():
            return False

        try:
            # Create worksheet
            worksheet = self.get_or_create_worksheet("Notification Preferences", 100, 9)
            if not worksheet:
                return False

            logger.info("Creating Notification Preferences template...")

            # Clear worksheet first
            if not self._safe_batch_operation(worksheet, "clear Notification Preferences", worksheet.clear):
                return False

            # Headers
            headers = ["👤 User ID", "📝 Display Name", "📢 Event Alerts", "🏆 Result Notifications", "⚠️ Error Alerts", "📱 DM Notifications", "🕐 Reminder Time", "🌍 Timezone", "📅 Last Updated"]
            
            if not self._safe_batch_operation(worksheet, "add Notification Preferences headers",
                                            worksheet.append_row, headers):
                return False

            # Add sample notification preferences
            sample_preferences = [
                ["123456789", "TestUser1", "✅ Enabled", "✅ Enabled", "❌ Disabled", "✅ Enabled", "30 minutes", "UTC-5", datetime.utcnow().strftime("%Y-%m-%d")],
                ["987654321", "TestUser2", "✅ Enabled", "❌ Disabled", "✅ Enabled", "❌ Disabled", "1 hour", "UTC+0", datetime.utcnow().strftime("%Y-%m-%d")],
            ]

            for i, pref_data in enumerate(sample_preferences):
                time.sleep(1)
                result = self.safe_worksheet_operation(worksheet, worksheet.append_row, pref_data)
                if result is None:
                    logger.warning(f"Failed to add sample preference {i}")

            # Apply formatting
            time.sleep(1)
            self._apply_header_formatting(worksheet, len(headers), "green")

            logger.info("✅ Created Notification Preferences template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create notification preferences template: {e}")
            return False
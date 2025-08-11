"""
Worksheet management module for Google Sheets integration.

This module provides:
- Individual worksheet operations
- Team roster synchronization
- Player statistics management
- Results history tracking
- Data loading and validation
"""

from datetime import datetime
from typing import Dict, Any, List

from utils.logger import setup_logger

from .base_manager import RateLimitedSheetsManager
try:
    from .config import SHEET_CONFIGS, TEAM_MAPPING
except ImportError:
    # Fallback configurations if not available in config
    SHEET_CONFIGS = {
        "Current Teams": {
            "rows": 50,
            "cols": 8, 
            "headers": ["🕐 Timestamp", "⚔️ Team", "👥 Player Count", "📝 Players", "📊 Status"]
        },
        "Results History": {
            "rows": 200,
            "cols": 8,
            "headers": ["📅 Date", "⚔️ Team", "🏆 Result", "👥 Players", "📝 Recorded By", "📊 Total Wins", "📊 Total Losses"]
        }
    }
    TEAM_MAPPING = {
        "main_team": "🏆 Main Team",
        "team_2": "🥈 Team 2",
        "team_3": "🥉 Team 3"
    }

logger = setup_logger("worksheet_handlers")


class WorksheetHandlers(RateLimitedSheetsManager):
    """
    Handles individual worksheet operations and data management.

    Features:
    - Worksheet creation and updates
    - Data synchronization
    - Template management
    - Error handling and logging
    - Data validation and formatting
    """

    def sync_current_teams(self, events_data):
        """
        Sync current team signups to Google Sheets.

        Args:
            events_data: Dictionary containing team rosters

        Features:
        - Team roster updates
        - Timestamp tracking
        - Player list formatting
        - Status indicators

        Returns:
            bool: Success status of sync operation
        """
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Current Teams"]
            worksheet = self.get_or_create_worksheet(
                "Current Teams", config["rows"], config["cols"]
            )

            # Clear and add headers
            self.rate_limited_request(worksheet.clear)
            self.rate_limited_request(worksheet.append_row, config["headers"])

            # Add current data
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            for team_key, players in events_data.items():
                team_name = TEAM_MAPPING.get(team_key, team_key)
                player_list = ", ".join(str(p) for p in players) if players else ""
                status = "Active"

                row = [timestamp, team_name, len(players), player_list, status]
                self.rate_limited_request(worksheet.append_row, row)

            logger.info("✅ Synced current teams to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def create_player_stats_template(self, player_stats: Dict[str, Any]) -> bool:
        """Create player stats template with current players."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Player Stats", 300, 21)
            if not worksheet:
                return False

            headers = [
                "User ID", "Display Name", "Main Team Role", "Main Wins", "Main Losses",
                "Team2 Wins", "Team2 Losses", "Team3 Wins", "Team3 Losses",
                "Total Wins", "Total Losses", "Win Rate", "Absents", "Blocked",
                "Power Rating", "Cavalry", "Mages", "Archers", "Infantry",
                "Whale Status", "Last Updated"
            ]

            # Clear and set headers
            self.rate_limited_request(worksheet.clear)
            self.rate_limited_request(worksheet.append_row, headers)

            # Add template rows for current players
            if player_stats:
                row_num = 2
                for user_id, stats in player_stats.items():
                    row = [
                        user_id,
                        stats.get("name", stats.get("display_name", f"User_{user_id}")),
                        "No",  # Manual entry required
                        0, 0, 0, 0, 0, 0,  # Win/Loss stats - manual entry
                        f"=D{row_num}+F{row_num}+H{row_num}",  # Total Wins formula
                        f"=E{row_num}+G{row_num}+I{row_num}",  # Total Losses formula
                        f"=IF(K{row_num}+J{row_num}=0,0,J{row_num}/(J{row_num}+K{row_num}))",  # Win Rate
                        stats.get("absents", 0),
                        "Yes" if stats.get("blocked", False) else "No",
                        "",  # Power rating - manual entry
                        "No", "No", "No", "No", "No",  # Specializations - manual entry
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                    ]
                    self.rate_limited_request(worksheet.append_row, row)
                    row_num += 1

            # Apply formatting
            self._apply_player_stats_formatting(worksheet, len(player_stats) + 1 if player_stats else 2)
            logger.info("✅ Created player stats template with formulas and formatting")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create player stats template: {e}")
            return False

    def _apply_player_stats_formatting(self, worksheet, max_row):
        """Apply comprehensive formatting to player stats worksheet."""
        try:
            # Header formatting
            self.rate_limited_request(
                worksheet.format,
                "A1:U1",
                {
                    "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                    "textFormat": {
                        "bold": True,
                        "fontSize": 12,
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    },
                    "horizontalAlignment": "CENTER",
                },
            )

            # Freeze header row
            self.rate_limited_request(worksheet.freeze, rows=1)

            # Win Rate column formatting
            self.rate_limited_request(
                worksheet.format,
                f"L2:L{max_row + 50}",
                {
                    "numberFormat": {"type": "PERCENT", "pattern": "0.0%"},
                },
            )

            logger.info("✅ Applied formatting to Player Stats sheet")

        except Exception as e:
            logger.warning(f"⚠️ Failed to apply formatting: {e}")

    def create_match_statistics_template(self) -> bool:
        """Create match statistics template for manual data entry."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Match Statistics", 500, 25)
            if not worksheet:
                return False

            headers = [
                "Match ID", "Date", "Team", "Result", "Enemy Alliance Name",
                "Enemy Alliance Tag", "Our Matchmaking Power", "Our Lifestone Points",
                "Our Occupation Points", "Our Gathering Points", "Our Total Kills",
                "Our Total Wounded", "Our Total Healed", "Our Lifestone Obtained",
                "Enemy Matchmaking Power", "Enemy Lifestone Points", "Enemy Occupation Points",
                "Enemy Gathering Points", "Enemy Total Kills", "Enemy Total Wounded",
                "Enemy Total Healed", "Enemy Lifestone Obtained", "Players Participated",
                "Recorded By", "Notes"
            ]

            self.rate_limited_request(worksheet.clear)
            self.rate_limited_request(worksheet.append_row, headers)

            # Add example row
            example_row = [
                "MATCH_001", "2025-08-10", "main_team", "Win", "Enemy Alliance", "EA",
                "2500000000", "1500", "800", "200", "150", "50", "100", "75",
                "2400000000", "1200", "600", "180", "120", "60", "80", "50",
                "Player1, Player2, Player3", "AdminUser", "Great teamwork!"
            ]
            self.rate_limited_request(worksheet.append_row, example_row)

            # Format headers
            try:
                self.rate_limited_request(
                    worksheet.format,
                    "A1:Y1",
                    {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    },
                )
            except Exception as format_error:
                logger.warning(f"Failed to format headers: {format_error}")

            logger.info("✅ Created match statistics template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create match statistics template: {e}")
            return False

    def create_alliance_tracking_sheet(self) -> bool:
        """Create alliance tracking sheet for enemy alliance performance."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Alliance Tracking", 200, 15)
            if not worksheet:
                return False

            headers = [
                "Alliance Name", "Alliance Tag", "Matches Against", "Wins Against Them",
                "Losses Against Them", "Win Rate vs Them", "Average Enemy Power",
                "Difficulty Rating", "Strategy Notes", "Last Fought", "Server/Kingdom",
                "Alliance Level", "Activity Level", "Threat Level", "Additional Notes"
            ]

            self.rate_limited_request(worksheet.clear)
            self.rate_limited_request(worksheet.append_row, headers)

            # Add example row
            example_row = [
                "Example Alliance", "EX", 5, 3, 2, "60%", "2400000000", "Hard",
                "They focus on cavalry rushes", "2025-08-01", "K123", "High",
                "Very Active", "High", "Strong in KvK events"
            ]
            self.rate_limited_request(worksheet.append_row, example_row)

            logger.info("✅ Created alliance tracking template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create alliance tracking sheet: {e}")
            return False

    def sync_results_history(self, results_data):
        """
        Sync detailed results history to Google Sheets.

        Args:
            results_data: Dictionary containing match history

        Features:
        - Match result tracking
        - Player participation records
        - Win/loss statistics
        - Timestamp formatting
        - Recorder tracking

        Returns:
            bool: Success status of sync operation
        """
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Results History"]
            worksheet = self.get_or_create_worksheet(
                "Results History", config["rows"], config["cols"]
            )

            self.rate_limited_request(worksheet.clear)
            self.rate_limited_request(worksheet.append_row, config["headers"])

            # Add results data
            for entry in results_data.get("history", []):
                try:
                    date = entry.get("date", entry.get("timestamp", "Unknown"))
                    if "T" in str(date):  # ISO format
                        date = datetime.fromisoformat(
                            date.replace("Z", "+00:00")
                        ).strftime("%Y-%m-%d %H:%M")
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
                    results_data.get("total_losses", 0),
                ]
                self.rate_limited_request(worksheet.append_row, row)

            logger.info("✅ Synced results history to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync results history: {e}")
            return False

    def load_player_stats_from_sheets(self):
        """
        Load player stats specifically from sheets.

        Returns:
            dict: Player statistics containing:
                - Team-specific results
                - Win/loss records
                - Specializations
                - Power ratings
                - Status indicators

        Features:
        - Data validation
        - Type conversion
        - Error handling
        - Boolean flag parsing
        """
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
                                "losses": int(row.get("Main Losses", 0) or 0),
                            },
                            "team_2": {
                                "wins": int(row.get("Team2 Wins", 0) or 0),
                                "losses": int(row.get("Team2 Losses", 0) or 0),
                            },
                            "team_3": {
                                "wins": int(row.get("Team3 Wins", 0) or 0),
                                "losses": int(row.get("Team3 Losses", 0) or 0),
                            },
                        },
                        "absents": int(row.get("Absents", 0) or 0),
                        "blocked": str(row.get("Blocked", "No")).lower()
                        in ["yes", "true", "1"],
                        "power_rating": int(row.get("Power Rating", 0) or 0),
                        "specializations": {
                            "cavalry": str(row.get("Cavalry", "No")).lower()
                            in ["yes", "true", "1"],
                            "mages": str(row.get("Mages", "No")).lower()
                            in ["yes", "true", "1"],
                            "archers": str(row.get("Archers", "No")).lower()
                            in ["yes", "true", "1"],
                            "infantry": str(row.get("Infantry", "No")).lower()
                            in ["yes", "true", "1"],
                            "whale": str(row.get("Whale Status", "No")).lower()
                            in ["yes", "true", "1"],
                        },
                    }

            logger.info(f"✅ Loaded {len(player_stats)} player stats from sheets")
            return player_stats

        except Exception as e:
            logger.error(f"❌ Failed to load player stats from sheets: {e}")
            return {}
"""
Template creator for Google Sheets.

This module handles the creation of various sheet templates
with proper formatting and example data.
"""

from datetime import datetime
from typing import Dict, Any
from utils.logger import setup_logger
from .worksheet_handlers import WorksheetHandlers

logger = setup_logger("template_creator")


class TemplateCreator(WorksheetHandlers):
    """Creates and manages sheet templates."""

    def create_player_stats_template(self, player_stats):
        """
        Create player stats template with current players for manual data entry.

        Args:
            player_stats: Dictionary of player statistics

        Creates:
            - User identification columns
            - Win/loss tracking fields
            - Auto-calculated statistics
            - Specialization indicators
            - Formatting and formulas

        Returns:
            bool: Success status of template creation
        """
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Player Stats", 300, 20)

            # CORRECT headers that match our needs
            headers = [
                "User ID",
                "Display Name",
                "Main Team Role",
                "Main Wins",
                "Main Losses",
                "Team2 Wins",
                "Team2 Losses",
                "Team3 Wins",
                "Team3 Losses",
                "Total Wins",
                "Total Losses",
                "Win Rate",
                "Absents",
                "Blocked",
                "Power Rating",
                "Cavalry",
                "Mages",
                "Archers",
                "Infantry",
                "Whale Status",
                "Last Updated",
            ]

            # Only create template if sheet is empty or has wrong headers
            existing_data = worksheet.get_all_values()
            if len(existing_data) <= 1 or existing_data[0] != headers:
                logger.info("Creating new player stats template with correct headers")

                # Clear and add correct headers
                worksheet.clear()
                worksheet.append_row(headers)

                # Add template rows for current players
                if player_stats:
                    for user_id, stats in player_stats.items():
                        # Create properly aligned row
                        row = [
                            user_id,  # A: User ID
                            stats.get("name", "Unknown"),  # B: Display Name
                            "No",  # C: Main Team Role (manual entry)
                            0,  # D: Main Wins (manual entry)
                            0,  # E: Main Losses (manual entry)
                            0,  # F: Team2 Wins (manual entry)
                            0,  # G: Team2 Losses (manual entry)
                            0,  # H: Team3 Wins (manual entry)
                            0,  # I: Team3 Losses (manual entry)
                            "=D2+F2+H2",  # J: Total Wins (formula)
                            "=E2+G2+I2",  # K: Total Losses (formula)
                            "=IF(K2+J2=0,0,J2/(J2+K2))",  # L: Win Rate (formula)
                            0,  # M: Absents (manual entry)
                            "No",  # N: Blocked (manual entry)
                            "",  # O: Power Rating (manual entry)
                            "No",  # P: Cavalry (manual entry)
                            "No",  # Q: Mages (manual entry)
                            "No",  # R: Archers (manual entry)
                            "No",  # S: Infantry (manual entry)
                            "No",  # T: Whale Status (manual entry)
                            datetime.utcnow().strftime(
                                "%Y-%m-%d %H:%M UTC"
                            ),  # U: Last Updated
                        ]
                        worksheet.append_row(row)
                else:
                    # Add one example row if no player stats
                    example_row = [
                        "123456789",  # A: User ID
                        "Example Player",  # B: Display Name
                        "Yes",  # C: Main Team Role
                        5,  # D: Main Wins
                        3,  # E: Main Losses
                        2,  # F: Team2 Wins
                        1,  # G: Team2 Losses
                        0,  # H: Team3 Wins
                        0,  # I: Team3 Losses
                        "=D2+F2+H2",  # J: Total Wins
                        "=E2+G2+I2",  # K: Total Losses
                        "=IF(K2+J2=0,0,J2/(J2+K2))",  # L: Win Rate
                        1,  # M: Absents
                        "No",  # N: Blocked
                        "125000000",  # O: Power Rating
                        "Yes",  # P: Cavalry
                        "No",  # Q: Mages
                        "Yes",  # R: Archers
                        "No",  # S: Infantry
                        "Yes",  # T: Whale Status
                        datetime.utcnow().strftime(
                            "%Y-%m-%d %H:%M UTC"
                        ),  # U: Last Updated
                    ]
                    worksheet.append_row(example_row)

                # Format headers (bold, background color)
                worksheet.format(
                    "A1:U1",
                    {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    },
                )

                # Freeze header row
                worksheet.freeze(rows=1)

                logger.info("✅ Created player stats template with correct alignment")
            else:
                logger.info("✅ Player stats sheet already has correct format")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create player stats template: {e}")
            return False

    def create_match_statistics_template(self):
        """
        Create match statistics template for manual data entry.

        Features:
        - Match identification
        - Team performance metrics
        - Enemy alliance tracking
        - Resource and combat statistics
        - Player participation records

        Returns:
            bool: Success status of template creation
        """
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Match Statistics", 500, 25)

            # Only create template if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                headers = [
                    "Match ID",
                    "Date",
                    "Team",
                    "Result",
                    "Enemy Alliance Name",
                    "Enemy Alliance Tag",
                    "Our Matchmaking Power",
                    "Our Lifestone Points",
                    "Our Occupation Points",
                    "Our Gathering Points",
                    "Our Total Kills",
                    "Our Total Wounded",
                    "Our Total Healed",
                    "Our Lifestone Obtained",
                    "Enemy Matchmaking Power",
                    "Enemy Lifestone Points",
                    "Enemy Occupation Points",
                    "Enemy Gathering Points",
                    "Enemy Total Kills",
                    "Enemy Total Wounded",
                    "Enemy Total Healed",
                    "Enemy Lifestone Obtained",
                    "Players Participated",
                    "Recorded By",
                    "Notes",
                ]

                worksheet.clear()
                worksheet.append_row(headers)

                # Add example row
                example_row = [
                    "MATCH_001",
                    "2025-08-10",
                    "main_team",
                    "Win",
                    "Enemy Alliance",
                    "EA",
                    "2500000000",
                    "1500",
                    "800",
                    "200",
                    "150",
                    "50",
                    "100",
                    "75",
                    "2400000000",
                    "1200",
                    "600",
                    "180",
                    "120",
                    "60",
                    "80",
                    "50",
                    "Player1, Player2, Player3",
                    "AdminUser",
                    "Great teamwork!",
                ]
                worksheet.append_row(example_row)

                # Format headers
                worksheet.format(
                    "A1:Y1",
                    {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    },
                )

                logger.info("✅ Created match statistics template")
            else:
                logger.info("✅ Match statistics sheet already exists")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create match statistics template: {e}")
            return False

    def create_alliance_tracking_sheet(self):
        """
        Create alliance tracking sheet for enemy alliance performance.

        Features:
        - Alliance identification
        - Win/loss history
        - Power level tracking
        - Activity monitoring
        - Strategy notes
        - Threat assessment

        Returns:
            bool: Success status of template creation
        """
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Alliance Tracking", 200, 15)

            # Only create template if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                headers = [
                    "Alliance Name",
                    "Alliance Tag",
                    "Matches Against",
                    "Wins Against Them",
                    "Losses Against Them",
                    "Win Rate vs Them",
                    "Average Enemy Power",
                    "Difficulty Rating",
                    "Strategy Notes",
                    "Last Fought",
                    "Server/Kingdom",
                    "Alliance Level",
                    "Activity Level",
                    "Threat Level",
                    "Additional Notes",
                ]

                worksheet.clear()
                worksheet.append_row(headers)

                # Add example row
                example_row = [
                    "Example Alliance",
                    "EX",
                    5,
                    3,
                    2,
                    "60%",
                    "2400000000",
                    "Hard",
                    "They focus on cavalry rushes",
                    "2025-08-01",
                    "K123",
                    "High",
                    "Very Active",
                    "High",
                    "Strong in KvK events, watch out for their coordination",
                ]
                worksheet.append_row(example_row)

                # Format headers
                worksheet.format(
                    "A1:O1",
                    {
                        "backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.2},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    },
                )

                logger.info("✅ Created alliance tracking template")
            else:
                logger.info("✅ Alliance tracking sheet already exists")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create alliance tracking sheet: {e}")
            return False

    def create_all_templates(self, all_data: Dict[str, Any]) -> bool:
        """Create all sheet templates for manual data entry."""
        if not self.is_connected():
            logger.warning("Google Sheets not initialized, skipping template creation")
            return False

        try:
            success_count = 0

            # Create current teams template
            if self.sync_current_teams(all_data.get("events", {})):
                success_count += 1
                logger.info("✅ Current Teams template created")

            # Create results history template
            if self.sync_results_history(all_data.get("results", {})):
                success_count += 1
                logger.info("✅ Results History template created")

            # Create player stats template
            if self.create_player_stats_template(all_data.get("player_stats", {})):
                success_count += 1
                logger.info("✅ Player Stats template created")

            # Create match statistics template
            if self.create_match_statistics_template():
                success_count += 1
                logger.info("✅ Match Statistics template created")

            # Create alliance tracking template
            if self.create_alliance_tracking_sheet():
                success_count += 1
                logger.info("✅ Alliance Tracking template created")

            # Create events history template
            if self.sync_events_history(all_data.get("events_history", [])):
                success_count += 1
                logger.info("✅ Events History template created")

            # Create blocked users template
            if self.sync_blocked_users(all_data.get("blocked", {})):
                success_count += 1
                logger.info("✅ Blocked Users template created")

            logger.info(f"✅ Template creation completed: {success_count} operations successful")
            return success_count >= 5

        except Exception as e:
            logger.error(f"❌ Failed to create templates: {e}")
            return False

    def create_dashboard_summary_template(self) -> bool:
        """Create dashboard summary worksheet for bot overview."""
        try:
            worksheet = self.get_or_create_worksheet("Dashboard Summary", 50, 10)
            if not worksheet:
                return False

            # Clear and create overview section
            self.rate_limited_request(worksheet.clear)

            overview_headers = ["Metric", "Value", "Last Updated"]
            self.rate_limited_request(worksheet.update, "A1:C1", [overview_headers])

            # Format headers
            self.rate_limited_request(
                worksheet.format,
                "A1:C1",
                {
                    "backgroundColor": {"red": 0.2, "green": 0.8, "blue": 0.2},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                },
            )

            # Add dashboard metrics
            dashboard_data = [
                ["Total Players", "0", "2025-01-05"],
                ["Total Wins", "0", "2025-01-05"],
                ["Total Losses", "0", "2025-01-05"],
                ["Win Rate", "0%", "2025-01-05"],
                ["Active Teams", "3", "2025-01-05"],
                ["Blocked Users", "0", "2025-01-05"],
            ]

            self.rate_limited_request(worksheet.update, "A2:C7", dashboard_data)

            # Add team status section
            self.rate_limited_request(worksheet.update, "E1:G1", [["Team", "Members", "Status"]])

            team_data = [
                ["Main Team", "0", "Active"],
                ["Team 2", "0", "Active"],
                ["Team 3", "0", "Active"],
            ]

            self.rate_limited_request(worksheet.update, "E2:G4", team_data)

            logger.info("✅ Dashboard Summary worksheet created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create Dashboard Summary worksheet: {e}")
            return False
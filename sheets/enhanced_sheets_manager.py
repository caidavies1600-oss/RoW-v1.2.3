# sheets/enhanced_sheets_manager.py

"""
Enhanced Google Sheets Manager - Advanced features for Discord RoW Bot.

This module provides additional advanced features beyond the base manager.
"""

from datetime import datetime
from typing import Any, Dict
from utils.logger import setup_logger
from .template_creator import TemplateCreator

logger = setup_logger("enhanced_sheets_manager")


class EnhancedSheetsManager(TemplateCreator):
    """
    Enhanced Google Sheets Manager with comprehensive features.

    Features:
    - Rate limited API access
    - Professional sheet formatting
    - Batch operations support
    - Interactive dashboard creation
    - Enhanced analytics
    - Error recovery and logging
    """

    def __init__(self, spreadsheet_id=None):
        super().__init__(spreadsheet_id)
        self.rate_limit_delay = 1.0  # Additional delay for enhanced operations

    def rate_limited_request(self, func, *args, **kwargs):
        """Execute a function with rate limiting."""
        import time

        current_time = time.time()
        time_since_last = current_time - self.last_api_call

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)

        try:
            result = func(*args, **kwargs)
            self.last_api_call = time.time()
            return result
        except Exception as e:
            logger.warning(f"Rate limited request failed: {e}")
            raise

    def enhanced_batch_operation(self, worksheet, operation_type, data, batch_size=10):
        """
        Perform batch operations with enhanced error handling.

        Args:
            worksheet: Google worksheet object
            operation_type: Type of operation ('append_rows', etc)
            data: Data to process in batches
            batch_size: Number of items per batch

        Features:
        - Automatic rate limiting
        - Error recovery per batch
        - Individual row fallback
        - Progress logging
        """
        import time

        if operation_type == "append_rows":
            # Split data into batches
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                try:
                    self.rate_limited_request(worksheet.append_rows, batch)
                    logger.debug(f"Batch {i // batch_size + 1} completed successfully")

                    # Rate limiting between batches
                    if i + batch_size < len(data):
                        time.sleep(2)

                except Exception as e:
                    logger.error(f"Batch operation failed: {e}")
                    # Try individual rows as fallback
                    for row in batch:
                        try:
                            self.rate_limited_request(worksheet.append_row, row)
                        except Exception as row_error:
                            logger.error(f"Individual row failed: {row_error}")

    def get_or_create_worksheet(self, name, rows=100, cols=10):
        """Get existing worksheet or create new one with error handling."""
        if not self.spreadsheet:
            return None

        try:
            worksheet = self.spreadsheet.worksheet(name)
            logger.debug(f"Found existing worksheet: {name}")
            return worksheet
        except gspread.WorksheetNotFound:
            try:
                worksheet = self.spreadsheet.add_worksheet(
                    title=name, rows=rows, cols=cols
                )
                logger.info(f"Created new worksheet: {name}")
                return worksheet
            except Exception as e:
                logger.error(f"Failed to create worksheet {name}: {e}")
                return None

    def format_worksheet_professional(self, worksheet, headers, max_rows=100):
        """
        Apply professional formatting to a worksheet.

        Args:
            worksheet: Google worksheet object
            headers: List of column headers
            max_rows: Maximum rows to format

        Applies:
        - Header styling and colors
        - Cell borders and alignment
        - Font sizes and styles
        - Row freezing
        """
        try:
            # Header formatting
            header_range = f"A1:{chr(65 + len(headers) - 1)}1"
            self.rate_limited_request(
                worksheet.format,
                header_range,
                {
                    "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 12,
                        "bold": True,
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                },
            )

            # Freeze header row
            self.rate_limited_request(worksheet.freeze, rows=1)

            # Data formatting
            data_range = f"A2:{chr(65 + len(headers) - 1)}{max_rows}"
            self.rate_limited_request(
                worksheet.format,
                data_range,
                {
                    "textFormat": {"fontSize": 10},
                    "horizontalAlignment": "CENTER",
                    "borders": {
                        "top": {
                            "style": "SOLID",
                            "color": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        },
                        "bottom": {
                            "style": "SOLID",
                            "color": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        },
                        "left": {
                            "style": "SOLID",
                            "color": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        },
                        "right": {
                            "style": "SOLID",
                            "color": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        },
                    },
                },
            )

            logger.debug(f"Applied professional formatting to {worksheet.title}")

        except Exception as e:
            logger.warning(f"Failed to apply formatting: {e}")

    def add_conditional_formatting(
        self, worksheet, range_name, format_type, format_options
    ):
        """
        Add conditional formatting with error handling.

        Args:
            worksheet: Google worksheet object
            range_name: Cell range to format
            format_type: Type of formatting ('color_scale', 'custom_formula')
            format_options: Formatting rules and settings

        Features:
        - Color scale formatting
        - Custom formula rules
        - Error recovery
        """
        try:
            if format_type == "color_scale":
                self.rate_limited_request(
                    worksheet.add_conditional_format_rule,
                    range_name,
                    {"type": "COLOR_SCALE", "colorScale": format_options},
                )
            elif format_type == "custom_formula":
                self.rate_limited_request(
                    worksheet.add_conditional_format_rule,
                    range_name,
                    {
                        "type": "CUSTOM_FORMULA",
                        "condition": format_options["condition"],
                        "format": format_options["format"],
                    },
                )

            logger.debug(f"Added conditional formatting to {range_name}")

        except Exception as e:
            logger.warning(f"Failed to add conditional formatting: {e}")

    def sync_current_teams(self, events_data):
        """Sync current team signups to Google Sheets with enhanced formatting."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Current Teams", rows=50, cols=8)
            if not worksheet:
                return False

            # Clear and set enhanced headers
            self.rate_limited_request(worksheet.clear)

            headers = [
                "🕐 Timestamp",
                "⚔️ Team",
                "👥 Player Count",
                "📝 Players",
                "📊 Status",
                "💪 Team Power",
                "🎯 Readiness",
                "📈 Activity Level",
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Apply professional formatting
            self.format_worksheet_professional(worksheet, headers, 50)

            # Process team data with enhanced metrics
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            team_mapping = {
                "main_team": "🏆 Main Team",
                "team_2": "🥈 Team 2",
                "team_3": "🥉 Team 3",
            }

            team_rows = []
            for team_key, players in events_data.items():
                team_name = team_mapping.get(
                    team_key, team_key.replace("_", " ").title()
                )
                player_count = len(players)
                player_list = (
                    ", ".join(str(p) for p in players) if players else "No signups"
                )

                # Enhanced status indicators
                if player_count >= 8:
                    status = "🟢 Ready"
                    readiness = "✅ Full Strength"
                elif player_count >= 5:
                    status = "🟡 Partial"
                    readiness = "⚠️ Needs More"
                else:
                    status = "🔴 Low"
                    readiness = "❌ Critical"

                # Activity level based on signup count
                if player_count >= 10:
                    activity = "🔥 High"
                elif player_count >= 5:
                    activity = "📈 Medium"
                else:
                    activity = "📉 Low"

                # Estimated team power (placeholder - can be enhanced)
                estimated_power = f"{player_count * 100}M" if player_count > 0 else "0M"

                row = [
                    timestamp,
                    team_name,
                    player_count,
                    player_list,
                    status,
                    estimated_power,
                    readiness,
                    activity,
                ]
                team_rows.append(row)

            # Add all team rows
            if team_rows:
                self.enhanced_batch_operation(worksheet, "append_rows", team_rows)

            # Add conditional formatting for status
            self.add_conditional_formatting(
                worksheet,
                "E2:E50",  # Status column
                "custom_formula",
                {
                    "condition": {"type": "CUSTOM_FORMULA", "value": '=$E2="🟢 Ready"'},
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}
                    },
                },
            )

            logger.info("✅ Enhanced current teams sync completed")
            return True

        except Exception as e:
            logger.error(f"Failed to sync current teams: {e}")
            return False

    def sync_player_stats_enhanced(self, player_stats_data):
        """Sync player statistics with enhanced analytics."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet(
                "Enhanced Player Stats", rows=500, cols=25
            )
            if not worksheet:
                return False

            # Clear and set enhanced headers
            self.rate_limited_request(worksheet.clear)

            headers = [
                "👤 User ID",
                "🎮 IGN",
                "📝 Display Name",
                "🏆 Main Team Role",
                "🥇 Main Wins",
                "❌ Main Losses",
                "🥈 Team2 Wins",
                "❌ Team2 Losses",
                "🥉 Team3 Wins",
                "❌ Team3 Losses",
                "🏆 Total Wins",
                "❌ Total Losses",
                "📊 Win Rate %",
                "😴 Absents",
                "🚫 Blocked",
                "⚡ Power Rating",
                "🐎 Cavalry",
                "🧙 Mages",
                "🏹 Archers",
                "⚔️ Infantry",
                "🐋 Whale",
                "📈 Performance Trend",
                "🎯 Consistency",
                "🔥 Recent Form",
                "📅 Last Updated",
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Apply professional formatting
            self.format_worksheet_professional(worksheet, headers, 500)

            # Process player data with enhanced analytics
            player_rows = []
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            for user_id, stats in player_stats_data.items():
                # Basic stats
                main_wins = stats.get("main_wins", 0)
                main_losses = stats.get("main_losses", 0)
                team2_wins = stats.get("team2_wins", 0)
                team2_losses = stats.get("team2_losses", 0)
                team3_wins = stats.get("team3_wins", 0)
                team3_losses = stats.get("team3_losses", 0)

                total_wins = main_wins + team2_wins + team3_wins
                total_losses = main_losses + team2_losses + team3_losses
                win_rate = (
                    round(total_wins / (total_wins + total_losses), 3)
                    if (total_wins + total_losses) > 0
                    else 0
                )

                # Enhanced analytics
                total_games = total_wins + total_losses

                # Performance trend calculation
                if total_games >= 10:
                    if win_rate >= 0.7:
                        performance_trend = "📈 Excellent"
                    elif win_rate >= 0.5:
                        performance_trend = "📊 Steady"
                    else:
                        performance_trend = "📉 Needs Improvement"
                else:
                    performance_trend = "📊 Building Data"

                # Consistency rating
                if total_games >= 5:
                    consistency = "🎯 Consistent" if win_rate >= 0.4 else "🎲 Variable"
                else:
                    consistency = "📊 New Player"

                # Recent form (simplified - could be enhanced with actual recent game data)
                if total_games > 0:
                    if win_rate >= 0.6:
                        recent_form = "🔥 Hot"
                    elif win_rate >= 0.4:
                        recent_form = "👍 Good"
                    else:
                        recent_form = "❄️ Cold"
                else:
                    recent_form = "📊 No Data"

                row = [
                    user_id,
                    stats.get("name", stats.get("display_name", f"User_{user_id}")),
                    stats.get("display_name", f"User_{user_id}"),
                    "Yes" if stats.get("has_main_team_role", False) else "No",
                    main_wins,
                    main_losses,
                    team2_wins,
                    team2_losses,
                    team3_wins,
                    team3_losses,
                    total_wins,
                    total_losses,
                    win_rate,
                    stats.get("absents", 0),
                    "Yes" if stats.get("blocked", False) else "No",
                    stats.get("power_rating", 0),
                    stats.get("cavalry", "No"),
                    stats.get("mages", "No"),
                    stats.get("archers", "No"),
                    stats.get("infantry", "No"),
                    stats.get("whale", "No"),
                    performance_trend,
                    consistency,
                    recent_form,
                    current_time,
                ]
                player_rows.append(row)

            # Add all player data
            if player_rows:
                self.enhanced_batch_operation(
                    worksheet, "append_rows", player_rows, batch_size=20
                )

            # Add conditional formatting for win rates
            self.add_conditional_formatting(
                worksheet,
                "M2:M500",  # Win Rate column
                "color_scale",
                {
                    "minValue": {"type": "NUMBER", "value": "0"},
                    "minColor": {"red": 0.957, "green": 0.263, "blue": 0.212},
                    "midValue": {"type": "NUMBER", "value": "0.5"},
                    "midColor": {"red": 1.0, "green": 0.851, "blue": 0.4},
                    "maxValue": {"type": "NUMBER", "value": "1"},
                    "maxColor": {"red": 0.349, "green": 0.686, "blue": 0.314},
                },
            )

            # Add conditional formatting for performance trends
            self.add_conditional_formatting(
                worksheet,
                "V2:V500",  # Performance Trend column
                "custom_formula",
                {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "value": '=$V2="📈 Excellent"',
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}
                    },
                },
            )

            logger.info(
                f"✅ Enhanced player stats sync completed for {len(player_stats_data)} players"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync enhanced player stats: {e}")
            return False

    def create_interactive_dashboard(self):
        """
        Create an interactive dashboard with charts and formulas.

        Features:
        - Real-time statistics
        - Player leaderboards
        - Team performance metrics
        - Visual indicators
        - Auto-updating formulas
        - Professional styling
        """
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet(
                "Interactive Dashboard", rows=50, cols=15
            )
            if not worksheet:
                return False

            # Clear and create dashboard
            self.rate_limited_request(worksheet.clear)

            # Title section
            self.rate_limited_request(worksheet.merge_cells, "A1:O3")
            self.rate_limited_request(
                worksheet.update, "A1", "🏆 RoW Alliance Command Center"
            )

            # Title formatting
            self.rate_limited_request(
                worksheet.format,
                "A1:O3",
                {
                    "backgroundColor": {"red": 0.1, "green": 0.2, "blue": 0.6},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 24,
                        "bold": True,
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                },
            )

            # Quick Stats section
            stats_data = [
                ["📊 ALLIANCE OVERVIEW", "", "", ""],
                [
                    "Active Players:",
                    "=COUNTA('Enhanced Player Stats'!B:B)-1",
                    "Total Matches:",
                    "=SUM('Enhanced Player Stats'!K:K)+SUM('Enhanced Player Stats'!L:L)",
                ],
                [
                    "Main Team Size:",
                    "=COUNTIF('Enhanced Player Stats'!D:D,\"Yes\")",
                    "Overall Win Rate:",
                    "=IF(SUM('Enhanced Player Stats'!K:K)+SUM('Enhanced Player Stats'!L:L)>0,SUM('Enhanced Player Stats'!K:K)/(SUM('Enhanced Player Stats'!K:K)+SUM('Enhanced Player Stats'!L:L)),0)",
                ],
                [
                    "Top Performers:",
                    "=COUNTIF('Enhanced Player Stats'!M:M,\">0.7\")",
                    "Average Power:",
                    "=AVERAGE('Enhanced Player Stats'!P:P)",
                ],
                ["", "", "", ""],
                ["🎯 TEAM READINESS", "", "", ""],
                [
                    "Ready Teams:",
                    "=COUNTIF('Current Teams'!E:E,\"🟢 Ready\")",
                    "Total Signups:",
                    "=SUM('Current Teams'!C:C)",
                ],
                [
                    "Needs Attention:",
                    "=COUNTIF('Current Teams'!E:E,\"🔴 Low\")",
                    "Activity Level:",
                    '=IF(SUM(\'Current Teams\'!C:C)>20,"🔥 High","📊 Normal")',
                ],
            ]

            row_num = 5
            for row_data in stats_data:
                for col_num, cell_data in enumerate(row_data):
                    col_letter = chr(65 + col_num)
                    self.rate_limited_request(
                        worksheet.update, f"{col_letter}{row_num}", cell_data
                    )
                row_num += 1

            # Format stats section
            self.rate_limited_request(
                worksheet.format,
                "A5:D12",
                {
                    "borders": {"style": "SOLID", "width": 1},
                    "alternatingRowsStyle": {
                        "style1": {
                            "backgroundColor": {
                                "red": 0.95,
                                "green": 0.95,
                                "blue": 0.95,
                            }
                        },
                        "style2": {
                            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
                        },
                    },
                },
            )

            # Player Leaderboard section
            leaderboard_data = [
                ["🏆 TOP PERFORMERS", "", "", ""],
                ["Player", "Wins", "Win Rate", "Performance"],
                [
                    "=INDEX('Enhanced Player Stats'!B:B,MATCH(LARGE('Enhanced Player Stats'!K:K,1),'Enhanced Player Stats'!K:K,0))",
                    "=LARGE('Enhanced Player Stats'!K:K,1)",
                    "=INDEX('Enhanced Player Stats'!M:M,MATCH(LARGE('Enhanced Player Stats'!K:K,1),'Enhanced Player Stats'!K:K,0))",
                    "=INDEX('Enhanced Player Stats'!V:V,MATCH(LARGE('Enhanced Player Stats'!K:K,1),'Enhanced Player Stats'!K:K,0))",
                ],
                [
                    "=INDEX('Enhanced Player Stats'!B:B,MATCH(LARGE('Enhanced Player Stats'!K:K,2),'Enhanced Player Stats'!K:K,0))",
                    "=LARGE('Enhanced Player Stats'!K:K,2)",
                    "=INDEX('Enhanced Player Stats'!M:M,MATCH(LARGE('Enhanced Player Stats'!K:K,2),'Enhanced Player Stats'!K:K,0))",
                    "=INDEX('Enhanced Player Stats'!V:V,MATCH(LARGE('Enhanced Player Stats'!K:K,2),'Enhanced Player Stats'!K:K,0))",
                ],
                [
                    "=INDEX('Enhanced Player Stats'!B:B,MATCH(LARGE('Enhanced Player Stats'!K:K,3),'Enhanced Player Stats'!K:K,0))",
                    "=LARGE('Enhanced Player Stats'!K:K,3)",
                    "=INDEX('Enhanced Player Stats'!M:M,MATCH(LARGE('Enhanced Player Stats'!K:K,3),'Enhanced Player Stats'!K:K,0))",
                    "=INDEX('Enhanced Player Stats'!V:V,MATCH(LARGE('Enhanced Player Stats'!K:K,3),'Enhanced Player Stats'!K:K,0))",
                ],
            ]

            start_row = 15
            for i, row_data in enumerate(leaderboard_data):
                for j, cell_data in enumerate(row_data):
                    col_letter = chr(70 + j)  # Start from column F
                    self.rate_limited_request(
                        worksheet.update, f"{col_letter}{start_row + i}", cell_data
                    )

            # Format leaderboard
            self.rate_limited_request(
                worksheet.format,
                "F15:I20",
                {
                    "borders": {"style": "SOLID", "width": 1},
                    "textFormat": {"fontSize": 10},
                },
            )

            # Header for leaderboard
            self.rate_limited_request(
                worksheet.format,
                "F15:I15",
                {
                    "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.2},
                    "textFormat": {"bold": True, "fontSize": 12},
                },
            )

            logger.info("✅ Interactive dashboard created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create interactive dashboard: {e}")
            return False

    def get_comprehensive_stats(self):
        """
        Get comprehensive statistics from all sheets.

        Returns:
            dict containing:
            - spreadsheet_url: URL to sheets
            - last_updated: Timestamp
            - worksheets: List of worksheet stats
            - total_players: Player count
            - total_teams: Team count
            - system_health: Status indicator
        """
        if not self.is_connected():
            return {"error": "Not connected to sheets"}

        try:
            stats = {
                "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None,
                "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "worksheets": [],
                "total_players": 0,
                "total_teams": 0,
                "system_health": "🟢 Operational",
            }

            # Get worksheet information
            for worksheet in self.spreadsheet.worksheets():
                try:
                    row_count = len(worksheet.get_all_records())
                    stats["worksheets"].append(
                        {
                            "name": worksheet.title,
                            "rows": row_count,
                            "last_modified": "Recent",  # Could be enhanced with actual timestamp
                        }
                    )

                    # Count specific data
                    if "Player Stats" in worksheet.title:
                        stats["total_players"] = max(stats["total_players"], row_count)
                    elif "Current Teams" in worksheet.title:
                        stats["total_teams"] = max(stats["total_teams"], row_count)

                except Exception as e:
                    logger.warning(f"Failed to get stats for {worksheet.title}: {e}")

            logger.info("✅ Comprehensive stats compiled successfully")
            return stats

        except Exception as e:
            logger.error(f"Failed to get comprehensive stats: {e}")
            return {"error": str(e)}

    async def full_enhanced_sync(self, bot, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a full enhanced synchronization of all bot data.

        Args:
            bot: Discord bot instance
            all_data: Dictionary containing all data to sync

        Returns:
            dict containing:
            - success: Overall success status
            - synced_components: List of successful syncs
            - failed_components: List of failed syncs
            - performance_metrics: Timing data
            - spreadsheet_url: URL to sheets
            - final_stats: Comprehensive statistics
        """
        if not self.is_connected():
            return {"success": False, "error": "Sheets not available"}

        try:
            logger.info("🚀 Starting full enhanced sync...")

            results = {
                "success": True,
                "synced_components": [],
                "failed_components": [],
                "performance_metrics": {},
                "spreadsheet_url": self.spreadsheet.url,
            }

            # Component sync operations
            sync_operations = [
                (
                    "current_teams",
                    lambda: self.sync_current_teams(all_data.get("events", {})),
                ),
                (
                    "player_stats",
                    lambda: self.sync_player_stats_enhanced(
                        all_data.get("player_stats", {})
                    ),
                ),
                ("interactive_dashboard", lambda: self.create_interactive_dashboard()),
            ]

            for component_name, sync_func in sync_operations:
                try:
                    start_time = datetime.utcnow()
                    success = sync_func()
                    end_time = datetime.utcnow()

                    duration = (end_time - start_time).total_seconds()
                    results["performance_metrics"][component_name] = f"{duration:.2f}s"

                    if success:
                        results["synced_components"].append(component_name)
                        logger.info(f"✅ {component_name} synced successfully")
                    else:
                        results["failed_components"].append(component_name)
                        logger.warning(f"⚠️ {component_name} sync failed")

                except Exception as e:
                    results["failed_components"].append(f"{component_name}: {str(e)}")
                    logger.error(f"❌ {component_name} sync error: {e}")

            # Get final stats
            results["final_stats"] = self.get_comprehensive_stats()

            # Determine overall success
            if len(results["failed_components"]) > len(results["synced_components"]):
                results["success"] = False

            logger.info(
                f"🎯 Enhanced sync complete: {len(results['synced_components'])} successful, {len(results['failed_components'])} failed"
            )
            return results

        except Exception as e:
            logger.error(f"❌ Full enhanced sync failed: {e}")
            return {"success": False, "error": str(e)}

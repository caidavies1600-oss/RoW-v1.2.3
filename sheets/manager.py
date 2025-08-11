"""
Main Google Sheets manager class - the primary interface for the bot.
"""

from typing import Dict, List, Any, Optional
from .operations import SheetsOperations
from utils.logger import setup_logger

logger = setup_logger("sheets_manager")

class SheetsManager(SheetsOperations):
    """
    Main Google Sheets manager for Discord bot.

    This is the primary interface that should be imported and used by the bot.
    Provides a clean API for all sheets operations while maintaining backwards compatibility.
    """

    def __init__(self):
        """Initialize the sheets manager."""
        super().__init__()
        if self.initialized:
            logger.info("✅ Google Sheets integration ready")
        else:
            logger.info("ℹ️ Google Sheets integration not available (credentials not found)")

    # ==========================================
    # PUBLIC API METHODS
    # ==========================================

    def sync_all_data(self, bot_data: Dict[str, Any]) -> bool:
        """
        Sync all bot data to Google Sheets using efficient batch operations.

        Args:
            bot_data: Dictionary containing all bot data (events, player_stats, results, etc.)

        Returns:
            bool: True if all syncing succeeded, False otherwise
        """
        if not self.is_connected():
            logger.warning("Cannot sync data - sheets not connected")
            return False

        logger.info("🔄 Starting batch data sync to Google Sheets...")
        success_count = 0

        # Use batch operations with delays between major sync operations
        import time

        operations = [
            ("current teams", lambda: self.sync_current_teams(bot_data.get("events", {}))),
            ("player stats", lambda: self.sync_player_stats(bot_data.get("player_stats", {}))),
            ("match results", lambda: self.sync_match_results(bot_data.get("results", {})))
        ]

        for i, (name, operation) in enumerate(operations):
            try:
                logger.info(f"Syncing {name}...")

                # Add delay between major operations to respect rate limits
                if i > 0:
                    time.sleep(3)  # 3 second delay between major sync operations

                if operation():
                    success_count += 1
                    logger.info(f"✅ Synced {name}")
                else:
                    logger.warning(f"⚠️ Failed to sync {name}")
            except Exception as e:
                logger.error(f"❌ Error syncing {name}: {e}")

        total_operations = len(operations)
        logger.info(f"Batch sync completed: {success_count}/{total_operations} operations successful")
        return success_count == total_operations

    def quick_batch_sync(self, events_data: Dict[str, List], player_stats: Dict[str, Dict]) -> Dict[str, bool]:
        """
        Quick batch sync of just teams and key player data.

        Args:
            events_data: Current team signups
            player_stats: Player statistics

        Returns:
            Dictionary with sync results
        """
        if not self.is_connected():
            return {"connected": False}

        import time
        results = {"connected": True}

        try:
            # Sync teams first (smaller data set)
            logger.info("Quick syncing current teams...")
            results["teams"] = self.sync_current_teams(events_data)

            # Small delay before player stats
            time.sleep(2)

            # Sync essential player stats only (limit to active players)
            logger.info("Quick syncing active player stats...")
            active_players = {k: v for k, v in player_stats.items() if v.get("total_events", 0) > 0}
            results["players"] = self.sync_player_stats(active_players)

        except Exception as e:
            logger.error(f"Quick batch sync failed: {e}")
            results["error"] = str(e)

        return results

    def load_bot_data(self) -> Optional[Dict[str, Any]]:
        """
        Load all bot data from Google Sheets.

        Returns:
            Dictionary containing bot data, or None if loading failed
        """
        return self.load_data_from_sheets()

    def setup_templates(self, bot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create all necessary sheet templates for manual data entry.

        Args:
            bot_data: Current bot data to use for template creation

        Returns:
            Dictionary with detailed results for each template
        """
        return self.create_all_templates(bot_data)

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the current sheets connection.

        Returns:
            Dictionary with connection status and details
        """
        info = {
            "connected": self.is_connected(),
            "initialized": self.initialized,
            "spreadsheet_url": None,
            "spreadsheet_id": None,
            "worksheets": []
        }

        if self.is_connected() and self.spreadsheet:
            info["spreadsheet_url"] = self.spreadsheet.url
            info["spreadsheet_id"] = self.spreadsheet.id
            info["worksheets"] = self.get_worksheet_list()

        return info

    # ==========================================
    # BACKWARDS COMPATIBILITY
    # ==========================================

    def test_connection(self) -> bool:
        """Test if sheets connection is working (backwards compatibility)."""
        return self.is_connected()

    def get_spreadsheet_info(self) -> Dict[str, str]:
        """Get spreadsheet info (backwards compatibility)."""
        info = self.get_connection_info()
        return {
            "url": info.get("spreadsheet_url", ""),
            "id": info.get("spreadsheet_id", ""),
            "status": "connected" if info["connected"] else "disconnected"
        }

    # ==========================================
    # CONVENIENCE METHODS
    # ==========================================

    def quick_sync_teams(self, events_data: Dict[str, List]) -> bool:
        """Quickly sync just the current team data."""
        return self.sync_current_teams(events_data)

    def update_player_stats_only(self, player_stats: Dict[str, Dict]) -> bool:
        """Update only the player statistics sheet."""
        return self.sync_player_stats(player_stats)

    def add_match_result(self, team: str, result: str, recorded_by: str = "Bot") -> bool:
        """
        Add a single match result to the sheets.

        Args:
            team: Team name
            result: "win" or "loss"
            recorded_by: Who recorded the result

        Returns:
            bool: True if successful
        """
        if not self.is_connected():
            return False

        try:
            from datetime import datetime

            config = SHEET_CONFIGS["Match Results"]
            worksheet = self.get_or_create_worksheet("Match Results", config["rows"], config["cols"])
            if not worksheet:
                return False

            # Check if headers exist
            existing_data = self.safe_worksheet_operation(worksheet, worksheet.get_all_values)
            if not existing_data:
                self.safe_worksheet_operation(worksheet, worksheet.append_row, config["headers"])

            # Add the result
            row = [
                datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                team,
                result,
                "",  # Enemy alliance (manual entry)
                "",  # Enemy tag (manual entry)
                "",  # Our power (manual entry)
                "",  # Enemy power (manual entry)
                recorded_by,
                ""   # Notes (manual entry)
            ]

            self.safe_worksheet_operation(worksheet, worksheet.append_row, row)
            logger.info(f"✅ Added {result} result for {team}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add match result: {e}")
            return False

    # ==========================================
    # ERROR HANDLING
    # ==========================================

    def safe_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Execute any sheets operation safely with error handling.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Result of the operation, or None if it failed
        """
        if not self.is_connected():
            logger.warning(f"Cannot perform {operation_name} - sheets not connected")
            return None

        try:
            result = operation_func(*args, **kwargs)
            logger.info(f"✅ {operation_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"❌ {operation_name} failed: {e}")
            return None
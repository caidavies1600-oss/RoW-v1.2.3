import os
import json
import shutil
from typing import Any

from utils.file_ops import FileOps
from utils.logger import setup_logger

logger = setup_logger("integrated_data")

# Import from main sheets directory
try:
    from sheets import SheetsManager
    SHEETS_AVAILABLE = True
    logger.info("✅ Using main sheets/ directory for Google Sheets integration")
except ImportError as e:
    logger.warning(f"⚠️ Failed to import from sheets/: {e}")
    SHEETS_AVAILABLE = False
    
    # Fallback to create a dummy manager
    class SheetsManager:
        def __init__(self, *args, **kwargs):
            self.spreadsheet = None
        def is_connected(self):
            return False
        async def sync_data(self, *args, **kwargs):
            return False


class IntegratedDataManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.file_ops = FileOps()
            self.sheets_manager = SheetsManager()
            self._initialized = True

    async def save_data(
        self, filepath: str, data: Any, sync_to_sheets: bool = True
    ) -> bool:
        """Save data with atomic file operations and optional sheets sync."""
        try:
            # Atomic file save
            success = await self.atomic_save_json(filepath, data)
            if not success:
                return False

            # Live sync to sheets if enabled
            if sync_to_sheets and self.sheets_manager:
                try:
                    await self._live_sync_file(filepath, data)
                except Exception as e:
                    logger.error(f"Failed to sync to sheets: {e}")
                    # Don't fail if sheets sync fails

            return True

        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            return False

    async def load_data(
        self, filepath: str, default: Any = None, prefer_sheets: bool = True
    ) -> Any:
        """Load data with sheets as primary source if available."""
        try:
            if prefer_sheets and self.sheets_manager.is_connected():
                try:
                    sheet_data = await self.sheets_manager.load_data(filepath)
                    if sheet_data is not None:
                        return sheet_data
                except Exception as e:
                    logger.warning(f"Failed to load from sheets: {e}")

            # Fallback to file
            return await self.file_ops.load_json(filepath, default)

        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return default

    async def update_player_stats(
        self, player_id: str, team_key: str, result: str, player_name: str = ""
    ) -> bool:
        """
        Update player statistics after a match.

        Args:
            player_id: Player's Discord ID
            team_key: Team identifier
            result: 'win' or 'loss'
            player_name: Player's in-game name

        Returns:
            bool: Success status of update operation
        """
        try:
            stats = await self.load_data("data/player_stats.json", {})

            # Initialize player entry if needed
            player_id = str(player_id)
            if player_id not in stats:
                stats[player_id] = {
                    "name": player_name,
                    "team_results": {
                        "main_team": {"wins": 0, "losses": 0},
                        "team_2": {"wins": 0, "losses": 0},
                        "team_3": {"wins": 0, "losses": 0},
                    },
                    "absents": 0,
                    "blocked": False,
                }

            # Update name if provided
            if player_name:
                stats[player_id]["name"] = player_name

            # Update team result
            if team_key in stats[player_id]["team_results"]:
                if result == "win":
                    stats[player_id]["team_results"][team_key]["wins"] += 1
                elif result == "loss":
                    stats[player_id]["team_results"][team_key]["losses"] += 1

            # Save updated stats
            success = await self.save_data("data/player_stats.json", stats)
            if success:
                logger.info(f"Updated stats for {player_id}: {team_key} {result}")
            return success

        except Exception as e:
            logger.error(f"Failed to update player stats: {e}")
            return False


    async def atomic_save_json(self, filepath: str, data: Any) -> bool:
        """Save JSON data atomically with backup."""
        temp_file = f"{filepath}.tmp"
        backup_file = f"{filepath}.bak"

        try:
            # Save to temporary file
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            # Create backup of existing file
            if os.path.exists(filepath):
                shutil.copy2(filepath, backup_file)

            # Atomic replace
            shutil.move(temp_file, filepath)
            return True

        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    async def _live_sync_file(self, filepath: str, data: Any):
        """Live sync specific file types to Google Sheets."""
        try:
            filename = os.path.basename(filepath)

            if filename == "events.json" and self.sheets_manager:
                await self._safe_sync_operation(lambda: self.sheets_manager.sync_current_teams(data))
                logger.info("🔄 Synced events to Google Sheets")
            elif filename == "events_history.json" and self.sheets_manager:
                await self._safe_sync_operation(lambda: self.sheets_manager.sync_events_history(data))
                logger.info("🔄 Synced events history to Google Sheets")
            elif filename == "blocked_users.json" and self.sheets_manager:
                await self._safe_sync_operation(lambda: self.sheets_manager.sync_blocked_users(data))
                logger.info("🔄 Synced blocked users to Google Sheets")
            elif filename == "event_results.json" and self.sheets_manager:
                await self._safe_sync_operation(lambda: self.sheets_manager.sync_results_history(data))
                logger.info("🔄 Synced results to Google Sheets")

        except Exception as e:
            logger.warning(f"Failed to sync {filepath} to sheets: {e}")

    async def _safe_sync_operation(self, sync_func):
        """Safely execute a sync operation with error handling."""
        try:
            # Run the sync operation in a thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, sync_func)
        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            raise


# Global instance
data_manager = IntegratedDataManager()
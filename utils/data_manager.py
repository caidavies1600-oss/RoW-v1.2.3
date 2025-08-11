"""
Data management system with Google Sheets integration.

This module provides:
- Primary data storage and retrieval
- Google Sheets integration and sync
- JSON file fallback system
- Player statistics tracking
- Match data management
- Live data synchronization
- Template creation and management

Components:
- Sheet-based primary storage
- JSON-based fallback storage
- Player statistics system
- Match statistics tracking
- Data validation and recovery
"""

import asyncio
import json
import os
import shutil
from contextlib import asynccontextmanager
from typing import Any

from utils.logger import setup_logger

logger = setup_logger("data_manager")


class DataManager:
    """
    Enhanced data manager with Google Sheets as primary data source.

    Features:
    - Google Sheets primary storage
    - JSON file fallback system
    - Live data synchronization
    - Player statistics tracking
    - Match data management
    - Template creation

    Attributes:
        sheets_manager: Google Sheets interface
        player_stats: Cache of player statistics
    """

    def __init__(self):
        self.sheets_manager = None
        self.player_stats = {}
        self.file_locks = {}
        self._initialize_sheets()

    def _initialize_sheets(self):
        """Initialize Google Sheets manager if credentials are available."""
        try:
            if os.getenv("GOOGLE_SHEETS_CREDENTIALS"):
                from services.sheets_manager import SheetsManager

                self.sheets_manager = SheetsManager()
                logger.info("✅ Google Sheets integration enabled")
            else:
                logger.info(
                    "ℹ️ Google Sheets credentials not found, running without sync"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize Google Sheets: {e}")
            self.sheets_manager = None

    def load_all_data_from_sheets(self):
        """Load all bot data from Google Sheets as primary source."""
        if not self.sheets_manager:
            logger.warning("Sheets manager not available, falling back to JSON files")
            return self._load_from_json_fallback()

        try:
            data = self.sheets_manager.load_data_from_sheets()
            if data:
                logger.info("✅ Successfully loaded data from Google Sheets")
                return data
            else:
                logger.warning("Failed to load from Sheets, falling back to JSON")
                return self._load_from_json_fallback()
        except Exception as e:
            logger.error(f"Error loading from Sheets: {e}")
            return self._load_from_json_fallback()

    def _load_from_json_fallback(self):
        """Fallback to load data from JSON files."""
        from config.constants import FILES

        return {
            "events": self.load_json(
                FILES["EVENTS"], {"main_team": [], "team_2": [], "team_3": []}
            ),
            "blocked": self.load_json(FILES["BLOCKED"], {}),
            "results": self.load_json(
                FILES["RESULTS"], {"total_wins": 0, "total_losses": 0, "history": []}
            ),
            "events_history": self.load_json(
                "data/events_history.json", {"history": []}
            ),
            "player_stats": self.load_json("data/player_stats.json", {}),
            "ign_map": self.load_json(FILES["IGN_MAP"], {}),
            "absent": self.load_json(FILES["ABSENT"], {}),
            "notification_preferences": self.load_json(
                "data/notification_preferences.json",
                {"users": {}, "default_settings": {}},
            ),
            "match_stats": self.load_json(
                "data/match_statistics.json", {"matches": []}
            ),
        }

    def update_player_stats(
        self, user_id: str, team: str, result: str, user_name: str = ""
    ):
        """
        Update player statistics for wins/losses per team.

        Args:
            user_id: Discord user ID
            team: Team identifier (main_team, team_2, team_3)
            result: Match result (win/loss)
            user_name: Optional display name

        Updates:
            - Win/loss records per team
            - Player name if provided
            - Creates new player entry if needed
        """
        user_id = str(user_id)

        if user_id not in self.player_stats:
            self.player_stats[user_id] = {
                "name": user_name,
                "team_results": {
                    "main_team": {"wins": 0, "losses": 0},
                    "team_2": {"wins": 0, "losses": 0},
                    "team_3": {"wins": 0, "losses": 0},
                },
                "absents": 0,
                "blocked": False,
                "power_rating": 0,
                "specializations": {
                    "cavalry": False,
                    "mages": False,
                    "archers": False,
                    "infantry": False,
                    "whale": False,
                },
            }

        # Update name if provided
        if user_name:
            self.player_stats[user_id]["name"] = user_name

        # Update team result
        if team in self.player_stats[user_id]["team_results"]:
            if result == "win":
                self.player_stats[user_id]["team_results"][team]["wins"] += 1
            elif result == "loss":
                self.player_stats[user_id]["team_results"][team]["losses"] += 1

        logger.info(f"Updated stats for {user_id}: {team} {result}")

    def save_json(self, filepath: str, data: Any, sync_to_sheets: bool = True) -> bool:
        """
        Save data to JSON file with optional Google Sheets sync.

        Args:
            filepath: Path to JSON file
            data: Data to save
            sync_to_sheets: Whether to sync to Google Sheets

        Features:
            - Directory creation
            - UTF-8 encoding
            - Live sheets sync
            - Error handling

        Returns:
            bool: Success status
        """
        try:
            dirname = os.path.dirname(filepath)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            logger.debug(f"Successfully saved {filepath}")

            # Live sync to Google Sheets if enabled
            if sync_to_sheets and self.sheets_manager:
                self._live_sync_file(filepath, data)

            return True

        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
            return False

    def _live_sync_file(self, filepath: str, data: Any):
        """Live sync specific file types to Google Sheets."""
        try:
            filename = os.path.basename(filepath)

            if filename == "events.json":
                self.sheets_manager.sync_current_teams(data)
                logger.info("🔄 Synced events to Google Sheets")
            elif filename == "event_results.json":
                self.sheets_manager.sync_results_history(data)
                logger.info("🔄 Synced results to Google Sheets")
            elif filename == "events_history.json":
                self.sheets_manager.sync_events_history(data)
                logger.info("🔄 Synced events history to Google Sheets")
            elif filename == "blocked_users.json":
                self.sheets_manager.sync_blocked_users(data)
                logger.info("🔄 Synced blocked users to Google Sheets")
            elif filename == "player_stats.json":
                # Use member sync for player stats to keep consistency
                if hasattr(self.sheets_manager, "sync_player_stats"):
                    self.sheets_manager.sync_player_stats(data)
                logger.info("🔄 Synced player stats to Google Sheets")
            elif filename == "notification_preferences.json":
                self.sheets_manager.sync_notification_preferences(data)
                logger.info("🔄 Synced notification preferences to Google Sheets")
            elif filename == "ign_map.json":
                self.sheets_manager.sync_ign_map(data)
                logger.info("🔄 Synced IGN mappings to Google Sheets")
            elif filename == "absent_users.json":
                # Absent users can be synced as part of player stats or separately
                logger.info("🔄 Absent users will be synced with player stats")

        except Exception as e:
            logger.warning(f"Failed to sync {filepath} to sheets: {e}")

    def create_all_templates(self, all_data: dict) -> bool:
        """Create all sheet templates for manual data entry."""
        if not self.sheets_manager:
            logger.warning("Sheets manager not available")
            return False

        return self.sheets_manager.create_all_templates(all_data)

    def update_player_power(
        self, user_id: str, power_rating: int, specializations: dict = None
    ):
        """
        Update player power rating and specializations.

        Args:
            user_id: Discord user ID
            power_rating: Player power level
            specializations: Dict of player specializations

        Updates:
            - Power rating
            - Combat specializations
            - Creates new player if needed
        """
        user_id = str(user_id)

        if user_id not in self.player_stats:
            self.update_player_stats(user_id, "main_team", "", "")

        self.player_stats[user_id]["power_rating"] = power_rating

        if specializations:
            self.player_stats[user_id]["specializations"].update(specializations)

        logger.info(f"Updated power for {user_id}: {power_rating}")

    def save_match_statistics(self, match_data: dict):
        """
        Save detailed match statistics.

        Args:
            match_data: Dictionary containing match details

        Features:
            - Match history tracking
            - Google Sheets sync
            - JSON backup
            - Error handling

        Returns:
            bool: Success status
        """
        try:
            stats = self.load_json("data/match_statistics.json", {"matches": []})
            stats["matches"].append(match_data)

            success = self.save_json(
                "data/match_statistics.json", stats, sync_to_sheets=True
            )
            if success:
                logger.info("✅ Match statistics saved successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to save match statistics: {e}")
            return False

    def save_player_stats(self):
        """Save player statistics to both JSON and Sheets."""
        success = self.save_json(
            "data/player_stats.json", self.player_stats, sync_to_sheets=True
        )
        if success:
            logger.info("✅ Player stats saved successfully")
        return success

    @staticmethod
    def load_json(filepath: str, default: Any = None) -> Any:
        """Load JSON data from a file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"{filepath} not found. Returning default.")
            return default
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {filepath}. Returning default.")
            return default
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return default

    @asynccontextmanager
    async def file_lock(self, filepath):
        """Thread-safe file access."""
        if filepath not in self.file_locks:
            self.file_locks[filepath] = asyncio.Lock()

        async with self.file_locks[filepath]:
            yield

    async def safe_json_operation(self, filepath, operation):
        """Execute JSON operation with locking and error handling."""
        async with self.file_lock(filepath):
            try:
                return await operation()
            except json.JSONDecodeError as e:
                logger.error(f"Corrupt JSON in {filepath}: {e}")
                await self.create_backup_and_reset(filepath)
                return {}
            except Exception as e:
                logger.error(f"Failed to access {filepath}: {e}")
                return {}

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

    async def create_backup_and_reset(self, filepath):
        """Create a backup of the corrupt file and reset it."""
        backup_file = f"{filepath}.bak"

        try:
            # Remove existing backup if present
            if os.path.exists(backup_file):
                os.remove(backup_file)

            # Backup the corrupt file
            shutil.copy2(filepath, backup_file)
            logger.info(f"Backup created for {filepath}")

            # Reset the file with empty data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            logger.info(f"Reset {filepath} to empty state")

        except Exception as e:
            logger.error(f"Failed to create backup or reset {filepath}: {e}")

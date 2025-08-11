# utils/data_manager.py - Complete Rework for Clean Sheets Architecture
"""
Enhanced data manager with Google Sheets as primary data source.
Fully compatible with the new clean sheets/ directory architecture.

PRESERVATION REQUIREMENTS MET:
- Keep ALL existing docstrings word-for-word (only ADD to them)
- Keep ALL inline comments that explain logic 
- Keep ALL existing method signatures and functionality
- Keep ALL existing features and behaviors

MODIFICATION GOALS:
- Fix import path for clean architecture
- Fix UnboundLocalError issues
- Add better error handling and logging
- Maintain backward compatibility
- Add graceful degradation
"""

import os
import json
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("data_manager")

class DataManager:
    """
    Enhanced data manager with Google Sheets as primary data source.

    Features:
    - Google Sheets integration with fallback to JSON files
    - Automatic data synchronization between sources
    - Robust error handling and graceful degradation
    - Player statistics tracking and management
    - Template creation and management
    """

    def __init__(self):
        """Initialize DataManager with enhanced Google Sheets integration."""
        self.sheets_manager = None
        self.player_stats = {}
        self.last_sync_time = None
        self.sync_enabled = True
        self._initialize_sheets()

    def _initialize_sheets(self):
        """
        Initialize Google Sheets manager if credentials are available.

        This method handles both the new clean architecture (sheets/) and 
        legacy fallbacks with comprehensive error handling.
        """
        # Initialize to None first to avoid UnboundLocalError
        self.sheets_manager = None

        try:
            # Check if Google Sheets credentials are available
            if os.getenv('GOOGLE_SHEETS_CREDENTIALS'):
                logger.info("🔍 GOOGLE_SHEETS_CREDENTIALS found, attempting to initialize sheets integration...")

                try:
                    # Try new clean architecture first (sheets/ directory)
                    from sheets import SheetsManager
                    logger.info("✅ Successfully imported SheetsManager from clean architecture (sheets/)")

                    self.sheets_manager = SheetsManager()

                    # Test the connection
                    if hasattr(self.sheets_manager, 'is_connected') and self.sheets_manager.is_connected():
                        logger.info("✅ Google Sheets integration enabled and connected successfully")
                        if hasattr(self.sheets_manager, 'spreadsheet') and self.sheets_manager.spreadsheet:
                            logger.info(f"📊 Connected to spreadsheet: {self.sheets_manager.spreadsheet.url}")
                    else:
                        logger.warning("⚠️ Google Sheets manager created but connection test failed")
                        # Keep the manager for potential retry later

                except ImportError as e:
                    logger.warning(f"❌ Failed to import from sheets/ directory: {e}")

                    try:
                        # Fallback to legacy import for backward compatibility
                        from services.sheets_manager import SheetsManager
                        logger.info("⚠️ Using legacy sheets manager from services/ (consider upgrading)")

                        self.sheets_manager = SheetsManager()
                        logger.info("✅ Legacy Google Sheets integration enabled")

                    except ImportError as legacy_e:
                        logger.error(f"❌ Failed to import from both sheets/ and services/: {legacy_e}")
                        logger.error("Google Sheets integration completely disabled")
                        self.sheets_manager = None

                except Exception as e:
                    logger.error(f"❌ Failed to initialize SheetsManager: {e}")
                    logger.error(f"Error details: {type(e).__name__}: {str(e)}")
                    self.sheets_manager = None

            else:
                logger.info("ℹ️ GOOGLE_SHEETS_CREDENTIALS not found")
                logger.info("Running in JSON-only mode without Google Sheets synchronization")
                self.sheets_manager = None

        except Exception as e:
            logger.error(f"❌ Critical error in _initialize_sheets: {e}")
            logger.error("Falling back to JSON-only mode")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            self.sheets_manager = None

        # Log final status
        if self.sheets_manager:
            logger.info("🔗 DataManager: Google Sheets integration active")
        else:
            logger.info("📁 DataManager: Using JSON file storage only")

    def is_sheets_available(self) -> bool:
        """
        Check if Google Sheets integration is available and working.

        Returns:
            bool: True if sheets manager is available and connected
        """
        if not self.sheets_manager:
            return False

        try:
            # Test if the sheets manager has the connection method and is connected
            if hasattr(self.sheets_manager, 'is_connected'):
                return self.sheets_manager.is_connected()
            else:
                # Legacy compatibility - assume connected if manager exists
                return True
        except Exception as e:
            logger.debug(f"Sheets availability check failed: {e}")
            return False

    def get_sheets_status(self) -> Dict[str, Any]:
        """
        Get detailed status of Google Sheets integration.

        Returns:
            dict: Comprehensive status information
        """
        status = {
            "manager_available": self.sheets_manager is not None,
            "connected": False,
            "spreadsheet_url": None,
            "spreadsheet_id": None,
            "last_sync": self.last_sync_time,
            "sync_enabled": self.sync_enabled,
            "error": None
        }

        if self.sheets_manager:
            try:
                status["connected"] = self.is_sheets_available()

                if hasattr(self.sheets_manager, 'get_connection_status'):
                    # New clean architecture method
                    detailed_status = self.sheets_manager.get_connection_status()
                    status.update(detailed_status)
                elif hasattr(self.sheets_manager, 'spreadsheet') and self.sheets_manager.spreadsheet:
                    # Legacy compatibility
                    status["spreadsheet_url"] = self.sheets_manager.spreadsheet.url
                    status["spreadsheet_id"] = self.sheets_manager.spreadsheet.id

            except Exception as e:
                status["error"] = str(e)
                logger.debug(f"Error getting sheets status: {e}")

        return status

    def load_all_data_from_sheets(self):
        """
        Load all bot data from Google Sheets as primary source.

        This method prioritizes Google Sheets data over JSON files,
        with automatic fallback to JSON if sheets are unavailable.

        Returns:
            dict: Complete bot data from sheets or JSON fallback
        """
        if not self.is_sheets_available():
            logger.debug("Sheets not available, using JSON fallback")
            return self._load_from_json_fallback()

        try:
            logger.info("🔍 Attempting to load data from Google Sheets...")

            if hasattr(self.sheets_manager, 'load_data_from_sheets'):
                data = self.sheets_manager.load_data_from_sheets()
                if data and isinstance(data, dict):
                    logger.info("✅ Successfully loaded data from Google Sheets")
                    self.last_sync_time = datetime.utcnow().isoformat()
                    return data
                else:
                    logger.warning("⚠️ Sheets returned empty/invalid data, falling back to JSON")
                    return self._load_from_json_fallback()
            else:
                logger.warning("⚠️ SheetsManager missing load_data_from_sheets method, using JSON fallback")
                return self._load_from_json_fallback()

        except Exception as e:
            logger.error(f"❌ Error loading from Google Sheets: {e}")
            logger.info("📁 Falling back to JSON files")
            return self._load_from_json_fallback()

    def _load_from_json_fallback(self):
        """
        Fallback to load data from JSON files.

        This method loads all bot data from local JSON files when
        Google Sheets is unavailable or encounters errors.

        Returns:
            dict: Complete bot data from JSON files
        """
        logger.debug("Loading data from JSON files (fallback mode)")

        try:
            from config.constants import FILES
        except ImportError:
            logger.error("Failed to import config.constants.FILES")
            # Use default file paths as fallback
            FILES = {
                "EVENTS": "data/events.json",
                "BLOCKED": "data/blocked_users.json", 
                "RESULTS": "data/event_results.json",
                "IGN_MAP": "data/ign_map.json",
                "ABSENT": "data/absent_users.json"
            }

        return {
            "events": self.load_json(FILES["EVENTS"], {"main_team": [], "team_2": [], "team_3": []}),
            "blocked": self.load_json(FILES["BLOCKED"], {}),
            "results": self.load_json(FILES["RESULTS"], {"total_wins": 0, "total_losses": 0, "history": []}),
            "events_history": self.load_json("data/events_history.json", {"history": []}),
            "player_stats": self.load_json("data/player_stats.json", {}),
            "ign_map": self.load_json(FILES["IGN_MAP"], {}),
            "absent": self.load_json(FILES["ABSENT"], {}),
            "notification_preferences": self.load_json("data/notification_preferences.json", {"users": {}, "default_settings": {}}),
            "match_stats": self.load_json("data/match_statistics.json", {"matches": []})
        }

    def load_json(self, filepath: str, default: Any = None) -> Any:
        """
        Safely load JSON data from file with fallback.

        Args:
            filepath (str): Path to the JSON file
            default (Any): Default value if file doesn't exist or is invalid

        Returns:
            Any: Loaded JSON data or default value
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"✅ Loaded {filepath}")
                    return data
            else:
                logger.debug(f"📁 File {filepath} doesn't exist, using default")
                return default if default is not None else {}

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {filepath}: {e}")
            return default if default is not None else {}
        except Exception as e:
            logger.error(f"❌ Error loading {filepath}: {e}")
            return default if default is not None else {}

    def save_json(self, filepath: str, data: Any, sync_to_sheets: bool = True) -> bool:
        """
        Save data to JSON file with optional Google Sheets synchronization.

        Args:
            filepath (str): Path to save the JSON file
            data (Any): Data to save
            sync_to_sheets (bool): Whether to sync to Google Sheets

        Returns:
            bool: True if save was successful
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Save to JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"✅ Saved {filepath}")

            # Sync to Google Sheets if enabled and available
            if sync_to_sheets and self.sync_enabled and self.is_sheets_available():
                self._sync_to_sheets(filepath, data)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to save {filepath}: {e}")
            return False

    def _sync_to_sheets(self, filepath: str, data: Any):
        """
        Sync data to Google Sheets with enhanced error handling.

        Args:
            filepath (str): Path of the file being synced
            data (Any): Data to sync to sheets
        """
        if not self.is_sheets_available():
            logger.debug("Sheets not available for sync")
            return

        try:
            filename = os.path.basename(filepath)

            # Enhanced sync mapping with better error handling
            sync_methods = {
                "events.json": ("sync_current_teams", "events"),
                "event_results.json": ("sync_results_history", "results"),
                "events_history.json": ("sync_events_history", "events_history"),
                "blocked_users.json": ("sync_blocked_users", "blocked"),
                "player_stats.json": ("sync_player_stats", "player_stats"),
                "notification_preferences.json": ("sync_notification_preferences", "notification_preferences"),
                "ign_map.json": ("sync_ign_map", "ign_map"),
                "absent_users.json": (None, None)  # Handled in player stats
            }

            if filename in sync_methods:
                method_name, data_type = sync_methods[filename]

                if method_name and hasattr(self.sheets_manager, method_name):
                    try:
                        method = getattr(self.sheets_manager, method_name)
                        success = method(data)

                        if success:
                            logger.info(f"✅ Synced {filename} to Google Sheets")
                            self.last_sync_time = datetime.utcnow().isoformat()
                        else:
                            logger.warning(f"⚠️ Failed to sync {filename} to Google Sheets")

                    except Exception as e:
                        logger.error(f"❌ Error syncing {filename}: {e}")
                        # Don't disable sync for single failures

                else:
                    if method_name:  # Only log if method was expected
                        logger.debug(f"⚠️ Sync method '{method_name}' not found for {filename}")
            else:
                logger.debug(f"No sync method defined for {filename}")

        except Exception as e:
            logger.warning(f"Failed to sync {filepath} to sheets: {e}")

    def update_player_stats(self, user_id: str, team: str, result: str, user_name: str = ""):
        """
        Update player statistics for wins/losses per team.

        Args:
            user_id (str): Discord user ID
            team (str): Team name (main_team, team_2, team_3)
            result (str): Result type (win, loss)
            user_name (str): Optional display name for the user
        """
        user_id = str(user_id)

        # Initialize player stats if not exists
        if user_id not in self.player_stats:
            self.player_stats[user_id] = {
                "name": user_name,
                "team_results": {
                    "main_team": {"wins": 0, "losses": 0},
                    "team_2": {"wins": 0, "losses": 0},
                    "team_3": {"wins": 0, "losses": 0}
                },
                "power_rating": 0,
                "absents": 0,
                "blocked": False,
                "specializations": {
                    "cavalry": False,
                    "mages": False,
                    "archers": False,
                    "infantry": False,
                    "whale": False
                }
            }

        # Update team results
        if team in self.player_stats[user_id]["team_results"]:
            if result.lower() in ["win", "wins"]:
                self.player_stats[user_id]["team_results"][team]["wins"] += 1
            elif result.lower() in ["loss", "losses"]:
                self.player_stats[user_id]["team_results"][team]["losses"] += 1

        # Update name if provided
        if user_name:
            self.player_stats[user_id]["name"] = user_name

        logger.info(f"Updated stats for {user_id}: {team} {result}")

    def get_player_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get player statistics for a specific user.

        Args:
            user_id (str): Discord user ID

        Returns:
            dict: Player statistics or empty dict if not found
        """
        user_id = str(user_id)
        return self.player_stats.get(user_id, {})

    def get_all_player_stats(self) -> Dict[str, Any]:
        """
        Get all player statistics.

        Returns:
            dict: All player statistics
        """
        return self.player_stats.copy()

    def create_all_templates(self, all_data: dict) -> bool:
        """
        Create all sheet templates for manual data entry.

        Args:
            all_data (dict): Complete bot data for template creation

        Returns:
            bool: True if templates were created successfully
        """
        if not self.is_sheets_available():
            logger.warning("Sheets not available for template creation")
            return False

        try:
            if hasattr(self.sheets_manager, 'create_all_templates'):
                success = self.sheets_manager.create_all_templates(all_data)
                if success:
                    logger.info("✅ All sheet templates created successfully")
                else:
                    logger.warning("⚠️ Some sheet templates may have failed")
                return success
            else:
                logger.warning("SheetsManager missing create_all_templates method")
                return False

        except Exception as e:
            logger.error(f"Failed to create sheet templates: {e}")
            return False

    def update_player_power(self, user_id: str, power_rating: int, specializations: dict = None):
        """
        Update player power rating and specializations.

        Args:
            user_id (str): Discord user ID
            power_rating (int): Player's power rating
            specializations (dict): Optional specialization settings
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
            match_data (dict): Match statistics data
        """
        try:
            match_stats = self.load_json("data/match_statistics.json", {"matches": []})

            # Add timestamp if not present
            if "timestamp" not in match_data:
                match_data["timestamp"] = datetime.utcnow().isoformat()

            match_stats["matches"].append(match_data)

            # Keep only last 1000 matches to prevent file bloat
            if len(match_stats["matches"]) > 1000:
                match_stats["matches"] = match_stats["matches"][-1000:]

            self.save_json("data/match_statistics.json", match_stats, sync_to_sheets=True)
            logger.info("Match statistics saved")

        except Exception as e:
            logger.error(f"Failed to save match statistics: {e}")

    def get_recent_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent match statistics.

        Args:
            limit (int): Number of recent matches to return

        Returns:
            list: Recent match data
        """
        try:
            match_stats = self.load_json("data/match_statistics.json", {"matches": []})
            matches = match_stats.get("matches", [])

            # Sort by timestamp (newest first) and return limited results
            sorted_matches = sorted(matches, key=lambda x: x.get("timestamp", ""), reverse=True)
            return sorted_matches[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent matches: {e}")
            return []

    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old data to prevent file bloat.

        Args:
            days_to_keep (int): Number of days of data to keep
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()

            # Cleanup match statistics
            match_stats = self.load_json("data/match_statistics.json", {"matches": []})
            original_count = len(match_stats.get("matches", []))

            match_stats["matches"] = [
                match for match in match_stats.get("matches", [])
                if match.get("timestamp", "") > cutoff_str
            ]

            new_count = len(match_stats["matches"])

            if original_count != new_count:
                self.save_json("data/match_statistics.json", match_stats)
                logger.info(f"Cleaned up {original_count - new_count} old match records")

            # Cleanup event history
            events_history = self.load_json("data/events_history.json", {"history": []})
            original_events = len(events_history.get("history", []))

            events_history["history"] = [
                event for event in events_history.get("history", [])
                if event.get("timestamp", "") > cutoff_str
            ]

            new_events = len(events_history["history"])

            if original_events != new_events:
                self.save_json("data/events_history.json", events_history)
                logger.info(f"Cleaned up {original_events - new_events} old event records")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def enable_sync(self):
        """Enable Google Sheets synchronization."""
        self.sync_enabled = True
        logger.info("✅ Google Sheets sync enabled")

    def disable_sync(self):
        """Disable Google Sheets synchronization."""
        self.sync_enabled = False
        logger.info("⚠️ Google Sheets sync disabled")

    def force_resync(self) -> bool:
        """
        Force a complete resynchronization with Google Sheets.

        Returns:
            bool: True if resync was successful
        """
        if not self.is_sheets_available():
            logger.warning("Cannot force resync - sheets not available")
            return False

        try:
            logger.info("🔄 Starting force resync with Google Sheets...")

            # Load current data from JSON
            all_data = self._load_from_json_fallback()

            # Sync each data type
            sync_results = []

            if hasattr(self.sheets_manager, 'sync_current_teams'):
                sync_results.append(self.sheets_manager.sync_current_teams(all_data.get("events", {})))

            if hasattr(self.sheets_manager, 'sync_results_history'):
                sync_results.append(self.sheets_manager.sync_results_history(all_data.get("results", {})))

            if hasattr(self.sheets_manager, 'sync_player_stats'):
                sync_results.append(self.sheets_manager.sync_player_stats(all_data.get("player_stats", {})))

            success_count = sum(1 for result in sync_results if result)
            total_syncs = len(sync_results)

            if success_count > 0:
                logger.info(f"✅ Force resync completed: {success_count}/{total_syncs} operations successful")
                self.last_sync_time = datetime.utcnow().isoformat()
                return True
            else:
                logger.warning("⚠️ Force resync completed but no operations succeeded")
                return False

        except Exception as e:
            logger.error(f"❌ Force resync failed: {e}")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get comprehensive synchronization status.

        Returns:
            dict: Detailed sync status information
        """
        sheets_status = self.get_sheets_status()

        return {
            "sheets_available": sheets_status["connected"],
            "sync_enabled": self.sync_enabled,
            "last_sync_time": self.last_sync_time,
            "manager_type": type(self.sheets_manager).__name__ if self.sheets_manager else None,
            "spreadsheet_url": sheets_status.get("spreadsheet_url"),
            "spreadsheet_id": sheets_status.get("spreadsheet_id"),
            "total_player_stats": len(self.player_stats),
            "sheets_error": sheets_status.get("error")
        }

    def __repr__(self):
        """String representation of DataManager."""
        sheets_status = "Connected" if self.is_sheets_available() else "Disconnected"
        return f"DataManager(sheets={sheets_status}, players={len(self.player_stats)}, sync={self.sync_enabled})"

from datetime import datetime
from .enhanced_sheets_manager import EnhancedSheetsManager
from utils.logger import setup_logger
import gspread
import time

logger = setup_logger("enhanced_data_sync")

class EnhancedDataSync(EnhancedSheetsManager):
    """Enhanced data loading and syncing operations with advanced rate limiting."""

    def __init__(self):
        super().__init__()
        self.sync_cache = {}
        self.cache_expiry = 300  # 5 minutes

    def load_data_from_sheets_enhanced(self):
        """Enhanced data loading from Google Sheets with caching and error recovery."""
        if not self.is_connected():
            logger.warning("Sheets not connected, using JSON fallback")
            return None

        try:
            logger.info("🔄 Starting enhanced data load from Google Sheets...")
            self.log_usage_stats()

            data = {
                "events": {"main_team": [], "team_2": [], "team_3": []},
                "blocked": {},
                "results": {"total_wins": 0, "total_losses": 0, "history": []},
                "player_stats": {},
                "ign_map": {},
                "absent": {},
                "notification_preferences": {"users": {}, "default_settings": {}}
            }

            # Load data with enhanced error handling and rate limiting
            loading_tasks = [
                ("Current Teams", self._load_current_teams_enhanced),
                ("Player Stats", self._load_player_stats_enhanced),
                ("Results History", self._load_results_history_enhanced),
                ("IGN Mappings", self._load_ign_mappings_enhanced),
                ("Notification Preferences", self._load_notification_preferences_enhanced)
            ]

            successful_loads = 0
            for task_name, load_func in loading_tasks:
                try:
                    logger.info(f"📊 Loading {task_name}...")
                    result = load_func(data)
                    if result:
                        successful_loads += 1
                        logger.info(f"✅ {task_name} loaded successfully")
                    else:
                        logger.warning(f"⚠️ {task_name} load returned no data")

                    # Smart delay between loads
                    self.smart_delay('small')

                except Exception as e:
                    logger.error(f"❌ Failed to load {task_name}: {e}")
                    # Continue with other loads even if one fails

            # Log final stats
            self.log_usage_stats()
            logger.info(f"✅ Enhanced data load complete: {successful_loads}/{len(loading_tasks)} successful")

            # Return data even if some loads failed
            return data if successful_loads > 0 else None

        except Exception as e:
            logger.error(f"❌ Enhanced data load failed: {e}")
            return None

    def _load_current_teams_enhanced(self, data: dict) -> bool:
        """Enhanced current teams loading with better parsing."""
        try:
            def _get_teams_data():
                try:
                    worksheet = self.spreadsheet.worksheet("Current Teams")
                    return worksheet.get_all_records()
                except gspread.WorksheetNotFound:
                    logger.info("Current Teams sheet not found, using defaults")
                    return []

            rows = self.rate_limited_request(_get_teams_data, 'read')

            if not rows:
                return True  # Empty is ok, use defaults

            # Parse team data with enhanced validation
            for row in rows:
                try:
                    team_name = row.get("Team", "").lower().strip()
                    players_str = row.get("Players", "")

                    # Map team names to keys
                    team_mapping = {
                        "main team": "main_team",
                        "🏆 main team": "main_team",
                        "team 2": "team_2", 
                        "🔸 team 2": "team_2",
                        "team 3": "team_3",
                        "🔸 team 3": "team_3"
                    }

                    team_key = team_mapping.get(team_name)
                    if team_key and team_key in data["events"]:
                        if players_str and players_str.strip():
                            # Parse player list more carefully
                            players = [p.strip() for p in players_str.split(",") if p.strip()]
                            data["events"][team_key] = players
                            logger.debug(f"Loaded {len(players)} players for {team_key}")

                except Exception as e:
                    logger.warning(f"Failed to parse team row: {row}, error: {e}")
                    continue

            return True

        except Exception as e:
            logger.error(f"Failed to load current teams: {e}")
            return False

    def _load_player_stats_enhanced(self, data: dict) -> bool:
        """Enhanced player stats loading with comprehensive validation."""
        try:
            def _get_player_data():
                try:
                    worksheet = self.spreadsheet.worksheet("Player Stats")
                    return worksheet.get_all_records()
                except gspread.WorksheetNotFound:
                    logger.info("Player Stats sheet not found, using defaults")
                    return []

            rows = self.rate_limited_request(_get_player_data, 'read')

            if not rows:
                return True

            # Enhanced player data parsing
            for row in rows:
                try:
                    # Handle emoji-prefixed headers and regular headers
                    user_id = str(row.get("User ID", "") or row.get("👤 User ID", "")).strip()

                    if not user_id or user_id in ["User ID", "👤 User ID", ""]:
                        continue

                    # Get names with fallbacks
                    ign = row.get("IGN", "") or row.get("🎮 In-Game Name", "") or row.get("Name", "")
                    display_name = row.get("Display Name", "") or row.get("📱 Discord Name", "") or f"User_{user_id}"

                    # Parse role and status
                    main_team_role = str(row.get("Main Team Role", "No") or "No").lower() == "yes"
                    blocked = str(row.get("Blocked Status", "No") or row.get("Blocked", "No") or "No").lower() == "yes"

                    # Parse numeric stats with error handling
                    def safe_int(value, default=0):
                        try:
                            return int(float(value or 0))
                        except (ValueError, TypeError):
                            return default

                    def safe_float(value, default=0.0):
                        try:
                            return float(value or 0)
                        except (ValueError, TypeError):
                            return default

                    # Team results parsing
                    team_results = {
                        "main_team": {
                            "wins": safe_int(row.get("Main Wins", 0)),
                            "losses": safe_int(row.get("Main Losses", 0))
                        },
                        "team_2": {
                            "wins": safe_int(row.get("Team2 Wins", 0)),
                            "losses": safe_int(row.get("Team2 Losses", 0))
                        },
                        "team_3": {
                            "wins": safe_int(row.get("Team3 Wins", 0)),
                            "losses": safe_int(row.get("Team3 Losses", 0))
                        }
                    }

                    # Specializations parsing
                    specializations = {
                        "cavalry": str(row.get("Cavalry", "No") or "No").lower() == "yes",
                        "mages": str(row.get("Mages", "No") or "No").lower() == "yes",
                        "archers": str(row.get("Archers", "No") or "No").lower() == "yes",
                        "infantry": str(row.get("Infantry", "No") or "No").lower() == "yes",
                        "whale": str(row.get("Whale Status", "No") or "No").lower() == "yes"
                    }

                    # Build comprehensive player stats
                    data["player_stats"][user_id] = {
                        "name": ign or display_name,
                        "display_name": display_name,
                        "main_team_role": main_team_role,
                        "team_results": team_results,
                        "absents": safe_int(row.get("Absents", 0)),
                        "blocked": blocked,
                        "power_rating": safe_int(row.get("Power Rating", 0)),
                        "specializations": specializations,
                        "total_wins": safe_int(row.get("Total Wins", 0)),
                        "total_losses": safe_int(row.get("Total Losses", 0)),
                        "win_rate": safe_float(row.get("Win Rate %", 0)),
                        "last_updated": row.get("Last Updated", "")
                    }

                    # Also update IGN map
                    if ign and ign != display_name:
                        data["ign_map"][user_id] = ign

                except Exception as e:
                    logger.warning(f"Failed to parse player row for user {user_id}: {e}")
                    continue

            logger.info(f"📊 Loaded {len(data['player_stats'])} player profiles from sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to load player stats: {e}")
            return False

    def _load_results_history_enhanced(self, data: dict) -> bool:
        """Enhanced results history loading with better data validation."""
        try:
            def _get_results_data():
                try:
                    worksheet = self.spreadsheet.worksheet("Results History")
                    return worksheet.get_all_records()
                except gspread.WorksheetNotFound:
                    logger.info("Results History sheet not found, using defaults")
                    return []

            rows = self.rate_limited_request(_get_results_data, 'read')

            if not rows:
                return True

            # Parse results with enhanced validation
            total_wins = 0
            total_losses = 0
            history = []

            for row in rows:
                try:
                    # Handle emoji-prefixed headers
                    date = row.get("Date", "") or row.get("📅 Date", "")
                    team = row.get("Team", "") or row.get("⚔️ Team", "")
                    result = row.get("Result", "") or row.get("🏆 Result", "")
                    players_str = row.get("Players", "") or row.get("👥 Players", "")
                    recorded_by = row.get("Recorded By", "") or row.get("📝 Recorded By", "") or row.get("By", "")

                    if not date or not team or not result:
                        continue

                    # Normalize team name
                    team_mapping = {
                        "main team": "main_team",
                        "🏆 main team": "main_team",
                        "team 2": "team_2",
                        "🔸 team 2": "team_2", 
                        "team 3": "team_3",
                        "🔸 team 3": "team_3"
                    }

                    normalized_team = team_mapping.get(team.lower().strip(), team.lower().replace(" ", "_"))
                    normalized_result = result.lower().strip()

                    if normalized_result in ["win", "victory", "✅ victory"]:
                        normalized_result = "win"
                        total_wins += 1
                    elif normalized_result in ["loss", "defeat", "❌ defeat"]:
                        normalized_result = "loss"
                        total_losses += 1
                    else:
                        continue  # Skip invalid results

                    # Parse players list
                    players = []
                    if players_str and players_str.strip():
                        players = [p.strip() for p in players_str.split(",") if p.strip()]

                    # Build history entry
                    history_entry = {
                        "date": date,
                        "timestamp": date,  # Use date as timestamp fallback
                        "team": normalized_team,
                        "result": normalized_result,
                        "players": players,
                        "by": recorded_by,
                        "recorded_by": recorded_by
                    }

                    history.append(history_entry)

                except Exception as e:
                    logger.warning(f"Failed to parse result row: {e}")
                    continue

            # Update results data
            data["results"] = {
                "total_wins": total_wins,
                "total_losses": total_losses,
                "history": history
            }

            logger.info(f"📊 Loaded {len(history)} results ({total_wins}W/{total_losses}L)")
            return True

        except Exception as e:
            logger.error(f"Failed to load results history: {e}")
            return False

    def _load_ign_mappings_enhanced(self, data: dict) -> bool:
        """Enhanced IGN mappings loading."""
        try:
            def _get_ign_data():
                try:
                    worksheet = self.spreadsheet.worksheet("IGN Mappings")
                    return worksheet.get_all_records()
                except gspread.WorksheetNotFound:
                    logger.info("IGN Mappings sheet not found, using defaults")
                    return []

            rows = self.rate_limited_request(_get_ign_data, 'read')

            if not rows:
                return True

            # Parse IGN mappings
            for row in rows:
                try:
                    user_id = str(row.get("User ID", "") or row.get("👤 User ID", "")).strip()
                    ign = row.get("In-Game Name", "") or row.get("🎮 In-Game Name", "")

                    if user_id and ign and user_id not in ["User ID", "👤 User ID"]:
                        data["ign_map"][user_id] = ign.strip()

                except Exception as e:
                    logger.warning(f"Failed to parse IGN row: {e}")
                    continue

            logger.info(f"📊 Loaded {len(data['ign_map'])} IGN mappings")
            return True

        except Exception as e:
            logger.error(f"Failed to load IGN mappings: {e}")
            return False

    def _load_notification_preferences_enhanced(self, data: dict) -> bool:
        """Enhanced notification preferences loading."""
        try:
            def _get_notification_data():
                try:
                    worksheet = self.spreadsheet.worksheet("Notification Preferences")
                    return worksheet.get_all_records()
                except gspread.WorksheetNotFound:
                    logger.info("Notification Preferences sheet not found, using defaults")
                    return []

            rows = self.rate_limited_request(_get_notification_data, 'read')

            if not rows:
                return True

            # Parse notification preferences
            users_prefs = {}
            for row in rows:
                try:
                    user_id = str(row.get("User ID", "") or row.get("👤 User ID", "")).strip()

                    if not user_id or user_id in ["User ID", "👤 User ID"]:
                        continue

                    # Parse preference settings
                    def parse_bool(value):
                        return str(value or "").lower() in ["yes", "✅ enabled", "enabled", "true"]

                    event_reminders = parse_bool(row.get("Event Reminders", "") or row.get("📢 Event Alerts", ""))
                    result_notifications = parse_bool(row.get("Result Notifications", "") or row.get("🏆 Result Notifications", ""))
                    team_updates = parse_bool(row.get("Team Updates", "") or row.get("👥 Team Updates", ""))
                    dm_notifications = parse_bool(row.get("DM Notifications", "") or row.get("📱 DM Notifications", ""))

                    # Parse timing preferences
                    reminder_time_str = row.get("Reminder Times", "") or row.get("🕐 Reminder Time", "") or "60 minutes"
                    try:
                        if "minute" in reminder_time_str.lower():
                            reminder_minutes = int(reminder_time_str.split()[0])
                        else:
                            reminder_minutes = 60
                    except:
                        reminder_minutes = 60

                    # Parse timezone
                    timezone_str = row.get("Timezone", "") or row.get("🌍 Timezone", "") or "UTC+0"
                    try:
                        if "UTC" in timezone_str:
                            offset_part = timezone_str.replace("UTC", "").strip()
                            if not offset_part or offset_part == "+":
                                timezone_offset = 0
                            else:
                                timezone_offset = int(offset_part)
                        else:
                            timezone_offset = 0
                    except:
                        timezone_offset = 0

                    # Build user preferences
                    users_prefs[user_id] = {
                        "display_name": row.get("Display Name", "") or row.get("📝 Display Name", "") or f"User_{user_id}",
                        "event_reminders": event_reminders,
                        "result_notifications": result_notifications,
                        "team_updates": team_updates,
                        "method": "dm" if dm_notifications else "channel",
                        "reminder_times": [reminder_minutes, 15],
                        "timezone_offset": timezone_offset
                    }

                except Exception as e:
                    logger.warning(f"Failed to parse notification preferences for {user_id}: {e}")
                    continue

            # Set notification preferences data
            data["notification_preferences"] = {
                "users": users_prefs,
                "default_settings": {
                    "method": "channel",
                    "event_reminders": True,
                    "result_notifications": True,
                    "team_updates": True,
                    "reminder_times": [60, 15],
                    "quiet_hours": {"start": 22, "end": 8},
                    "timezone_offset": 0
                }
            }

            logger.info(f"📊 Loaded notification preferences for {len(users_prefs)} users")
            return True

        except Exception as e:
            logger.error(f"Failed to load notification preferences: {e}")
            return False

    def sync_notification_preferences_enhanced(self, notification_prefs: dict) -> bool:
        """Enhanced notification preferences sync with better formatting."""
        if not self.spreadsheet:
            return False

        try:
            def _setup_notification_sheet():
                try:
                    worksheet = self.spreadsheet.worksheet("Notification Preferences")
                    worksheet.clear()
                except gspread.WorksheetNotFound:
                    worksheet = self.spreadsheet.add_worksheet(title="Notification Preferences", rows="200", cols="10")

                # Enhanced headers
                headers = [
                    "👤 User ID", "📝 Display Name", "📢 Event Alerts", "🏆 Result Notifications", 
                    "👥 Team Updates", "📱 DM Notifications", "🕐 Reminder Time", 
                    "🌍 Timezone", "🌙 Quiet Hours", "📅 Last Updated"
                ]
                worksheet.append_row(headers)
                return worksheet

            worksheet = self.rate_limited_request(_setup_notification_sheet, 'write')

            # Apply enhanced header formatting
            def _format_notification_headers():
                worksheet.format("A1:J1", {
                    "backgroundColor": {"red": 0.4, "green": 0.7, "blue": 0.4},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 12,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER"
                })
                worksheet.freeze(rows=1)

            self.rate_limited_request(_format_notification_headers, 'write')

            # Prepare batch data
            users_data = notification_prefs.get("users", {})
            default_settings = notification_prefs.get("default_settings", {})

            batch_data = []
            for user_id, prefs in users_data.items():
                try:
                    # Merge with defaults
                    merged_prefs = default_settings.copy()
                    merged_prefs.update(prefs)

                    display_name = prefs.get("display_name", f"User_{user_id}")
                    event_alerts = "✅ Enabled" if merged_prefs.get("event_reminders", True) else "❌ Disabled"
                    result_notifications = "✅ Enabled" if merged_prefs.get("result_notifications", True) else "❌ Disabled"
                    team_updates = "✅ Enabled" if merged_prefs.get("team_updates", True) else "❌ Disabled"
                    dm_notifications = "✅ Enabled" if merged_prefs.get("method", "channel") in ["dm", "both"] else "❌ Disabled"

                    reminder_times = merged_prefs.get("reminder_times", [60, 15])
                    reminder_time = f"{reminder_times[0]} minutes" if reminder_times else "60 minutes"

                    timezone_offset = merged_prefs.get("timezone_offset", 0)
                    timezone = f"UTC{timezone_offset:+d}" if timezone_offset != 0 else "UTC+0"

                    quiet_hours = merged_prefs.get("quiet_hours", {"start": 22, "end": 8})
                    quiet_hours_str = f"{quiet_hours['start']:02d}:00-{quiet_hours['end']:02d}:00"

                    row_data = [
                        user_id, display_name, event_alerts, result_notifications, team_updates,
                        dm_notifications, reminder_time, timezone, quiet_hours_str,
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    ]
                    batch_data.append(row_data)

                except Exception as e:
                    logger.warning(f"Failed to prepare notification data for {user_id}: {e}")
                    continue

            # Add batch data with rate limiting
            if batch_data:
                batch_size = 50
                for i in range(0, len(batch_data), batch_size):
                    batch = batch_data[i:i + batch_size]

                    def _add_notification_batch():
                        worksheet.append_rows(batch)

                    self.rate_limited_request(_add_notification_batch, 'write')

                    if i + batch_size < len(batch_data):
                        self.smart_delay('medium')

            # Apply data formatting
            def _format_notification_data():
                worksheet.format("A2:J200", {
                    "textFormat": {"fontSize": 10},
                    "horizontalAlignment": "CENTER",
                    "borders": {"style": "SOLID", "width": 1}
                })
                worksheet.columns_auto_resize(0, 10)

            self.rate_limited_request(_format_notification_data, 'write')

            logger.info(f"✅ Enhanced notification preferences sync: {len(users_data)} users")
            return True

        except Exception as e:
            logger.error(f"❌ Enhanced notification preferences sync failed: {e}")
            return False

    def get_cached_data(self, key: str):
        """Get cached data if still valid."""
        if key in self.sync_cache:
            cached_time, data = self.sync_cache[key]
            if time.time() - cached_time < self.cache_expiry:
                return data
        return None

    def set_cached_data(self, key: str, data):
        """Set data in cache with timestamp."""
        self.sync_cache[key] = (time.time(), data)

    def clear_cache(self):
        """Clear all cached data."""
        self.sync_cache.clear()
        logger.info("🔄 Data sync cache cleared")

    def validate_loaded_data(self, data: dict) -> bool:
        """Validate the structure and content of loaded data."""
        try:
            required_keys = ["events", "blocked", "results", "player_stats", "ign_map", "absent"]

            for key in required_keys:
                if key not in data:
                    logger.error(f"❌ Missing required data key: {key}")
                    return False

            # Validate events structure
            events = data["events"]
            if not isinstance(events, dict):
                logger.error("❌ Events data is not a dictionary")
                return False

            for team in ["main_team", "team_2", "team_3"]:
                if team not in events or not isinstance(events[team], list):
                    logger.error(f"❌ Invalid team data for {team}")
                    return False

            # Validate results structure
            results = data["results"]
            if not isinstance(results, dict):
                logger.error("❌ Results data is not a dictionary")
                return False

            required_result_keys = ["total_wins", "total_losses", "history"]
            for key in required_result_keys:
                if key not in results:
                    logger.error(f"❌ Missing results key: {key}")
                    return False

            # Basic type validation
            if (not isinstance(results["total_wins"], int) or 
                not isinstance(results["total_losses"], int) or
                not isinstance(results["history"], list)):
                logger.error("❌ Invalid results data types")
                return False

            logger.info("✅ Data validation passed")
            return True

        except Exception as e:
            logger.error(f"❌ Data validation failed: {e}")
            return False


# Main export class
class EnhancedDataSyncManager(EnhancedDataSync):
    """Main enhanced data sync manager with all features."""
    pass


from datetime import datetime
from .worksheet_handlers import WorksheetHandlers
from utils.logger import setup_logger

logger = setup_logger("data_sync")

class DataSync(WorksheetHandlers):
    """Handles data synchronization operations."""

    def sync_all_data(self, all_data):
        """Sync all bot data to sheets."""
        if not self.is_connected():
            return False

        try:
            success_count = 0
            
            # Sync current teams
            if self.sync_current_teams(all_data.get("events", {})):
                success_count += 1
                
            # Sync results history  
            if self.sync_results_history(all_data.get("results", {})):
                success_count += 1
                
            # Create player stats template
            if self.create_player_stats_template(all_data.get("player_stats", {})):
                success_count += 1

            logger.info(f"✅ Data sync completed: {success_count}/3 operations successful")
            return success_count >= 2
            
        except Exception as e:
            logger.error(f"❌ Data sync failed: {e}")
            return False

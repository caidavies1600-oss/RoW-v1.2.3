"""
Startup data validation and repair system.

Features:
- Automatic data structure validation
- File existence verification
- Data type standardization
- Corrupted file recovery
- User ID normalization
- IGN mapping fixes

Components:
- File structure validation
- Data consistency checks
- Recovery mechanisms
- Logging system
"""

import json
import os

from utils.logger import setup_logger

logger = setup_logger("startup_fixer")


class StartupDataFixer:
    """
    Automatically fixes data inconsistencies on bot startup.

    Features:
    - Missing file creation
    - Data structure repair
    - User ID standardization
    - Corruption recovery
    - IGN mapping fixes
    - Logging of applied fixes

    Attributes:
        bot: Discord bot instance
        fixes_applied: List of fixes performed
    """

    def __init__(self, bot=None):
        self.bot = bot
        self.fixes_applied = []

    def run_startup_fixes(self) -> bool:
        """Run all critical data fixes on startup. Returns success status."""
        logger.info("🚀 Running automatic startup data fixes...")

        try:
            # Since Google Sheets is the source of truth, we can be aggressive
            self.ensure_all_files_exist()
            self.fix_events_data_structure()
            self.standardize_user_ids()
            self.clean_corrupted_files()

            if self.fixes_applied:
                logger.info(
                    f"✅ Startup fixes completed: {len(self.fixes_applied)} fixes applied"
                )
                for fix in self.fixes_applied[:10]:  # Log first 10 fixes
                    logger.info(f"  🔧 {fix}")
                if len(self.fixes_applied) > 10:
                    logger.info(f"  ... and {len(self.fixes_applied) - 10} more fixes")
            else:
                logger.info("✅ All data files are healthy, no fixes needed")

            return True

        except Exception as e:
            logger.error(f"❌ Startup data fix failed: {e}")
            return False

    def ensure_all_files_exist(self):
        """Create missing data files with clean defaults."""
        from config.constants import DEFAULT_TIMES, FILES

        file_defaults = {
            FILES["EVENTS"]: {"main_team": [], "team_2": [], "team_3": []},
            FILES["BLOCKED"]: {},
            FILES["IGN_MAP"]: {},
            FILES["RESULTS"]: {"total_wins": 0, "total_losses": 0, "history": []},
            FILES["HISTORY"]: [],
            FILES["TIMES"]: DEFAULT_TIMES,
            FILES["ABSENT"]: {},
            FILES["SIGNUP_LOCK"]: False,
        }

        for file_path, default_data in file_defaults.items():
            try:
                # Create directory if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                if not os.path.exists(file_path):
                    self._save_json(file_path, default_data)
                    self.fixes_applied.append(
                        f"Created missing file: {os.path.basename(file_path)}"
                    )

            except Exception as e:
                logger.warning(f"Failed to create {file_path}: {e}")

    def fix_events_data_structure(self):
        """Fix events.json structure and data types."""
        from config.constants import FILES

        try:
            events = self._load_json(
                FILES["EVENTS"], {"main_team": [], "team_2": [], "team_3": []}
            )
            ign_map = self._load_json(FILES["IGN_MAP"], {})

            # Ensure proper structure
            if not isinstance(events, dict):
                events = {"main_team": [], "team_2": [], "team_3": []}
                self.fixes_applied.append("Reset events.json structure")

            # Fix each team
            for team_key in ["main_team", "team_2", "team_3"]:
                if team_key not in events:
                    events[team_key] = []
                    self.fixes_applied.append(f"Added missing team: {team_key}")
                    continue

                if not isinstance(events[team_key], list):
                    events[team_key] = []
                    self.fixes_applied.append(f"Fixed team {team_key} to be a list")
                    continue

                # Convert user IDs to IGNs
                fixed_members = []
                for member in events[team_key]:
                    if isinstance(member, int):
                        # Convert user ID to IGN
                        user_id_str = str(member)
                        if user_id_str in ign_map:
                            fixed_members.append(ign_map[user_id_str])
                            self.fixes_applied.append(
                                f"Converted user ID {member} to IGN in {team_key}"
                            )
                        else:
                            # Try to get from bot
                            if self.bot:
                                try:
                                    user = self.bot.get_user(member)
                                    if user:
                                        ign = user.display_name
                                        fixed_members.append(ign)
                                        # Update IGN map
                                        ign_map[user_id_str] = ign
                                        self.fixes_applied.append(
                                            f"Added new IGN mapping: {member} -> {ign}"
                                        )
                                    else:
                                        # User not found, skip
                                        self.fixes_applied.append(
                                            f"Removed invalid user ID {member} from {team_key}"
                                        )
                                except:
                                    # Keep as placeholder
                                    fixed_members.append(f"User_{member}")
                                    self.fixes_applied.append(
                                        f"Converted unknown user ID {member} to placeholder"
                                    )
                            else:
                                # No bot available, use placeholder
                                fixed_members.append(f"User_{member}")

                    elif isinstance(member, str):
                        # Already IGN, but clean it
                        cleaned = member.strip()
                        if cleaned and len(cleaned) >= 2:
                            fixed_members.append(cleaned)
                            if cleaned != member:
                                self.fixes_applied.append(
                                    f"Cleaned IGN: '{member}' -> '{cleaned}'"
                                )
                        else:
                            self.fixes_applied.append(
                                f"Removed invalid IGN '{member}' from {team_key}"
                            )

                    else:
                        # Invalid type, remove
                        self.fixes_applied.append(
                            f"Removed invalid member type {type(member)} from {team_key}"
                        )

                events[team_key] = fixed_members

            # Save fixed files
            self._save_json(FILES["EVENTS"], events)
            self._save_json(FILES["IGN_MAP"], ign_map)

        except Exception as e:
            logger.warning(f"Failed to fix events data: {e}")

    def standardize_user_ids(self):
        """Ensure all user IDs are strings across all files."""
        from config.constants import FILES

        user_id_files = [
            (FILES["BLOCKED"], "blocked_users.json"),
            (FILES["IGN_MAP"], "ign_map.json"),
            (FILES["ABSENT"], "absent_users.json"),
        ]

        for file_path, file_name in user_id_files:
            try:
                if not os.path.exists(file_path):
                    continue

                data = self._load_json(file_path, {})
                if not isinstance(data, dict):
                    continue

                fixed_data = {}
                needs_fix = False

                for key, value in data.items():
                    str_key = str(key)
                    fixed_data[str_key] = value
                    if str_key != key:
                        needs_fix = True

                if needs_fix:
                    self._save_json(file_path, fixed_data)
                    self.fixes_applied.append(f"Standardized user IDs in {file_name}")

            except Exception as e:
                logger.warning(f"Failed to standardize {file_name}: {e}")

    def clean_corrupted_files(self):
        """Clean up corrupted or malformed JSON files."""
        from config.constants import FILES

        critical_files = [
            (FILES["EVENTS"], {"main_team": [], "team_2": [], "team_3": []}),
            (FILES["BLOCKED"], {}),
            (FILES["IGN_MAP"], {}),
            (FILES["RESULTS"], {"total_wins": 0, "total_losses": 0, "history": []}),
            (FILES["ABSENT"], {}),
        ]

        for file_path, default_data in critical_files:
            try:
                if not os.path.exists(file_path):
                    continue

                # Try to load and validate
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Basic validation
                    if not self._validate_file_structure(file_path, data):
                        raise ValueError("Invalid structure")

                except (json.JSONDecodeError, ValueError, TypeError):
                    # File is corrupted, reset it
                    self._save_json(file_path, default_data)
                    self.fixes_applied.append(
                        f"Reset corrupted file: {os.path.basename(file_path)}"
                    )

            except Exception as e:
                logger.warning(f"Failed to clean {file_path}: {e}")

    def _validate_file_structure(self, file_path: str, data) -> bool:
        """
        Validate basic file structure.

        Args:
            file_path: Path to JSON file
            data: Loaded JSON data

        Returns:
            bool: True if structure is valid

        Validates:
        - Data type correctness
        - Required keys presence
        - List/dict structure
        - Team data format
        """
        from config.constants import FILES

        try:
            if file_path == FILES["EVENTS"]:
                return (
                    isinstance(data, dict)
                    and all(team in data for team in ["main_team", "team_2", "team_3"])
                    and all(
                        isinstance(data[team], list)
                        for team in ["main_team", "team_2", "team_3"]
                    )
                )

            elif file_path == FILES["RESULTS"]:
                return (
                    isinstance(data, dict)
                    and "total_wins" in data
                    and "total_losses" in data
                    and "history" in data
                    and isinstance(data["history"], list)
                )

            elif file_path in [FILES["BLOCKED"], FILES["IGN_MAP"], FILES["ABSENT"]]:
                return isinstance(data, dict)

            else:
                return True  # Unknown file, assume valid

        except:
            return False

    def _load_json(self, file_path: str, default=None):
        """
        Load JSON with fallback.

        Args:
            file_path: Path to JSON file
            default: Default value if load fails

        Returns:
            Any: Loaded JSON data or default

        Features:
        - UTF-8 encoding
        - Error recovery
        - Default fallback
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return default

    def _save_json(self, file_path: str, data) -> bool:
        """
        Save JSON safely.

        Args:
            file_path: Path to JSON file
            data: Data to save

        Returns:
            bool: Success status

        Features:
        - Directory creation
        - UTF-8 encoding
        - Error handling
        - Pretty printing
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")
            return False


# Convenience function
def run_startup_data_fixes(bot=None) -> bool:
    """Run startup data fixes. Call this from bot startup."""
    fixer = StartupDataFixer(bot)
    return fixer.run_startup_fixes()

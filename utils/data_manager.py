import os
import json
from typing import Any
from utils.logger import setup_logger

logger = setup_logger("data_manager")

class DataManager:
    """Utility class for JSON file operations with validation."""

    @staticmethod
    def load_json(filepath: str, default: Any = None) -> Any:
        """Load JSON data from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
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

    @staticmethod
    def save_json(filepath: str, data: Any) -> bool:
        """Save data to JSON file with error handling."""
        try:
            dirname = os.path.dirname(filepath)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            logger.debug(f"Successfully saved {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
            return False

    @staticmethod
    def ensure_data_files_exist():
        """Ensure all required data files exist with proper defaults."""
        from config.constants import FILES
        try:
            from config.constants import DEFAULT_TIMES
        except ImportError:
            # Fallback if DEFAULT_TIMES is not defined
            DEFAULT_TIMES = {
                "row_start": "19:00",
                "signup_reminder": "18:30"
            }

        file_defaults = {
            FILES["EVENTS"]: {"main_team": [], "team_2": [], "team_3": []},
            FILES["BLOCKED"]: {},
            FILES["IGN_MAP"]: {},
            FILES["RESULTS"]: {"total_wins": 0, "total_losses": 0, "history": []},
            FILES["HISTORY"]: [],
            FILES["TIMES"]: DEFAULT_TIMES,
            FILES["ABSENT"]: {}
        }

        created_files = []
        for filepath, default_data in file_defaults.items():
            try:
                # Create directory if it doesn't exist
                dirname = os.path.dirname(filepath)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)

                # Create file if it doesn't exist
                if not os.path.exists(filepath):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, indent=4, ensure_ascii=False)
                    logger.info(f"✅ Created missing data file: {filepath}")
                    created_files.append(filepath)

            except Exception as e:
                logger.error(f"❌ Failed to create {filepath}: {e}")

        return created_files

    @staticmethod
    def validate_data_integrity():
        """Validate existing data files for corruption."""
        from config.constants import FILES

        issues = []

        try:
            # Check events.json structure
            events = DataManager.load_json(FILES["EVENTS"], {})
            if not isinstance(events, dict):
                issues.append("events.json is not a dictionary")
            else:
                for team in ["main_team", "team_2", "team_3"]:
                    if team not in events:
                        issues.append(f"events.json missing {team}")
                    elif not isinstance(events[team], list):
                        issues.append(f"events.json {team} is not a list")
                    else:
                        # Check for mixed user ID types
                        for i, member in enumerate(events[team]):
                            if isinstance(member, int):
                                issues.append(f"events.json {team}[{i}] contains integer user ID: {member}")

            # Check ign_map.json structure  
            ign_map = DataManager.load_json(FILES["IGN_MAP"], {})
            if not isinstance(ign_map, dict):
                issues.append("ign_map.json is not a dictionary")
            else:
                for user_id in ign_map.keys():
                    if not isinstance(user_id, str):
                        issues.append(f"ign_map.json contains non-string key: {user_id} ({type(user_id)})")

            # Check blocked_users.json structure
            blocked = DataManager.load_json(FILES["BLOCKED"], {})
            if not isinstance(blocked, dict):
                issues.append("blocked_users.json is not a dictionary")
            else:
                for user_id in blocked.keys():
                    if not isinstance(user_id, str):
                        issues.append(f"blocked_users.json contains non-string key: {user_id} ({type(user_id)})")

            # Check results.json structure
            results = DataManager.load_json(FILES["RESULTS"], {})
            if not isinstance(results, dict):
                issues.append("results.json is not a dictionary")
            else:
                required_keys = ["total_wins", "total_losses", "history"]
                for key in required_keys:
                    if key not in results:
                        issues.append(f"results.json missing required key: {key}")

        except Exception as e:
            issues.append(f"Error during validation: {e}")

        return issues

    @staticmethod
    def migrate_user_ids_to_strings():
        """Convert integer user IDs to strings for consistency."""
        from config.constants import FILES

        migrated_files = []

        try:
            # Migrate events.json
            events = DataManager.load_json(FILES["EVENTS"], {})
            events_migrated = False

            for team, members in events.items():
                new_members = []
                for member in members:
                    if isinstance(member, int):
                        new_members.append(str(member))
                        events_migrated = True
                        logger.info(f"Migrated user ID {member} to string in {team}")
                    else:
                        new_members.append(member)
                events[team] = new_members

            if events_migrated:
                if DataManager.save_json(FILES["EVENTS"], events):
                    logger.info("✅ Successfully migrated events.json user IDs to strings")
                    migrated_files.append("events.json")
                else:
                    logger.error("❌ Failed to save migrated events.json")

            # Note: ign_map.json and blocked_users.json should already use string keys
            # as they come from JSON which converts all keys to strings

        except Exception as e:
            logger.error(f"❌ Error during user ID migration: {e}")

        return migrated_files

    @staticmethod
    def backup_data_files():
        """Create backup copies of all data files."""
        from config.constants import FILES
        from datetime import datetime

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(FILES["EVENTS"]), "backups", timestamp)

        try:
            os.makedirs(backup_dir, exist_ok=True)
            backed_up = []

            for file_key, filepath in FILES.items():
                if os.path.exists(filepath):
                    filename = os.path.basename(filepath)
                    backup_path = os.path.join(backup_dir, filename)

                    # Copy file content
                    with open(filepath, 'r', encoding='utf-8') as src:
                        content = src.read()
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(content)

                    backed_up.append(filename)

            if backed_up:
                logger.info(f"✅ Backed up {len(backed_up)} files to {backup_dir}")
                return backup_dir
            else:
                logger.warning("⚠️ No files found to backup")
                return None

        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            return None

    @staticmethod
    def run_critical_startup_checks():
        """Run all critical data checks at startup."""
        logger.info("🔄 Running critical startup checks...")

        # 1. Ensure data files exist
        created_files = DataManager.ensure_data_files_exist()
        if created_files:
            logger.info(f"✅ Created {len(created_files)} missing data files")

        # 2. Validate data integrity
        issues = DataManager.validate_data_integrity()
        if issues:
            logger.warning("⚠️ Data integrity issues found:")
            for issue in issues:
                logger.warning(f"  - {issue}")

            # 3. Attempt to migrate user IDs if needed
            migrated = DataManager.migrate_user_ids_to_strings()
            if migrated:
                logger.info(f"✅ Migrated user IDs in: {', '.join(migrated)}")

                # Re-validate after migration
                post_issues = DataManager.validate_data_integrity()
                if post_issues:
                    logger.warning("⚠️ Some issues remain after migration:")
                    for issue in post_issues:
                        logger.warning(f"  - {issue}")
                else:
                    logger.info("✅ All data integrity issues resolved")
        else:
            logger.info("✅ Data integrity validation passed")

        # 4. Create backup
        backup_dir = DataManager.backup_data_files()
        if backup_dir:
            logger.info(f"✅ Data backup created: {backup_dir}")

        logger.info("✅ Critical startup checks completed")
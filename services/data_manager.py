"""Data management service for the Discord RoW bot."""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger

logger = setup_logger("data_manager")

class DataManager:
    """Handles all data persistence operations."""

    @staticmethod
    def load_json(filepath: str, default: Any = None) -> Any:
        """Load JSON data from file with fallback to default."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.info(f"File {filepath} doesn't exist, using default")
                return default if default is not None else {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            return default if default is not None else {}
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return default if default is not None else {}

    @staticmethod
    def save_json(filepath: str, data: Any) -> bool:
        """Save data to JSON file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
            return False

    @staticmethod
    def backup_data_files() -> Optional[str]:
        """Create backup of all data files."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"data/backups/backup_{timestamp}"

            if os.path.exists("data"):
                shutil.copytree("data", backup_dir, ignore=shutil.ignore_patterns("backups"))
                logger.info(f"✅ Data backup created: {backup_dir}")
                return backup_dir
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
        return None
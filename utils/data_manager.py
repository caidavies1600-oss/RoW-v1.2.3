import os
import json
from typing import Any
from utils.logger import setup_logger

logger = setup_logger("data_manager")


class DataManager:
    """Utility class for JSON file operations."""

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

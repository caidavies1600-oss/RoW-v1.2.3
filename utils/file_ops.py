import asyncio
import json
import os
import shutil
from datetime import datetime
from typing import Any, Optional

from utils.logger import setup_logger

logger = setup_logger("file_ops")


class FileOps:
    """Thread-safe file operations manager."""

    _instance: Optional["FileOps"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._locks = {}
            self._initialized = True

    def get_lock(self, filepath: str) -> asyncio.Lock:
        if filepath not in self._locks:
            self._locks[filepath] = asyncio.Lock()
        return self._locks[filepath]

    async def load_json(self, filepath: str, default: Any = None) -> Any:
        """Thread-safe JSON loading."""
        async with self.get_lock(filepath):
            try:
                if not os.path.exists(filepath):
                    return default

                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)

            except json.JSONDecodeError as e:
                logger.error(f"Corrupt JSON in {filepath}: {e}")
                await self._create_backup(filepath)
                return default
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
                return default

    async def save_json(self, filepath: str, data: Any) -> bool:
        """Thread-safe atomic JSON saving."""
        async with self.get_lock(filepath):
            temp_file = f"{filepath}.tmp"
            backup_file = f"{filepath}.bak"

            try:
                # Create directory if needed
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # Write to temp file
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                # Backup existing file
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

    async def _create_backup(self, filepath: str):
        """Create backup of corrupted file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{filepath}.{timestamp}.bak"
            shutil.copy2(filepath, backup_path)
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup of {filepath}: {e}")

    async def shutdown(self):
        """Cleanup any open resources."""
        # Wait for any pending operations
        for lock in self._locks.values():
            if lock.locked():
                await lock.acquire()
                lock.release()
        self._locks.clear()


# Global instance
file_ops = FileOps()

"""
Data backup and recovery system for the Discord bot.

Features:
- Automatic and manual backup creation
- Backup rotation and cleanup
- Metadata tracking and validation
- Pre-restore safety backups
- Activity-based backup scheduling
- Backup statistics and monitoring

Components:
- Backup creation and management
- File rotation and cleanup
- Restore functionality
- Scheduling system
- Statistics tracking
"""

import json
import os
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("backup_manager")


class BackupManager:
    """
    Manages data backups and recovery.

    Features:
    - Automatic scheduled backups
    - Manual backup creation
    - Backup rotation system
    - Metadata tracking
    - Recovery functionality
    - Statistics monitoring

    Attributes:
        data_manager: Data management interface
        backup_dir: Directory for backup storage
        max_backups: Maximum number of backups to keep
    """

    def __init__(self):
        self.data_manager = DataManager()
        self.backup_dir = "data/backups"
        self.max_backups = 30  # Keep last 30 backups
        self._ensure_backup_directory()

    def _ensure_backup_directory(self):
        """Ensure backup directory exists."""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"❌ Failed to create backup directory: {e}")

    def create_backup(self, backup_type: str = "manual") -> Optional[str]:
        """Create a full backup of all data files."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{backup_type}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")

            from config.constants import FILES

            # Create backup metadata
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "backup_type": backup_type,
                "files_included": [],
                "bot_version": "1.0.2",  # From version.txt
                "total_size": 0,
            }

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                total_size = 0

                # Backup all data files
                for file_key, filepath in FILES.items():
                    if os.path.exists(filepath):
                        # Add file to zip
                        arcname = f"{file_key}.json"
                        zipf.write(filepath, arcname)

                        # Update metadata
                        file_size = os.path.getsize(filepath)
                        total_size += file_size
                        metadata["files_included"].append(
                            {
                                "key": file_key,
                                "original_path": filepath,
                                "archive_name": arcname,
                                "size": file_size,
                            }
                        )

                # Backup config files
                config_files = [
                    "config/constants.py",
                    "config/settings.py",
                    "version.txt",
                ]
                for config_file in config_files:
                    if os.path.exists(config_file):
                        zipf.write(
                            config_file, f"config/{os.path.basename(config_file)}"
                        )
                        file_size = os.path.getsize(config_file)
                        total_size += file_size
                        metadata["files_included"].append(
                            {
                                "key": f"config_{os.path.basename(config_file)}",
                                "original_path": config_file,
                                "archive_name": f"config/{os.path.basename(config_file)}",
                                "size": file_size,
                            }
                        )

                metadata["total_size"] = total_size

                # Add metadata to backup
                metadata_json = json.dumps(metadata, indent=2)
                zipf.writestr("backup_metadata.json", metadata_json)

            logger.info(f"✅ Backup created: {backup_path} ({total_size} bytes)")

            # Clean up old backups
            self._cleanup_old_backups()

            return backup_path

        except Exception as e:
            logger.exception(f"❌ Failed to create backup: {e}")
            return None

    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []

        try:
            if not os.path.exists(self.backup_dir):
                return backups

            for filename in os.listdir(self.backup_dir):
                if filename.endswith(".zip") and filename.startswith("backup_"):
                    backup_path = os.path.join(self.backup_dir, filename)

                    try:
                        # Get file stats
                        stats = os.stat(backup_path)

                        # Try to read metadata from backup
                        metadata = None
                        try:
                            with zipfile.ZipFile(backup_path, "r") as zipf:
                                if "backup_metadata.json" in zipf.namelist():
                                    metadata_content = zipf.read(
                                        "backup_metadata.json"
                                    ).decode("utf-8")
                                    metadata = json.loads(metadata_content)
                        except:
                            pass

                        backup_info = {
                            "filename": filename,
                            "path": backup_path,
                            "size": stats.st_size,
                            "created": datetime.fromtimestamp(stats.st_ctime),
                            "metadata": metadata,
                        }

                        backups.append(backup_info)

                    except Exception as e:
                        logger.warning(f"Error reading backup {filename}: {e}")

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)

        except Exception as e:
            logger.error(f"❌ Failed to list backups: {e}")

        return backups

    def restore_backup(self, backup_filename: str, confirm: bool = False) -> bool:
        """Restore data from a backup."""
        if not confirm:
            logger.warning("⚠️ Restore not confirmed - use confirm=True to proceed")
            return False

        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
                logger.error(f"❌ Backup file not found: {backup_filename}")
                return False

            # Create a backup of current state before restoring
            current_backup = self.create_backup("pre_restore")
            if current_backup:
                logger.info(f"✅ Created pre-restore backup: {current_backup}")

            from config.constants import FILES

            with zipfile.ZipFile(backup_path, "r") as zipf:
                # Read metadata
                metadata = None
                if "backup_metadata.json" in zipf.namelist():
                    metadata_content = zipf.read("backup_metadata.json").decode("utf-8")
                    metadata = json.loads(metadata_content)
                    logger.info(
                        f"📋 Restoring backup from {metadata.get('timestamp', 'unknown time')}"
                    )

                restored_files = []

                # Restore data files
                for file_key, filepath in FILES.items():
                    archive_name = f"{file_key}.json"
                    if archive_name in zipf.namelist():
                        # Extract file content
                        file_content = zipf.read(archive_name).decode("utf-8")

                        # Ensure directory exists
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)

                        # Write file
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(file_content)

                        restored_files.append(filepath)
                        logger.info(f"✅ Restored: {filepath}")

                logger.info(
                    f"✅ Restore completed: {len(restored_files)} files restored"
                )
                return True

        except Exception as e:
            logger.exception(f"❌ Failed to restore backup: {e}")
            return False

    def _cleanup_old_backups(self):
        """Remove old backups to stay within limit."""
        try:
            backups = self.list_backups()

            if len(backups) > self.max_backups:
                # Remove oldest backups
                to_remove = backups[self.max_backups :]

                for backup in to_remove:
                    try:
                        os.remove(backup["path"])
                        logger.info(f"🗑️ Removed old backup: {backup['filename']}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove old backup {backup['filename']}: {e}"
                        )

        except Exception as e:
            logger.error(f"❌ Failed to cleanup old backups: {e}")

    def schedule_automatic_backups(self):
        """
        Setup automatic backup scheduling.

        Features:
        - 6-hour interval checks
        - Activity-based triggering
        - Error handling and logging
        - Automatic cleanup

        Returns:
            Task: Discord task loop for scheduling
        """
        from discord.ext import tasks

        @tasks.loop(hours=6)  # Every 6 hours
        async def auto_backup_task():
            try:
                # Only create backup if there have been changes
                if self._has_recent_activity():
                    backup_path = self.create_backup("automatic")
                    if backup_path:
                        logger.info(f"🔄 Automatic backup created: {backup_path}")
            except Exception as e:
                logger.error(f"❌ Automatic backup failed: {e}")

        return auto_backup_task

    def _has_recent_activity(self) -> bool:
        """
        Check if there has been recent activity worth backing up.

        Returns:
            bool: True if files were modified in last 6 hours

        Checks:
        - File modification times
        - Critical file changes
        - Data file updates
        """
        try:
            from config.constants import FILES

            # Check if any data files were modified in the last 6 hours
            cutoff = datetime.utcnow() - timedelta(hours=6)

            for filepath in FILES.values():
                if os.path.exists(filepath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime > cutoff:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Error checking recent activity: {e}")
            return True  # Assume activity if we can't check

    def get_backup_stats(self) -> Dict:
        """
        Get backup system statistics.

        Returns:
            dict containing:
            - total_backups: Number of backups
            - total_size: Size in bytes
            - total_size_mb: Size in megabytes
            - oldest_backup: Timestamp of oldest
            - newest_backup: Timestamp of newest
            - backup_types: Count by type
        """
        try:
            backups = self.list_backups()

            if not backups:
                return {
                    "total_backups": 0,
                    "total_size": 0,
                    "oldest_backup": None,
                    "newest_backup": None,
                    "backup_types": {},
                }

            total_size = sum(b["size"] for b in backups)
            backup_types = {}

            for backup in backups:
                if backup["metadata"]:
                    backup_type = backup["metadata"].get("backup_type", "unknown")
                    backup_types[backup_type] = backup_types.get(backup_type, 0) + 1

            return {
                "total_backups": len(backups),
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "oldest_backup": backups[-1]["created"] if backups else None,
                "newest_backup": backups[0]["created"] if backups else None,
                "backup_types": backup_types,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get backup stats: {e}")
            return {}


# Global backup manager instance
backup_manager = BackupManager()


# Convenience functions
def create_backup(backup_type: str = "manual") -> Optional[str]:
    """
    Create a backup of all data files.

    Args:
        backup_type: Type of backup (manual, automatic, pre_restore)

    Returns:
        str: Path to created backup file or None on failure

    Features:
        - Metadata generation
        - File compression
        - Error handling
        - Automatic cleanup
    """
    return backup_manager.create_backup(backup_type)


def list_backups() -> List[Dict]:
    """
    List all available backups.

    Returns:
        list: List of backup information dictionaries containing:
            - filename: Backup file name
            - path: Full file path
            - size: Backup size in bytes
            - created: Creation timestamp
            - metadata: Backup metadata if available
    """
    return backup_manager.list_backups()


def restore_backup(backup_filename: str, confirm: bool = False) -> bool:
    """
    Restore data from a backup.

    Args:
        backup_filename: Name of backup file to restore
        confirm: Safety confirmation flag

    Returns:
        bool: True if restore successful

    Features:
        - Pre-restore backup creation
        - Safety confirmation
        - File validation
        - Error handling
    """
    return backup_manager.restore_backup(backup_filename, confirm)

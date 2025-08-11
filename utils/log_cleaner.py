
"""
Log cleanup utility for managing log file sizes and rotation.

Features:
- Automatic log file size monitoring
- Log rotation with configurable limits
- Cleanup of old log files
- Compression of archived logs
- Integration with existing logger system

Components:
- Size-based cleanup
- Time-based cleanup
- Log compression
- Monitoring integration
"""

import os
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger("log_cleaner")


class LogCleaner:
    """
    Manages log file cleanup and rotation.

    Features:
    - Size-based log rotation
    - Time-based log cleanup
    - Log compression
    - Automatic monitoring
    - Statistics tracking

    Attributes:
        log_dir: Directory containing log files
        max_file_size: Maximum size per log file (MB)
        max_age_days: Maximum age for log files
        max_total_size: Maximum total log directory size (MB)
        compress_old_logs: Whether to compress rotated logs
    """

    def __init__(
        self,
        log_dir: str = "data/logs",
        max_file_size: int = 10,  # MB
        max_age_days: int = 30,
        max_total_size: int = 100,  # MB
        compress_old_logs: bool = True
    ):
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size * 1024 * 1024  # Convert to bytes
        self.max_age_days = max_age_days
        self.max_total_size = max_total_size * 1024 * 1024  # Convert to bytes
        self.compress_old_logs = compress_old_logs
        self.cleaned_files = []
        self.compressed_files = []
        self.deleted_files = []

    def cleanup_logs(self, force: bool = False) -> Dict:
        """
        Perform comprehensive log cleanup.

        Args:
            force: Force cleanup even if not needed

        Returns:
            dict: Cleanup statistics and results

        Features:
        - Size-based rotation
        - Age-based cleanup
        - Total size management
        - Compression handling
        - Statistics generation
        """
        logger.info("🧹 Starting log cleanup process...")

        # Reset tracking lists
        self.cleaned_files = []
        self.compressed_files = []
        self.deleted_files = []

        try:
            # Ensure log directory exists
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Get current log statistics
            initial_stats = self._get_log_stats()
            logger.info(f"📊 Current log stats: {initial_stats['file_count']} files, {initial_stats['total_size_mb']:.2f} MB")

            # Step 1: Rotate large log files
            self._rotate_large_files()

            # Step 2: Compress old rotated logs
            if self.compress_old_logs:
                self._compress_old_logs()

            # Step 3: Clean up old log files
            self._cleanup_old_files()

            # Step 4: Manage total directory size
            self._manage_total_size()

            # Get final statistics
            final_stats = self._get_log_stats()

            # Calculate savings
            size_saved = initial_stats['total_size'] - final_stats['total_size']
            size_saved_mb = size_saved / 1024 / 1024

            results = {
                "success": True,
                "initial_stats": initial_stats,
                "final_stats": final_stats,
                "size_saved_mb": round(size_saved_mb, 2),
                "files_rotated": len(self.cleaned_files),
                "files_compressed": len(self.compressed_files),
                "files_deleted": len(self.deleted_files),
                "actions": {
                    "rotated": self.cleaned_files,
                    "compressed": self.compressed_files,
                    "deleted": self.deleted_files
                }
            }

            logger.info(f"✅ Log cleanup completed: {size_saved_mb:.2f} MB saved, {len(self.cleaned_files)} rotated, {len(self.deleted_files)} deleted")
            return results

        except Exception as e:
            logger.error(f"❌ Log cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "initial_stats": initial_stats if 'initial_stats' in locals() else {},
                "actions": {}
            }

    def _rotate_large_files(self):
        """Rotate log files that exceed size limit."""
        for log_file in self.log_dir.glob("*.log"):
            try:
                if log_file.stat().st_size > self.max_file_size:
                    # Create rotated filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    rotated_name = f"{log_file.stem}_{timestamp}.log"
                    rotated_path = self.log_dir / rotated_name

                    # Move current log to rotated name
                    shutil.move(str(log_file), str(rotated_path))

                    # Create new empty log file
                    log_file.touch()

                    self.cleaned_files.append(str(rotated_path))
                    logger.info(f"🔄 Rotated large log: {log_file.name} -> {rotated_name}")

            except Exception as e:
                logger.warning(f"Failed to rotate {log_file}: {e}")

    def _compress_old_logs(self):
        """Compress old rotated log files."""
        # Find rotated logs (contain timestamp in filename)
        for log_file in self.log_dir.glob("*_????????_??????.log"):
            try:
                compressed_name = f"{log_file.name}.gz"
                compressed_path = self.log_dir / compressed_name

                # Skip if already compressed
                if compressed_path.exists():
                    continue

                # Compress the file
                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove original after successful compression
                log_file.unlink()

                self.compressed_files.append(str(compressed_path))
                logger.info(f"🗜️ Compressed log: {log_file.name} -> {compressed_name}")

            except Exception as e:
                logger.warning(f"Failed to compress {log_file}: {e}")

    def _cleanup_old_files(self):
        """Remove old log files based on age."""
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        cutoff_timestamp = cutoff_date.timestamp()

        # Check all log files and compressed logs
        patterns = ["*.log", "*.log.gz"]
        for pattern in patterns:
            for log_file in self.log_dir.glob(pattern):
                try:
                    # Skip current active log files (no timestamp in name)
                    if pattern == "*.log" and "_" not in log_file.stem:
                        continue

                    if log_file.stat().st_mtime < cutoff_timestamp:
                        log_file.unlink()
                        self.deleted_files.append(str(log_file))
                        logger.info(f"🗑️ Deleted old log: {log_file.name}")

                except Exception as e:
                    logger.warning(f"Failed to delete {log_file}: {e}")

    def _manage_total_size(self):
        """Manage total directory size by removing oldest files if needed."""
        current_size = self._get_total_directory_size()

        if current_size <= self.max_total_size:
            return

        logger.info(f"📏 Directory size ({current_size / 1024 / 1024:.2f} MB) exceeds limit, removing oldest files...")

        # Get all log files sorted by modification time (oldest first)
        all_files = []
        for pattern in ["*.log", "*.log.gz"]:
            for log_file in self.log_dir.glob(pattern):
                # Skip current active logs
                if pattern == "*.log" and "_" not in log_file.stem:
                    continue
                
                try:
                    stat = log_file.stat()
                    all_files.append((log_file, stat.st_mtime, stat.st_size))
                except:
                    continue

        # Sort by modification time (oldest first)
        all_files.sort(key=lambda x: x[1])

        # Remove oldest files until we're under the size limit
        for log_file, mtime, size in all_files:
            if current_size <= self.max_total_size:
                break

            try:
                log_file.unlink()
                current_size -= size
                self.deleted_files.append(str(log_file))
                logger.info(f"🗑️ Deleted for size limit: {log_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {log_file} for size management: {e}")

    def _get_log_stats(self) -> Dict:
        """Get current log directory statistics."""
        try:
            total_size = 0
            file_count = 0
            files_by_type = {"log": 0, "compressed": 0}

            for log_file in self.log_dir.rglob("*"):
                if log_file.is_file():
                    try:
                        size = log_file.stat().st_size
                        total_size += size
                        file_count += 1

                        if log_file.suffix == ".gz":
                            files_by_type["compressed"] += 1
                        elif log_file.suffix == ".log":
                            files_by_type["log"] += 1

                    except:
                        continue

            return {
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "file_count": file_count,
                "files_by_type": files_by_type
            }

        except Exception as e:
            logger.error(f"Failed to get log stats: {e}")
            return {"total_size": 0, "total_size_mb": 0, "file_count": 0, "files_by_type": {}}

    def _get_total_directory_size(self) -> int:
        """Get total size of log directory in bytes."""
        total_size = 0
        try:
            for log_file in self.log_dir.rglob("*"):
                if log_file.is_file():
                    try:
                        total_size += log_file.stat().st_size
                    except:
                        continue
        except:
            pass
        return total_size

    def get_large_files(self, min_size_mb: int = 5) -> List[Dict]:
        """
        Get list of large log files.

        Args:
            min_size_mb: Minimum size in MB to be considered large

        Returns:
            list: List of large file information
        """
        large_files = []
        min_size_bytes = min_size_mb * 1024 * 1024

        try:
            for log_file in self.log_dir.glob("*"):
                if log_file.is_file():
                    try:
                        stat = log_file.stat()
                        if stat.st_size >= min_size_bytes:
                            large_files.append({
                                "name": log_file.name,
                                "path": str(log_file),
                                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                            })
                    except:
                        continue

            # Sort by size (largest first)
            large_files.sort(key=lambda x: x["size_mb"], reverse=True)

        except Exception as e:
            logger.error(f"Failed to get large files: {e}")

        return large_files


# Global log cleaner instance
log_cleaner = LogCleaner()


# Convenience functions
def cleanup_logs(force: bool = False) -> Dict:
    """
    Clean up log files with rotation and compression.

    Args:
        force: Force cleanup even if not needed

    Returns:
        dict: Cleanup results and statistics

    Features:
        - Size-based rotation
        - Age-based cleanup
        - Compression handling
        - Statistics tracking
    """
    return log_cleaner.cleanup_logs(force)


def get_log_stats() -> Dict:
    """
    Get current log directory statistics.

    Returns:
        dict: Log directory statistics including:
            - total_size_mb: Total size in megabytes
            - file_count: Number of log files
            - files_by_type: Breakdown by file type
    """
    return log_cleaner._get_log_stats()


def get_large_log_files(min_size_mb: int = 5) -> List[Dict]:
    """
    Get list of large log files for manual review.

    Args:
        min_size_mb: Minimum size in MB to be considered large

    Returns:
        list: List of large file information with paths and sizes
    """
    return log_cleaner.get_large_files(min_size_mb)

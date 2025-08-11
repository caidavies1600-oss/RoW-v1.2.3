"""Error logging service for the Discord bot."""

import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

from utils.logger import setup_logger

if TYPE_CHECKING:
    from utils.sheets_manager import SheetsManager
    from discord.ext import commands

logger = setup_logger("error_logger")

class ErrorLogger:
    def __init__(self, bot: 'commands.Bot'):
        self.bot = bot
        self.error_log_file = "data/error_log.json"
        self.max_local_errors = 1000
        self._sheets_manager: Optional['SheetsManager'] = None

    def set_sheets_manager(self, sheets_manager: 'SheetsManager') -> None:
        """Set the sheets manager instance for error logging."""
        self._sheets_manager = sheets_manager

    async def log_error(self, 
                 error_type: str, 
                 command: str, 
                 user_id: Optional[int], 
                 error_message: str,
                 traceback_str: str,
                 severity: str = "Medium",
                 context: Optional[Dict[str, Any]] = None) -> None:
        """Log error to both local file and sheets."""
        try:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            error_entry = {
                "timestamp": timestamp,
                "error_type": error_type,
                "command": command,
                "user_id": str(user_id) if user_id else "System",
                "error_message": error_message,
                "traceback": traceback_str,
                "severity": severity,
                "context": context or {}
            }

            # Save to local file
            self._save_to_file(error_entry)

            # Log to sheets if available
            if self._sheets_manager and self._sheets_manager.is_connected():
                await self._log_to_sheets(error_entry)

        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    def _save_to_file(self, error_entry: Dict[str, Any]) -> None:
        """Save error to local JSON file."""
        try:
            errors = self._load_errors()
            errors.append(error_entry)
            
            # Keep only last N errors
            if len(errors) > self.max_local_errors:
                errors = errors[-self.max_local_errors:]

            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error to file: {e}")

    def _load_errors(self) -> list:
        """Load existing errors from file."""
        try:
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    async def _log_to_sheets(self, error_entry: Dict[str, Any]) -> None:
        """Log error to Google Sheets."""
        try:
            if self._sheets_manager and hasattr(self._sheets_manager, 'append_error'):
                await self._sheets_manager.append_error(error_entry)
            else:
                logger.error("SheetsManager does not have append_error method")
        except Exception as e:
            logger.error(f"Failed to log error to sheets: {e}")

# Global error logger instance
error_logger: Optional[ErrorLogger] = None

def setup_error_logger(bot: 'commands.Bot') -> None:
    """Initialize the global error logger."""
    global error_logger
    error_logger = ErrorLogger(bot)
    logger.info("✅ Error logger initialized")

async def log_error(error_type: str, error: Exception, context: str = "") -> None:
    """Convenience function to log errors."""
    if error_logger:
        await error_logger.log_error(
            error_type=error_type,
            command="System",
            user_id=None,
            error_message=str(error),
            traceback_str=traceback.format_exc(),
            severity="High",
            context={"details": context}
        )
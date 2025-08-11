"""Error logging system with Google Sheets integration."""

import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from utils.logger import setup_logger

logger = setup_logger("error_logger")

class ErrorLogger:
    """Logs all bot errors to both local files and Google Sheets."""

    def __init__(self, bot):
        """
        Initializes the ErrorLogger.

        Args:
            bot: An instance of the bot to log errors from.
        """
        self.bot = bot
        self.error_log_file = "data/error_log.json"
        self.max_local_errors = 1000
        self.sheets_manager = None

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Logs an error message with traceback to the log file and Google Sheets.

        Args:
            error (Exception): The exception instance to log.
            context (Optional[Dict[str, Any]]): Additional context about the error.
        """
        # Prepare the error message
        error_message = f"Error: {str(error)}\n"
        error_message += "Traceback:\n"
        error_message += "".join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))

        # Log to file
        logger.error(error_message)

        # Log to Google Sheets if sheets_manager is available
        if self.sheets_manager:
            self.sheets_manager.log_error_to_sheet(error_message, context)

    def set_sheets_manager(self, sheets_manager: GoogleSheetsManager):
        """
        Sets the Google Sheets manager instance.

        Args:
            sheets_manager (GoogleSheetsManager): An instance of GoogleSheetsManager.
        """
        self.sheets_manager = sheets_manager

    def log_message(self, message: str):
        """
        Logs a regular message to the log file and Google Sheets.

        Args:
            message (str): The message to log.
        """
        # Log to file
        logger.info(message)

        # Log to Google Sheets if sheets_manager is available
        if self.sheets_manager:
            self.sheets_manager.log_message_to_sheet(message)
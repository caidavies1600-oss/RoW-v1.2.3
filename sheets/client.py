"""
Google Sheets client for authentication and basic operations.
"""

import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger("sheets_client")

class SheetsClient:
    """Handles Google Sheets authentication and basic operations."""

    def __init__(self):
        self.gc: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests (more conservative)
        self._request_count = 0
        self._max_requests_per_minute = 50  # Conservative limit

    def initialize(self) -> bool:
        """Initialize Google Sheets client with service account credentials."""
        try:
            # Define the scope
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # Load credentials from environment variable
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if not creds_json:
                logger.info("No Google Sheets credentials found in environment")
                return False

            try:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {e}")
                return False

            self.gc = gspread.authorize(creds)

            # Open or create the spreadsheet
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
            if spreadsheet_id:
                try:
                    self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
                    logger.info(f"✅ Connected to existing spreadsheet: {self.spreadsheet.url}")
                except gspread.SpreadsheetNotFound:
                    logger.error(f"Spreadsheet with ID {spreadsheet_id} not found")
                    return False
            else:
                # Create new spreadsheet
                self.spreadsheet = self.gc.create("Discord RoW Bot Data")
                logger.info(f"✅ Created new spreadsheet: {self.spreadsheet.url}")
                logger.info(f"Set GOOGLE_SHEETS_ID={self.spreadsheet.id} in your environment")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets client: {e}")
            self.gc = None
            self.spreadsheet = None
            return False

    def is_connected(self) -> bool:
        """Check if sheets connection is active."""
        return self.gc is not None and self.spreadsheet is not None

    def _rate_limit(self):
        """Simple rate limiting to avoid API quota issues."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()

    def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
        """Get existing worksheet or create new one with rate limiting."""
        if not self.is_connected():
            return None

        try:
            self._rate_limit()
            return self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            try:
                self._rate_limit()
                worksheet = self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
                logger.info(f"Created new worksheet: {title}")
                return worksheet
            except Exception as e:
                logger.error(f"Failed to create worksheet {title}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error accessing worksheet {title}: {e}")
            return None

    def safe_worksheet_operation(self, worksheet, operation, *args, **kwargs):
        """Execute worksheet operation with error handling and rate limiting."""
        if not worksheet:
            return None

        try:
            self._rate_limit()
            return operation(*args, **kwargs)
        except Exception as e:
            logger.error(f"Worksheet operation failed: {e}")
            return None
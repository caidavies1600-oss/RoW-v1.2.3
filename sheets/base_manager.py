import gspread
from google.oauth2.service_account import Credentials
import json
import os
from utils.logger import setup_logger

logger = setup_logger("sheets_base")

class BaseSheetsManager:
    """Core Google Sheets connection and authentication."""

    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.initialize_client()

    def initialize_client(self):
        """Initialize Google Sheets client with service account credentials."""
        try:
            # Define the scope
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # Load credentials from environment variable or file
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            else:
                creds = Credentials.from_service_account_file('credentials.json', scopes=scope)

            self.gc = gspread.authorize(creds)

            # Open the spreadsheet
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
            if spreadsheet_id:
                self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
                logger.info(f"✅ Connected to existing spreadsheet: {self.spreadsheet.url}")
            else:
                self.spreadsheet = self.gc.create("Discord RoW Bot Data")
                logger.info(f"✅ Created new spreadsheet: {self.spreadsheet.url}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets client: {e}")
            self.gc = None
            self.spreadsheet = None

    def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
        """Get existing worksheet or create new one."""
        if not self.spreadsheet:
            return None

        try:
            return self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    def is_connected(self) -> bool:
        """Check if sheets connection is active."""
        return self.gc is not None and self.spreadsheet is not None
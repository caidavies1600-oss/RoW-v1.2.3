
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from utils.logger import setup_logger

logger = setup_logger("sheets_connection")

class BaseSheetsConnection:
    """Handles Google Sheets authentication and connection management."""

    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.last_error = None
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize Google Sheets client with enhanced error handling."""
        try:
            # Define the scope
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # Load credentials with better error messages
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if creds_json:
                try:
                    creds_dict = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
                    logger.info("✅ Loaded credentials from environment variable")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {e}")
                    self.last_error = f"Invalid credentials JSON: {e}"
                    return
            else:
                # Fallback to credentials file
                creds_path = 'credentials.json'
                if os.path.exists(creds_path):
                    try:
                        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
                        logger.info("✅ Loaded credentials from credentials.json file")
                    except Exception as e:
                        logger.error(f"❌ Failed to load credentials.json: {e}")
                        self.last_error = f"Credentials file error: {e}"
                        return
                else:
                    logger.error("❌ No credentials found - set GOOGLE_SHEETS_CREDENTIALS or add credentials.json")
                    self.last_error = "No credentials configured"
                    return

            # Authorize the client
            try:
                self.gc = gspread.authorize(creds)
                logger.info("✅ Google Sheets client authorized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to authorize Google Sheets client: {e}")
                self.last_error = f"Authorization failed: {e}"
                return

            # Open or create the spreadsheet
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
            if spreadsheet_id:
                try:
                    self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
                    logger.info(f"✅ Connected to existing spreadsheet: {self.spreadsheet.url}")
                except gspread.SpreadsheetNotFound:
                    logger.error(f"❌ Spreadsheet not found with ID: {spreadsheet_id}")
                    self.last_error = f"Spreadsheet not found: {spreadsheet_id}"
                    return
                except Exception as e:
                    logger.error(f"❌ Failed to open spreadsheet: {e}")
                    self.last_error = f"Failed to open spreadsheet: {e}"
                    return
            else:
                try:
                    self.spreadsheet = self.gc.create("Discord RoW Bot Data")
                    logger.info(f"✅ Created new spreadsheet: {self.spreadsheet.url}")
                    logger.info(f"📝 Set GOOGLE_SHEETS_ID={self.spreadsheet.id} to reuse this spreadsheet")
                except Exception as e:
                    logger.error(f"❌ Failed to create new spreadsheet: {e}")
                    self.last_error = f"Failed to create spreadsheet: {e}"
                    return

            self.last_error = None  # Clear any previous errors

        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets client: {e}")
            self.gc = None
            self.spreadsheet = None
            self.last_error = str(e)

    def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
        """Get existing worksheet or create new one with better error handling."""
        if not self.spreadsheet:
            logger.error("❌ Cannot access worksheet - spreadsheet not initialized")
            return None

        try:
            # Try to get existing worksheet
            worksheet = self.spreadsheet.worksheet(title)
            logger.debug(f"✅ Found existing worksheet: {title}")
            return worksheet
        except gspread.WorksheetNotFound:
            try:
                # Create new worksheet
                worksheet = self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
                logger.info(f"✅ Created new worksheet: {title}")
                return worksheet
            except Exception as e:
                logger.error(f"❌ Failed to create worksheet '{title}': {e}")
                return None
        except Exception as e:
            logger.error(f"❌ Error accessing worksheet '{title}': {e}")
            return None

    def is_connected(self) -> bool:
        """Check if sheets connection is active with detailed status."""
        if self.gc is None:
            logger.debug("❌ Google Sheets client not initialized")
            return False
        
        if self.spreadsheet is None:
            logger.debug("❌ No spreadsheet connected")
            return False
            
        try:
            # Test connection by accessing spreadsheet properties
            _ = self.spreadsheet.id
            logger.debug("✅ Sheets connection verified")
            return True
        except Exception as e:
            logger.debug(f"❌ Sheets connection test failed: {e}")
            return False

    def get_connection_status(self) -> dict:
        """Get detailed connection status for debugging."""
        return {
            "client_initialized": self.gc is not None,
            "spreadsheet_connected": self.spreadsheet is not None,
            "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None,
            "spreadsheet_id": self.spreadsheet.id if self.spreadsheet else None,
            "last_error": self.last_error,
            "is_connected": self.is_connected()
        }

import gspread
import time
import logging
import os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class GoogleSheetsManager:
    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        self.credentials = None
        self.load_credentials()

    def load_credentials(self):
        """Load Google Sheets API credentials."""
        try:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not creds_path:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

            self.credentials = Credentials.from_service_account_file(creds_path, scopes=self.scopes)
            self.gc = gspread.authorize(self.credentials)
            logger.info("Google Sheets credentials loaded successfully.")
        except FileNotFoundError:
            logger.error(f"Credentials file not found at {creds_path}")
            self.credentials = None
            self.gc = None
        except Exception as e:
            logger.error(f"Failed to load Google Sheets credentials: {e}")
            self.credentials = None
            self.gc = None

    def open_spreadsheet(self, spreadsheet_name):
        """Open a Google Sheet by its name."""
        if not self.gc:
            logger.error("Google Sheets client not authorized. Cannot open spreadsheet.")
            return False
        try:
            self.spreadsheet = self.gc.open(spreadsheet_name)
            logger.info(f"Successfully opened spreadsheet: '{spreadsheet_name}'")
            return True
        except gspread.SpreadsheetNotFound:
            logger.error(f"Spreadsheet '{spreadsheet_name}' not found.")
            self.spreadsheet = None
            return False
        except Exception as e:
            logger.error(f"Failed to open spreadsheet '{spreadsheet_name}': {e}")
            self.spreadsheet = None
            return False

    def get_all_data_from_sheet(self, sheet_name="Sheet1"):
        """Get all data from a specific sheet."""
        if not self.spreadsheet:
            logger.error("Spreadsheet not opened. Cannot retrieve data.")
            return None

        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_records()
            logger.info(f"✅ Successfully loaded all data from Google Sheets")
            return data

        except gspread.WorksheetNotFound:
            logger.error(f"Worksheet '{sheet_name}' not found in the spreadsheet.")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load data from sheets: {e}")
            import traceback
            logger.error(f"Data loading traceback: {traceback.format_exc()}")
            return None

    # Add the missing sync methods that are referenced by data_manager.py
    def sync_events_history(self, events_history_data):
        """Sync events history to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            try:
                worksheet = self.spreadsheet.worksheet("Events History")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Events History", rows="1000", cols="8")

            # Headers
            headers = ["📅 Date", "🎯 Team", "👥 Player Count", "📝 Players", "📊 Status", "⏰ Event Time", "🎮 Event Type", "📝 Notes"]
            worksheet.append_row(headers)

            # Add historical events data
            history = events_history_data.get("history", [])
            for i, event in enumerate(history[-500:]):  # Last 500 events
                if i > 0 and i % 20 == 0:
                    time.sleep(2)  # Rate limiting

                row_data = [
                    event.get("date", "Unknown"),
                    event.get("team", "Unknown"),
                    event.get("player_count", 0),
                    ", ".join(event.get("players", [])),
                    event.get("status", "Completed"),
                    event.get("event_time", "Unknown"),
                    event.get("event_type", "Weekly Event"),
                    event.get("notes", "")
                ]
                worksheet.append_row(row_data)

            logger.info(f"✅ Synced {len(history)} events history to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync events history: {e}")
            return False
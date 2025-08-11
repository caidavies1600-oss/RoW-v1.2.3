"""
Google Sheets manager for the RoW bot.

This module handles all interactions with Google Sheets for:
- Loading and saving event data
- Managing player signups and team assignments
- Storing and retrieving match results and statistics

Usage:
    Import and use the `SheetsManager` class in other parts of the bot to
    interact with Google Sheets for event management.

Requirements:
    - Google Sheets API credentials must be set up
    - Required scopes: `https://www.googleapis.com/auth/spreadsheets`
"""

import random
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.constants import GOOGLE_SHEET_ID, GOOGLE_SHEET_RANGE
from utils.logger import setup_logger

logger = setup_logger("sheets_manager")


class SheetsManager:
    def __init__(self, spreadsheet_id=GOOGLE_SHEET_ID, range_name=GOOGLE_SHEET_RANGE):
        """Initialize the SheetsManager.

        Args:
            spreadsheet_id (str): The ID of the Google Sheet to manage.
            range_name (str): The A1 notation of the range to access.
        """
        self.spreadsheet_id = spreadsheet_id
        self.range_name = range_name
        self.service = None
        self.spreadsheet = None

    def connect(self):
        """Connect to the Google Sheets API and open the spreadsheet."""
        try:
            self.service = build("sheets", "v4")
            self.spreadsheet = (
                self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            )
            logger.info(f"✅ Connected to Google Sheets: {self.spreadsheet['properties']['title']}")
        except HttpError as e:
            logger.error(f"❌ Failed to connect to Google Sheets: {e}")

    def is_connected(self) -> bool:
        """Check if the manager is connected to Google Sheets.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self.service is not None and self.spreadsheet is not None

    def get_spreadsheet_url(self) -> str:
        """Get the URL of the current spreadsheet."""
        if self.spreadsheet:
            return self.spreadsheet.url
        return ""

    async def load_data(self) -> dict | None:
        """Load data from Google Sheets."""
        if not self.is_connected():
            return None

        try:
            data = {
                "events": {"main_team": [], "team_2": [], "team_3": []},
                "blocked": {},
                "results": {"total_wins": 0, "total_losses": 0, "history": []},
                "player_stats": {},
                "ign_map": {},
                "absent": {}
            }

            # Load Current Teams
            try:
                worksheet = self.spreadsheet.worksheet("Current Teams")
                rows = worksheet.get_all_records()
                for row in rows:
                    team = row.get("Team", "").lower().replace(" ", "_")
                    players = row.get("Players", "")
                    if team in data["events"] and players:
                        player_list = [p.strip() for p in players.split(",") if p.strip()]
                        data["events"][team] = player_list
            except Exception:
                logger.info("Current Teams sheet not found, using defaults")

            return data

        except Exception as e:
            logger.error(f"❌ Failed to load data from sheets: {e}")
            return None

    # ...existing methods...
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
import os
import asyncio
from typing import Any

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
            self.connect()
            if not self.is_connected():
                return None

        try:
            if not self.service:
                logger.error("❌ Google Sheets service is not initialized")
                return None

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
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range="Current Teams"
                ).execute()
                rows = [dict(zip(result['values'][0], row)) for row in result['values'][1:]]
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

    async def sync_data(self, filepath: str, data: Any):
        """Sync data to appropriate sheet based on filepath."""
        if not self.is_connected():
            return

        filename = os.path.basename(filepath)

        try:
            if filename == "events.json":
                await self._run_sync_in_executor(lambda: self.sync_current_teams(data))
            elif filename == "events_history.json":
                await self._run_sync_in_executor(lambda: self.sync_events_history(data))
            elif filename == "blocked_users.json":
                await self._run_sync_in_executor(lambda: self.sync_blocked_users(data))
            elif filename == "event_results.json":
                await self._run_sync_in_executor(lambda: self.sync_results_history(data))
        except Exception as e:
            logger.error(f"Failed to sync {filename}: {e}")

    async def _run_sync_in_executor(self, sync_func):
        """Run sync operation in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_func)

    def sync_current_teams(self, data):
        """Sync current teams to the 'Current Teams' sheet."""
        try:
            values = [["Team", "Players"]]
            for team, players in data.get("events", {}).items():
                values.append([team.replace("_", " ").title(), ", ".join(players)])
            
            body = {"values": values}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Current Teams",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            logger.info("✅ Synced current teams")
        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")

    def sync_events_history(self, data):
        """Sync event history to the 'Event History' sheet."""
        try:
            values = [["Event Name", "Winner", "Date"]] # Example columns, adjust as needed
            for event in data.get("event_history", []): # Assuming data structure
                values.append([event.get("name"), event.get("winner"), event.get("date")])

            body = {"values": values}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Event History",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            logger.info("✅ Synced event history")
        except Exception as e:
            logger.error(f"❌ Failed to sync event history: {e}")

    def sync_blocked_users(self, data):
        """Sync blocked users to the 'Blocked Users' sheet."""
        try:
            values = [["User ID", "Reason", "Timestamp"]] # Example columns
            for user_id, info in data.get("blocked", {}).items():
                values.append([user_id, info.get("reason"), info.get("timestamp")])

            body = {"values": values}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Blocked Users",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            logger.info("✅ Synced blocked users")
        except Exception as e:
            logger.error(f"❌ Failed to sync blocked users: {e}")

    def sync_results_history(self, data):
        """Sync results history to the 'Results History' sheet."""
        try:
            values = [["Total Wins", "Total Losses", "Match History"]] # Example columns
            results = data.get("results", {})
            values.append([
                results.get("total_wins", 0),
                results.get("total_losses", 0),
                "\n".join([f"{h['team1']} vs {h['team2']}: {h['result']}" for h in results.get("history", [])])
            ])

            body = {"values": values}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Results History",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            logger.info("✅ Synced results history")
        except Exception as e:
            logger.error(f"❌ Failed to sync results history: {e}")
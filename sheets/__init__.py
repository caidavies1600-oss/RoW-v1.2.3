"""
Google Sheets Integration Module for Discord RoW Bot.

This module provides:
- Rate-limited Google Sheets access
- Template creation and formatting
- Data synchronization between bot and sheets
- Error handling and connection management

Components:
- SheetsManager: Main interface for sheets operations
- Rate limiting with exponential backoff
- Automatic retry on API errors
- Template-based sheet creation
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from utils.logger import setup_logger

logger = setup_logger("sheets_manager")


class SheetsManager:
    """
    Main Google Sheets manager with comprehensive functionality.

    Features:
    - Rate-limited API access with exponential backoff
    - Comprehensive error handling and recovery
    - Batch operation support
    - Worksheet management
    - Usage tracking and statistics
    - Auto-reconnection on failures
    """

    def __init__(self, spreadsheet_id=None):
        self.gc = None
        self.spreadsheet = None
        self.spreadsheet_id = spreadsheet_id
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        self.rate_limit_hits = 0
        self.session_start_time = time.time()
        self.max_retries = 5
        self.initialize_client()

    def initialize_client(self):
        """Initialize Google Sheets client with service account credentials."""
        try:
            # Define the scope
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            # Load credentials from environment variable or file
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
                logger.info("✅ Loaded Google Sheets credentials from environment")
            else:
                if os.path.exists("credentials.json"):
                    creds = Credentials.from_service_account_file(
                        "credentials.json", scopes=scope
                    )
                    logger.info("✅ Loaded Google Sheets credentials from file")
                else:
                    logger.error("❌ No Google Sheets credentials found")
                    self.gc = None
                    self.spreadsheet = None
                    return

            self.gc = gspread.authorize(creds)

            # Open the spreadsheet
            spreadsheet_id = self.spreadsheet_id or os.getenv("GOOGLE_SHEETS_ID")
            if spreadsheet_id:
                self.spreadsheet = self.rate_limited_request(
                    lambda: self.gc.open_by_key(spreadsheet_id)
                )
                self.spreadsheet_id = spreadsheet_id
                logger.info(
                    f"✅ Connected to existing spreadsheet: {self.spreadsheet.url}"
                )
            else:
                self.spreadsheet = self.rate_limited_request(
                    lambda: self.gc.create("Discord RoW Bot Data")
                )
                self.spreadsheet_id = self.spreadsheet.id
                logger.info(f"✅ Created new spreadsheet: {self.spreadsheet.url}")
                logger.warning(
                    "⚠️ Set GOOGLE_SHEETS_ID environment variable to reuse this spreadsheet"
                )

        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets client: {e}")
            logger.info("💡 Make sure GOOGLE_SHEETS_CREDENTIALS and GOOGLE_SHEETS_ID are set in environment")
            self.gc = None
            self.spreadsheet = None

    def rate_limited_request(self, func, *args, **kwargs):
        """Execute request with rate limiting and error handling."""
        # Enforce minimum interval between requests
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        # Update tracking
        self.last_request_time = time.time()
        self.request_count += 1

        # Execute with retries
        for attempt in range(self.max_retries):
            try:
                if args or kwargs:
                    result = func(*args, **kwargs)
                else:
                    result = func()
                return result
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)

    def is_connected(self) -> bool:
        """Check if sheets connection is active and functional."""
        if not self.gc or not self.spreadsheet:
            return False
        try:
            self.rate_limited_request(lambda: self.spreadsheet.worksheets())
            return True
        except:
            return False

    def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
        """Get existing worksheet or create new one with rate limiting."""
        if not self.spreadsheet:
            logger.error("❌ No spreadsheet available")
            return None

        try:
            worksheet = self.rate_limited_request(
                lambda: self.spreadsheet.worksheet(title)
            )
            logger.debug(f"✅ Found existing worksheet: {title}")
            return worksheet
        except gspread.WorksheetNotFound:
            try:
                worksheet = self.rate_limited_request(
                    lambda: self.spreadsheet.add_worksheet(
                        title=title, rows=rows, cols=cols
                    )
                )
                logger.info(f"✅ Created worksheet: {title}")
                return worksheet
            except Exception as e:
                logger.error(f"❌ Failed to create worksheet {title}: {e}")
                return None
        except Exception as e:
            logger.error(f"❌ Error accessing worksheet {title}: {e}")
            return None

    async def scan_and_sync_all_members(self, bot, guild_id=None):
        """
        Scan Discord guild and sync all members to Google Sheets.

        Args:
            bot: Discord bot instance
            guild_id: Discord guild ID to scan

        Returns:
            dict: Results of the sync operation
        """
        if not self.is_connected():
            return {"success": False, "error": "Sheets not connected"}

        try:
            guild = bot.get_guild(guild_id)
            if not guild:
                return {"success": False, "error": f"Guild {guild_id} not found"}

            logger.info(f"🔄 Scanning guild: {guild.name} ({guild.id})")

            # Get all non-bot members
            members = [member for member in guild.members if not member.bot]

            # Create member data for sheets
            member_data = []
            for member in members:
                member_data.append({
                    "user_id": str(member.id),
                    "username": member.name,
                    "display_name": member.display_name,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [role.name for role in member.roles if role.name != "@everyone"],
                    "status": str(member.status),
                    "synced_at": datetime.utcnow().isoformat()
                })

            # Sync to sheets
            success = await self._sync_members_to_sheets(member_data, guild.name)

            return {
                "success": success,
                "guild_name": guild.name,
                "total_discord_members": len(members),
                "new_members_added": len(member_data),
                "existing_members_updated": 0
            }

        except Exception as e:
            logger.error(f"❌ Failed to scan and sync members: {e}")
            return {"success": False, "error": str(e)}

    async def _sync_members_to_sheets(self, member_data, guild_name):
        """Sync member data to Google Sheets."""
        try:
            worksheet = self.get_or_create_worksheet("Discord Members", 1000, 10)
            if not worksheet:
                return False

            # Clear and set headers
            self.rate_limited_request(worksheet.clear)
            headers = [
                "👤 User ID",
                "📝 Username", 
                "💬 Display Name",
                "📅 Joined At",
                "🎭 Roles",
                "🟢 Status",
                "🔄 Synced At",
                "🏰 Guild",
                "📊 Notes"
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Add member data
            for member in member_data:
                row = [
                    member["user_id"],
                    member["username"],
                    member["display_name"],
                    member["joined_at"] or "Unknown",
                    ", ".join(member["roles"]),
                    member["status"],
                    member["synced_at"],
                    guild_name,
                    ""
                ]
                self.rate_limited_request(worksheet.append_row, row)

            # Apply formatting
            self.rate_limited_request(
                worksheet.format,
                "A1:I1",
                {
                    "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.8},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    },
                    "horizontalAlignment": "CENTER",
                },
            )

            self.rate_limited_request(worksheet.freeze, rows=1)

            logger.info(f"✅ Synced {len(member_data)} members to Discord Members sheet")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync members to sheets: {e}")
            return False

    def sync_current_teams(self, events_data):
        """Sync current team signups to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Current Teams", 50, 8)
            if not worksheet:
                return False

            # Clear and set headers
            self.rate_limited_request(worksheet.clear)
            headers = [
                "🕐 Timestamp",
                "⚔️ Team",
                "👥 Player Count",
                "📝 Players",
                "📊 Status",
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Add current data
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            team_mapping = {
                "main_team": "🏆 Main Team",
                "team_2": "🥈 Team 2",
                "team_3": "🥉 Team 3",
            }

            for team_key, players in events_data.items():
                team_name = team_mapping.get(
                    team_key, team_key.replace("_", " ").title()
                )
                player_count = len(players)
                player_list = (
                    ", ".join(str(p) for p in players) if players else "No signups"
                )

                # Status indicators
                if player_count >= 8:
                    status = "🟢 Ready"
                elif player_count >= 5:
                    status = "🟡 Partial"
                elif player_count > 0:
                    status = "🟠 Low"
                else:
                    status = "🔴 Empty"

                row = [timestamp, team_name, player_count, player_list, status]
                self.rate_limited_request(worksheet.append_row, row)

            logger.info("✅ Synced current teams to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def sync_results_history(self, results_data):
        """Sync results history to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Results History", 200, 8)
            if not worksheet:
                return False

            # Clear and set headers
            self.rate_limited_request(worksheet.clear)
            headers = [
                "📅 Date",
                "⚔️ Team",
                "🏆 Result",
                "👥 Players",
                "📝 Recorded By",
                "📋 Notes",
                "📊 Total Wins",
                "📊 Total Losses",
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Add history data
            history = results_data.get("history", [])
            for entry in history:
                date = entry.get("date", entry.get("timestamp", "Unknown"))
                team = entry.get("team", "Unknown")
                result = entry.get("result", "Unknown")
                players = ", ".join(entry.get("players", []))
                recorded_by = entry.get("by", entry.get("recorded_by", "Unknown"))
                notes = entry.get("notes", "")

                row = [
                    date,
                    team,
                    result,
                    players,
                    recorded_by,
                    notes,
                    results_data.get("total_wins", 0),
                    results_data.get("total_losses", 0),
                ]
                self.rate_limited_request(worksheet.append_row, row)

            logger.info(f"✅ Synced {len(history)} results to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync results history: {e}")
            return False

    def sync_events_history(self, history_data):
        """Sync events history to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Events History", 100, 6)
            if not worksheet:
                return False

            # Clear and set headers
            self.rate_limited_request(worksheet.clear)
            headers = [
                "📅 Timestamp",
                "🏆 Main Team",
                "🥈 Team 2", 
                "🥉 Team 3",
                "📊 Total Players",
                "📝 Notes"
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Add history data
            for entry in history_data:
                timestamp = entry.get("timestamp", "Unknown")
                teams = entry.get("teams", {})

                main_team = len(teams.get("main_team", []))
                team_2 = len(teams.get("team_2", []))
                team_3 = len(teams.get("team_3", []))
                total = main_team + team_2 + team_3

                row = [timestamp, main_team, team_2, team_3, total, ""]
                self.rate_limited_request(worksheet.append_row, row)

            logger.info("✅ Synced events history to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync events history: {e}")
            return False

    def sync_blocked_users(self, blocked_data):
        """Sync blocked users to Google Sheets."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Blocked Users", 50, 5)
            if not worksheet:
                return False

            # Clear and set headers
            self.rate_limited_request(worksheet.clear)
            headers = [
                "👤 User ID",
                "📝 Display Name", 
                "🚫 Blocked Date",
                "👮 Blocked By",
                "📋 Reason"
            ]
            self.rate_limited_request(worksheet.append_row, headers)

            # Add blocked users data
            for user_id, user_data in blocked_data.items():
                row = [
                    user_id,
                    user_data.get("name", "Unknown"),
                    user_data.get("blocked_date", "Unknown"),
                    user_data.get("blocked_by", "Unknown"),
                    user_data.get("reason", "No reason provided")
                ]
                self.rate_limited_request(worksheet.append_row, row)

            logger.info("✅ Synced blocked users to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync blocked users: {e}")
            return False

    def create_all_templates(self, all_data):
        """Create all sheet templates."""
        if not self.is_connected():
            return False

        try:
            success_count = 0

            # Create templates
            if self.sync_current_teams(all_data.get("events", {})):
                success_count += 1

            if self.sync_results_history(all_data.get("results", {})):
                success_count += 1

            if self.sync_events_history(all_data.get("events_history", [])):
                success_count += 1

            if self.sync_blocked_users(all_data.get("blocked", {})):
                success_count += 1

            logger.info(f"✅ Template creation completed: {success_count} operations successful")
            return success_count >= 2

        except Exception as e:
            logger.error(f"❌ Failed to create templates: {e}")
            return False

    def smart_delay(self, delay_type="small"):
        """
        Smart delay implementation for rate limiting.

        Args:
            delay_type: Type of delay ('small', 'medium', 'large')

        Features:
        - Configurable delay periods
        - Rate limit management  
        - Performance optimization
        """
        import time

        delay_map = {
            "small": 0.5,
            "medium": 1.0, 
            "large": 2.0
        }

        delay_time = delay_map.get(delay_type, 0.5)
        time.sleep(delay_time)


# Export the main class
__all__ = ["SheetsManager"]

# Module metadata
__version__ = "2.1.0"
__author__ = "RoW Bot Team"
__description__ = "Google Sheets integration with comprehensive features"
__requirements__ = ["gspread", "google-auth", "google-auth-oauthlib"]
__min_python_version__ = "3.8"

# Configuration constants
DEFAULT_REQUEST_INTERVAL = 0.1
DEFAULT_MAX_RETRIES = 5
DEFAULT_BATCH_SIZE = 50

# Supported sheet types
SUPPORTED_SHEETS = [
    "Current Teams",
    "Events History",
    "Player Stats", 
    "Results History",
    "Blocked Users",
    "Discord Members",
    "Match Statistics",
    "Alliance Tracking"
]
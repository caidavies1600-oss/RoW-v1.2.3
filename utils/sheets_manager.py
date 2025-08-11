import asyncio
import time
import random
from typing import Any, Optional
from utils.logger import setup_logger
from contextlib import asynccontextmanager
from datetime import datetime

logger = setup_logger("sheets_manager")

try:
    import gspread
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

class SheetsManager:
    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.client = None
        self.spreadsheet = None
        self.last_request = 0
        self.min_request_interval = 1.1  # Seconds between requests
        self.max_retries = 3
        self.spreadsheet_id = spreadsheet_id
        self._initialize(spreadsheet_id)
    def _initialize(self, spreadsheet_id: Optional[str]):
        try:
            if GSPREAD_AVAILABLE:
                self.client = gspread.service_account()
                if spreadsheet_id:
                    self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            else:
                logger.warning("gspread not available, sheets functionality disabled")
        except Exception as e:
            logger.error(f"Failed to initialize sheets manager: {e}")
            self.client = None
            self.spreadsheet = None
            # ...existing initialization code...

    def is_connected(self) -> bool:
        """Check if sheets client is properly connected."""
        return self.client is not None and GSPREAD_AVAILABLE

    async def _rate_limited_request(self, func):
        """Execute request with rate limiting and retries."""
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                now = time.time()
                if now - self.last_request < self.min_request_interval:
                    await asyncio.sleep(self.min_request_interval)
                
                result = await asyncio.to_thread(func)
                self.last_request = time.time()
                return result

            except gspread.exceptions.APIError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = (2 ** attempt) + random.random()
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                raise
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)

    async def sync_blocked_users(self, data: dict) -> bool:
        """Sync blocked users to Google Sheets."""
        if not self.is_connected():
            return False
            
        try:
            def _update():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                worksheet = self.spreadsheet.worksheet("Blocked Users")
                # ...update sheet with data...
                
            await self._rate_limited_request(_update)
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync blocked users: {e}")
            return False

    async def sync_results(self, data: Any) -> bool:
        """Sync results to Google Sheets."""
        if not self.is_connected():
            return False
            
        try:
            def _update():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                worksheet = self.spreadsheet.worksheet("Results")
                # ...update sheet with data...
                
            await self._rate_limited_request(_update)
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync results: {e}")
            return False

    async def sync_data(self, filepath: str, data: Any) -> bool:
        """Smart sync based on file type."""
        async with self._rate_limit():
            try:
                if "blocked" in filepath:
                    return await self.sync_blocked_users(data)
                elif "results" in filepath:
                    return await self.sync_results(data)
                # ...handle other file types...
                return True
            except Exception as e:
                logger.error(f"Sheet sync failed: {e}")
                return False
    @asynccontextmanager
    async def _rate_limit(self):
        """Rate limiting context manager."""
        now = time.time()
        if now - self.last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval)
        try:
            yield
        finally:
            self.last_request = time.time()
            self.last_request = time.time()

    def create_all_templates(self, data: dict) -> bool:
        """
        Create all necessary templates in Google Sheets.
        
        Args:
            data: Dictionary containing all data needed for templates
            
        Returns:
            bool: True if all critical templates were created
        """
        if not self.spreadsheet:
            logger.error("No spreadsheet connection available")
            return False

        try:
            success_count = 0
            templates = [
                ("Current Teams", lambda: self._create_teams_template(data.get("events", {}))),
                ("Player Stats", lambda: self._create_stats_template(data.get("player_stats", {}))),
                ("Results History", lambda: self._create_results_template(data.get("results", {}))),
                ("Events History", lambda: self._create_history_template(data.get("events_history", {}))),
                ("Blocked Users", lambda: self._create_blocked_template(data.get("blocked", {}))),
                ("IGN Mappings", lambda: self._create_ign_template(data.get("ign_map", {}))),
                ("Notification Preferences", lambda: self._create_notifications_template(data.get("notification_preferences", {})))
            ]

            for name, create_func in templates:
                try:
                    worksheet = self._get_or_create_sheet(name)
                    if create_func():
                        success_count += 1
                        logger.info(f"✅ Created template: {name}")
                except Exception as e:
                    logger.error(f"Failed to create {name} template: {e}")

            # Consider successful if majority of templates created
            return success_count >= len(templates) // 2

        except Exception as e:
            logger.error(f"Failed to create templates: {e}")
            return False

    def _get_or_create_sheet(self, name: str):
        """Get existing worksheet or create new one."""
        if not self.spreadsheet:
            raise ValueError("No spreadsheet available")
        try:
            return self.spreadsheet.worksheet(name)
        except:
            return self.spreadsheet.add_worksheet(name, 1000, 26)

    def _update_sheet(self, worksheet, values: list, range_name: str):
        """Safely update worksheet with proper typing."""
        if not worksheet:
            return False
        try:
            worksheet.update(range_name, values)
            return True
        except Exception as e:
            logger.error(f"Failed to update sheet: {e}")
            return False

    def get_spreadsheet_url(self) -> str:
        """
        Get the URL of the managed spreadsheet.

        Returns:
            str: Google Sheets URL or empty string if not available
        """
        if self.spreadsheet and hasattr(self.spreadsheet, 'url'):
            return self.spreadsheet.url
        elif hasattr(self, 'spreadsheet_id'):
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return ""

    def create_error_summary(self):
        """Create comprehensive Error Summary sheet with formatting."""
        try:
            worksheet = self._get_or_create_sheet("Error Summary")
            
            # Set up headers
            headers = [
                "🕐 Timestamp", "⚠️ Error Type", "💬 Command", 
                "👤 User ID", "📝 Error Message", "🔍 Traceback",
                "⚡ Severity", "🛠️ Status", "📋 Notes"
            ]
            
            worksheet.update(values=[headers], range_name='A1:I1')
            # ...formatting implementation...
            
            return True
        except Exception as e:
            logger.error(f"Failed to create error summary: {e}")
            return False

    def _create_teams_template(self, data: dict) -> bool:
        """Create Current Teams sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Current Teams")
            
            # Update headers
            headers = [["Team", "Players", "Count", "Last Updated"]]
            self._update_sheet(worksheet, headers, 'A1:D1')
            
            # Add sample data
            rows = []
            for team in ["main_team", "team_2", "team_3"]:
                players = data.get(team, [])
                rows.append([
                    team.replace("_", " ").title(),
                    ", ".join(players),
                    len(players),
                    datetime.now().strftime("%Y-%m-%d %H:%M UTC")
                ])
            
            if rows:
                self._update_sheet(worksheet, rows, 'A2:D4')
            return True
            
        except Exception as e:
            logger.error(f"Failed to create teams template: {e}")
            return False

    def _create_stats_template(self, data: dict) -> bool:
        """Create Player Stats sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Player Stats")
            headers = [["Player ID", "Name", "Wins", "Losses", "Win Rate", "Power Rating"]]
            return self._update_sheet(worksheet, headers, 'A1:F1')
        except Exception as e:
            logger.error(f"Failed to create stats template: {e}")
            return False

    def _create_results_template(self, data: dict) -> bool:
        """Create Results History sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Results History")
            headers = ["Date", "Team", "Result", "Players", "Notes"]
            worksheet.update(values=[headers], range_name='A1:E1')
            return True
        except Exception as e:
            logger.error(f"Failed to create results template: {e}")
            return False

    def _create_history_template(self, data: dict) -> bool:
        """Create Events History sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Events History")
            headers = ["Date", "Event Type", "Teams", "Participants", "Status"]
            worksheet.update(values=[headers], range_name='A1:E1')
            return True
        except Exception as e:
            logger.error(f"Failed to create history template: {e}")
            return False

    def _create_blocked_template(self, data: dict) -> bool:
        """Create Blocked Users sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Blocked Users")
            headers = ["User ID", "Name", "Blocked By", "Blocked At", "Duration", "Expires"]
            worksheet.update(values=[headers], range_name='A1:F1')
            return True
        except Exception as e:
            logger.error(f"Failed to create blocked template: {e}")
            return False

    def _create_ign_template(self, data: dict) -> bool:
        """Create IGN Mappings sheet template."""
        try:
            worksheet = self._get_or_create_sheet("IGN Mappings")
            headers = ["Discord ID", "Discord Name", "In-Game Name", "Last Updated"]
            worksheet.update(values=[headers], range_name='A1:D1')
            return True
        except Exception as e:
            logger.error(f"Failed to create IGN template: {e}")
            return False

    def _create_notifications_template(self, data: dict) -> bool:
        """Create Notification Preferences sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Notification Preferences")
            headers = ["User ID", "Name", "DM Reminders", "Mention Type", "Custom Message"]
            worksheet.update(values=[headers], range_name='A1:E1')
            return True
        except Exception as e:
            logger.error(f"Failed to create notifications template: {e}")
            return False

    async def append_error(self, error_entry: dict) -> bool:
        """
        Append an error entry to the Error Summary sheet.
        
        Args:
            error_entry: Dictionary containing error details
            
        Returns:
            bool: Success status of append operation
        """
        if not self.is_connected():
            return False
            
        try:
            def _append():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                    
                worksheet = self._get_or_create_sheet("Error Summary")
                row = [
                    error_entry.get("timestamp", ""),
                    error_entry.get("error_type", "Unknown"),
                    error_entry.get("command", ""),
                    error_entry.get("user_id", "System"),
                    error_entry.get("error_message", "")[:500],  # Truncate long messages
                    error_entry.get("traceback", "")[:500],      # Truncate long tracebacks
                    error_entry.get("severity", "Medium"),
                    "Open",  # Default status
                    ""      # Empty notes field
                ]
                worksheet.append_row(row)
                
            await self._rate_limited_request(_append)
            return True
            
        except Exception as e:
            logger.error(f"Failed to append error to sheets: {e}")
            return False

    # ...existing code...

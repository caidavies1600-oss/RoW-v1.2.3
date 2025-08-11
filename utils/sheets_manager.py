import asyncio
import time
import random
from typing import Any, Optional
from utils.logger import setup_logger
from contextlib import asynccontextmanager

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
        try:
            return self.spreadsheet.worksheet(name)
        except:
            return self.spreadsheet.add_worksheet(name, 1000, 26)

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
            
            worksheet.update('A1:I1', [headers])
            # ...formatting implementation...
            
            return True
        except Exception as e:
            logger.error(f"Failed to create error summary: {e}")
            return False

    # ...similar improvements for other sheet operations...

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

    # ...similar improvements for other sheet operations...

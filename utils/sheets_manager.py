import asyncio
from typing import Optional, Any
import gspread
from utils.logger import setup_logger

logger = setup_logger("sheets_manager")

class SheetsManager:
    def __init__(self):
        self.client = None
        self.last_request = 0
        self.min_request_interval = 1.1  # Seconds between requests
        self.max_retries = 3
        self._initialize()

    def _initialize(self):
        try:
            // ...existing initialization code...

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
                worksheet = self.spreadsheet.worksheet("Blocked Users")
                // ...update sheet with data...
                
            await self._rate_limited_request(_update)
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync blocked users: {e}")
            return False

    // ...similar improvements for other sheet operations...

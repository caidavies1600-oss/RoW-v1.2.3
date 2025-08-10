        import gspread
        from google.oauth2.service_account import Credentials
        import json
        import os
        import time
        import random
        import threading
        from datetime import datetime, timedelta
        from typing import Dict, List, Optional, Callable, Any
        from collections import deque
        from utils.logger import setup_logger

        logger = setup_logger("sheets_base")

        class RateLimitTracker:
            """Advanced rate limiting and quota tracking for Google Sheets API."""

            def __init__(self):
                self.request_history = deque()  # Store (timestamp, request_type) tuples
                self.read_requests_per_minute = 0
                self.write_requests_per_minute = 0
                self.total_requests = 0
                self.last_request_time = 0
                self.min_request_interval = 0.1  # 100ms between requests
                self.lock = threading.Lock()

                # Google Sheets API limits (conservative estimates)
                self.limits = {
                    'read_requests_per_minute': 250,  # Conservative (actual: 300)
                    'write_requests_per_minute': 80,   # Conservative (actual: 100)
                    'total_requests_per_100_seconds': 450,  # Conservative (actual: 500)
                    'requests_per_user_per_100_seconds': 90   # Conservative (actual: 100)
                }

            def track_request(self, request_type: str = 'read'):
                """Track a new API request."""
                with self.lock:
                    now = time.time()
                    self.request_history.append((now, request_type))
                    self.total_requests += 1
                    self.last_request_time = now
                    self._cleanup_old_requests()

            def _cleanup_old_requests(self):
                """Remove requests older than 100 seconds."""
                cutoff = time.time() - 100
                while self.request_history and self.request_history[0][0] < cutoff:
                    self.request_history.popleft()

            def get_current_usage(self) -> Dict[str, int]:
                """Get current usage statistics."""
                with self.lock:
                    self._cleanup_old_requests()
                    now = time.time()

                    # Count requests in last minute
                    minute_cutoff = now - 60
                    reads_last_minute = sum(1 for timestamp, req_type in self.request_history 
                                          if timestamp > minute_cutoff and req_type == 'read')
                    writes_last_minute = sum(1 for timestamp, req_type in self.request_history 
                                           if timestamp > minute_cutoff and req_type == 'write')

                    # Count total requests in last 100 seconds
                    total_last_100s = len(self.request_history)

                    return {
                        'reads_last_minute': reads_last_minute,
                        'writes_last_minute': writes_last_minute,
                        'total_last_100_seconds': total_last_100s,
                        'total_requests': self.total_requests
                    }

            def should_throttle(self, request_type: str = 'read') -> tuple[bool, float]:
                """Check if we should throttle the next request."""
                usage = self.get_current_usage()

                # Check read quota
                if request_type == 'read' and usage['reads_last_minute'] >= self.limits['read_requests_per_minute']:
                    return True, 60 - (time.time() % 60)

                # Check write quota
                if request_type == 'write' and usage['writes_last_minute'] >= self.limits['write_requests_per_minute']:
                    return True, 60 - (time.time() % 60)

                # Check total quota
                if usage['total_last_100_seconds'] >= self.limits['total_requests_per_100_seconds']:
                    return True, 100 - (time.time() % 100)

                # Check minimum interval
                if self.last_request_time > 0:
                    time_since_last = time.time() - self.last_request_time
                    if time_since_last < self.min_request_interval:
                        return True, self.min_request_interval - time_since_last

                return False, 0

        class EnhancedBaseSheetsManager:
            """Enhanced base manager with advanced rate limiting and error handling."""

            def __init__(self):
                self.gc = None
                self.spreadsheet = None
                self.rate_tracker = RateLimitTracker()
                self.retry_attempts = 5
                self.max_backoff_time = 64
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

            def rate_limited_request(self, func: Callable, request_type: str = 'read', *args, **kwargs) -> Any:
                """Execute a request with rate limiting and exponential backoff."""
                # Check if we should throttle
                should_throttle, wait_time = self.rate_tracker.should_throttle(request_type)
                if should_throttle:
                    logger.warning(f"Rate limit approaching, waiting {wait_time:.2f}s for {request_type} request")
                    time.sleep(wait_time)

                # Execute with exponential backoff
                return self.exponential_backoff_retry(func, request_type, *args, **kwargs)

            def exponential_backoff_retry(self, func: Callable, request_type: str, *args, **kwargs) -> Any:
                """Execute function with exponential backoff on rate limit errors."""
                for attempt in range(self.retry_attempts):
                    try:
                        # Track the request
                        self.rate_tracker.track_request(request_type)

                        # Execute the function
                        result = func(*args, **kwargs)

                        # Log successful request
                        if attempt > 0:
                            logger.info(f"✅ Request succeeded on attempt {attempt + 1}")

                        return result

                    except gspread.exceptions.APIError as e:
                        if hasattr(e, 'response') and e.response.status_code == 429:
                            # Rate limit exceeded - use exponential backoff
                            wait_time = min((2 ** attempt) + random.uniform(0, 1), self.max_backoff_time)
                            logger.warning(f"⚠️ Rate limit hit (429), attempt {attempt + 1}/{self.retry_attempts}, waiting {wait_time:.2f}s")
                            time.sleep(wait_time)
                            continue
                        elif hasattr(e, 'response') and e.response.status_code in [503, 500]:
                            # Server error - shorter backoff
                            wait_time = min((1.5 ** attempt) + random.uniform(0, 0.5), 16)
                            logger.warning(f"⚠️ Server error ({e.response.status_code}), attempt {attempt + 1}/{self.retry_attempts}, waiting {wait_time:.2f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Other API error - don't retry
                            logger.error(f"❌ API error (non-retryable): {e}")
                            raise
                    except Exception as e:
                        # Non-API error - don't retry
                        logger.error(f"❌ Non-API error: {e}")
                        raise

                # All retries exhausted
                raise Exception(f"❌ Request failed after {self.retry_attempts} attempts with exponential backoff")

            def batch_update_with_rate_limiting(self, requests: List[Dict], batch_size: int = 100):
                """Execute batch updates with proper rate limiting."""
                if not self.spreadsheet:
                    logger.error("❌ Spreadsheet not initialized")
                    return False

                try:
                    total_batches = (len(requests) + batch_size - 1) // batch_size
                    logger.info(f"🔄 Processing {len(requests)} requests in {total_batches} batches of {batch_size}")

                    for i in range(0, len(requests), batch_size):
                        batch = requests[i:i + batch_size]
                        batch_num = i // batch_size + 1

                        logger.info(f"📝 Processing batch {batch_num}/{total_batches} ({len(batch)} requests)")

                        # Execute batch with rate limiting
                        self.rate_limited_request(
                            self.spreadsheet.batch_update,
                            'write',
                            {'requests': batch}
                        )

                        # Log progress
                        logger.info(f"✅ Batch {batch_num}/{total_batches} completed")

                        # Add delay between batches for large operations
                        if batch_num < total_batches and len(requests) > 500:
                            time.sleep(2)

                    logger.info(f"✅ All {total_batches} batches completed successfully")
                    return True

                except Exception as e:
                    logger.error(f"❌ Batch update failed: {e}")
                    return False

            def safe_worksheet_operation(self, operation: Callable, worksheet_title: str, *args, **kwargs) -> Any:
                """Safely execute worksheet operations with error handling."""
                try:
                    if not self.spreadsheet:
                        raise Exception("Spreadsheet not initialized")

                    # Get or create worksheet
                    try:
                        worksheet = self.spreadsheet.worksheet(worksheet_title)
                    except gspread.WorksheetNotFound:
                        logger.info(f"📄 Worksheet '{worksheet_title}' not found, creating it")
                        worksheet = self.spreadsheet.add_worksheet(title=worksheet_title, rows=1000, cols=26)

                    # Execute operation with rate limiting
                    return self.rate_limited_request(operation, 'write', worksheet, *args, **kwargs)

                except Exception as e:
                    logger.error(f"❌ Worksheet operation failed for '{worksheet_title}': {e}")
                    raise

            def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
                """Get existing worksheet or create new one with rate limiting."""
                def _get_worksheet():
                    try:
                        return self.spreadsheet.worksheet(title)
                    except gspread.WorksheetNotFound:
                        logger.info(f"📄 Creating new worksheet: {title}")
                        return self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

                return self.rate_limited_request(_get_worksheet, 'read')

            def is_connected(self) -> bool:
                """Check if sheets connection is active."""
                return self.gc is not None and self.spreadsheet is not None

            def get_api_usage_stats(self) -> Dict[str, Any]:
                """Get comprehensive API usage statistics."""
                usage = self.rate_tracker.get_current_usage()
                limits = self.rate_tracker.limits

                return {
                    'current_usage': usage,
                    'limits': limits,
                    'utilization': {
                        'reads_percent': (usage['reads_last_minute'] / limits['read_requests_per_minute']) * 100,
                        'writes_percent': (usage['writes_last_minute'] / limits['write_requests_per_minute']) * 100,
                        'total_percent': (usage['total_last_100_seconds'] / limits['total_requests_per_100_seconds']) * 100
                    },
                    'is_throttling': self.rate_tracker.should_throttle()[0],
                    'last_request': datetime.fromtimestamp(self.rate_tracker.last_request_time) if self.rate_tracker.last_request_time > 0 else None
                }

            def log_usage_stats(self):
                """Log current API usage statistics."""
                stats = self.get_api_usage_stats()
                usage = stats['current_usage']
                util = stats['utilization']

                logger.info(f"📊 API Usage: Reads: {usage['reads_last_minute']}/250 ({util['reads_percent']:.1f}%), "
                           f"Writes: {usage['writes_last_minute']}/80 ({util['writes_percent']:.1f}%), "
                           f"Total: {usage['total_last_100_seconds']}/450 ({util['total_percent']:.1f}%)")

            def smart_delay(self, operation_size: str = 'small'):
                """Add intelligent delays based on operation size."""
                delays = {
                    'small': 0.1,    # Single cell updates
                    'medium': 0.5,   # Row operations
                    'large': 2.0,    # Batch operations
                    'xlarge': 5.0    # Full sheet operations
                }

                delay = delays.get(operation_size, 0.1)
                if delay > 0.1:
                    logger.debug(f"⏱️ Smart delay: {delay}s for {operation_size} operation")
                time.sleep(delay)

            def reset_rate_tracking(self):
                """Reset rate tracking (useful for testing or debugging)."""
                self.rate_tracker = RateLimitTracker()
                logger.info("🔄 Rate tracking reset")

            def wait_for_quota_reset(self, quota_type: str = 'minute'):
                """Wait for quota to reset."""
                if quota_type == 'minute':
                    wait_time = 60 - (time.time() % 60)
                    logger.info(f"⏳ Waiting {wait_time:.1f}s for minute quota reset")
                else:
                    wait_time = 100 - (time.time() % 100)
                    logger.info(f"⏳ Waiting {wait_time:.1f}s for 100-second quota reset")

                time.sleep(wait_time + 1)  # Add 1 second buffer
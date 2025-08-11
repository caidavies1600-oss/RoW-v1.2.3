"""
Base Google Sheets manager with rate limiting and error handling.

Features:
- Rate-limited API access with exponential backoff
- Comprehensive error handling and recovery
- Batch operation support
- Worksheet management
- Usage tracking and statistics
- Auto-reconnection on failures
"""

import json
import os
import random
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import gspread
from google.oauth2.service_account import Credentials

from utils.logger import setup_logger

logger = setup_logger("sheets_base")


class RateLimitedSheetsManager:
    """
    Enhanced Google Sheets manager with comprehensive rate limiting and error recovery.

    Features:
    - Automatic retry with exponential backoff
    - Request rate limiting and quota management
    - Batch operations for large updates
    - Usage statistics and monitoring
    - Automatic worksheet creation/management
    - Error handling with detailed logging
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
        self.api_quota_used = 0
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

    def exponential_backoff_retry(
        self, func: Callable, max_retries: Optional[int] = None
    ) -> Any:
        """
        Execute function with exponential backoff on rate limit errors.

        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts

        Returns:
            Any: Result of the function execution

        Raises:
            Exception: If all retries fail or non-retryable error occurs

        Features:
            - Exponential delay between retries
            - Random jitter to prevent thundering herd
            - Different handling for various error types
            - Quota exceeded detection
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_exception = None

        for attempt in range(max_retries):
            try:
                result = func()
                if attempt > 0:
                    logger.info(f"✅ Request succeeded after {attempt} retries")
                return result

            except gspread.exceptions.APIError as e:
                last_exception = e

                # Check if it's a rate limit error (429)
                if hasattr(e, "response") and e.response.status_code == 429:
                    self.rate_limit_hits += 1
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    max_wait = min(wait_time, 64)  # Cap at 64 seconds

                    logger.warning(
                        f"⏳ Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {max_wait:.2f}s..."
                    )
                    time.sleep(max_wait)
                    continue

                # Check for quota exceeded (403)
                elif hasattr(e, "response") and e.response.status_code == 403:
                    if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                        logger.error("🚫 Google Sheets API quota exceeded for today")
                        raise Exception(
                            "Google Sheets API quota exceeded. Try again tomorrow."
                        )
                    else:
                        # Other 403 errors (permissions, etc.)
                        logger.error(f"🚫 Permission error: {e}")
                        raise

                # For other API errors, retry with backoff
                elif hasattr(e, "response") and e.response.status_code >= 500:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    max_wait = min(wait_time, 32)
                    logger.warning(
                        f"🔄 Server error {e.response.status_code} (attempt {attempt + 1}/{max_retries}). Retrying in {max_wait:.2f}s..."
                    )
                    time.sleep(max_wait)
                    continue
                else:
                    # Non-retryable API error
                    logger.error(f"❌ Non-retryable API error: {e}")
                    raise

            except Exception as e:
                last_exception = e
                # For non-API errors, still retry a few times
                if attempt < 2:
                    wait_time = 1 + random.uniform(0, 1)
                    logger.warning(
                        f"🔄 Unexpected error (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    # Give up on non-API errors after 3 attempts
                    logger.error(
                        f"❌ Non-retryable error after {attempt + 1} attempts: {e}"
                    )
                    raise

        # If we get here, all retries failed
        logger.error(f"❌ Request failed after {max_retries} attempts")
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"Request failed after {max_retries} attempts")

    def rate_limited_request(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute request with rate limiting and comprehensive error handling.

        Args:
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function

        Returns:
            Any: Result of the function execution

        Features:
            - Enforces minimum interval between requests
            - Tracks request count and rate limit hits
            - Logs usage statistics periodically
            - Handles API errors with retries
        """
        # Enforce minimum interval between requests
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        # Update tracking
        self.last_request_time = time.time()
        self.request_count += 1

        # Log every 100 requests for monitoring
        if self.request_count % 100 == 0:
            logger.info(
                f"📊 API Usage: {self.request_count} requests, {self.rate_limit_hits} rate limit hits"
            )

        # Execute with exponential backoff
        if args or kwargs:
            return self.exponential_backoff_retry(lambda: func(*args, **kwargs))
        else:
            return self.exponential_backoff_retry(func)

    def batch_update_cells(self, worksheet, updates: list, batch_size: int = 50):
        """
        Update multiple cells in batches with aggressive rate limiting.

        Args:
            worksheet: Google Sheets worksheet object
            updates: List of cell updates to perform
            batch_size: Number of updates per batch

        Features:
            - Progressive delays between batches
            - Progress tracking and logging
            - Error handling per batch
            - Rate limit compliance
        """
        if not updates:
            return True

        logger.info(
            f"🔄 Starting batch update: {len(updates)} updates in batches of {batch_size}"
        )

        try:
            for i in range(0, len(updates), batch_size):
                batch = updates[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(updates) - 1) // batch_size + 1

                logger.info(
                    f"📝 Processing batch {batch_num}/{total_batches} ({len(batch)} updates)"
                )

                # Convert updates to the format expected by gspread
                batch_data = []
                for update in batch:
                    if isinstance(update, dict):
                        batch_data.append(update)
                    else:
                        # Assume it's a simple row
                        batch_data.append(update)

                # Execute batch update with rate limiting
                if batch_data:
                    self.rate_limited_request(worksheet.append_rows, batch_data)

                # Progressive delay - longer delays for larger batches
                if batch_num < total_batches:
                    delay = min(2 + (batch_num * 0.1), 5)  # 2-5 second delays
                    logger.debug(
                        f"⏸️ Batch {batch_num} complete. Waiting {delay:.1f}s before next batch..."
                    )
                    time.sleep(delay)

            logger.info(
                f"✅ Batch update completed successfully: {len(updates)} updates processed"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Batch update failed: {e}")
            return False

    def safe_worksheet_operation(
        self, operation_name: str, operation_func: Callable
    ) -> Any:
        """
        Safely execute worksheet operations with comprehensive error handling.

        Args:
            operation_name: Name of operation for logging
            operation_func: Function performing the worksheet operation

        Returns:
            Any: Result of the operation or None on failure

        Features:
            - Detailed error context
            - Helpful error hints
            - Operation logging
            - Rate limit compliance
        """
        try:
            logger.debug(f"🔄 Executing {operation_name}...")
            result = self.rate_limited_request(operation_func)
            logger.debug(f"✅ {operation_name} completed successfully")
            return result

        except Exception as e:
            logger.error(f"❌ {operation_name} failed: {e}")

            # Try to provide helpful error context
            if "worksheet" in str(e).lower():
                logger.error(
                    "💡 Hint: Check if the worksheet exists and has proper permissions"
                )
            elif "range" in str(e).lower():
                logger.error(
                    "💡 Hint: Check if the cell range is valid (e.g., A1:Z100)"
                )
            elif "quota" in str(e).lower():
                logger.error("💡 Hint: Google Sheets API quota may be exceeded")
            elif "permission" in str(e).lower():
                logger.error(
                    "💡 Hint: Check if the service account has edit permissions"
                )

            return None

    def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
        """
        Get existing worksheet or create new one with rate limiting.

        Args:
            title: Name of the worksheet
            rows: Initial number of rows
            cols: Initial number of columns

        Returns:
            Worksheet object or None on failure

        Features:
            - Checks for existing worksheet
            - Creates new if not found
            - Rate limited operations
            - Error handling and logging
        """
        if not self.spreadsheet:
            logger.error("❌ No spreadsheet available")
            return None

        try:
            # Try to get existing worksheet
            worksheet = self.rate_limited_request(
                lambda: self.spreadsheet.worksheet(title)
            )
            logger.debug(f"✅ Found existing worksheet: {title}")
            return worksheet

        except gspread.WorksheetNotFound:
            logger.info(f"📄 Creating new worksheet: {title}")
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

    def is_connected(self) -> bool:
        """Check if sheets connection is active and functional."""
        if not self.gc or not self.spreadsheet:
            return False

        try:
            # Test connection with a simple operation
            self.rate_limited_request(lambda: self.spreadsheet.worksheets())
            return True
        except:
            return False

    def get_api_usage_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive API usage statistics.

        Returns:
            dict containing:
            - total_requests: Total API requests made
            - rate_limit_hits: Number of rate limit hits
            - session_duration_minutes: Session duration
            - requests_per_minute: Request rate
            - quota_health: Health status of quota usage
            - estimated_quota_used_percent: Estimated quota consumption
        """
        session_duration = time.time() - self.session_start_time

        return {
            "total_requests": self.request_count,
            "rate_limit_hits": self.rate_limit_hits,
            "session_duration_minutes": round(session_duration / 60, 2),
            "requests_per_minute": round(
                self.request_count / (session_duration / 60), 2
            )
            if session_duration > 0
            else 0,
            "last_request_time": self.last_request_time,
            "min_request_interval": self.min_request_interval,
            "quota_health": "good"
            if self.rate_limit_hits < 5
            else "warning"
            if self.rate_limit_hits < 20
            else "critical",
            "estimated_quota_used_percent": min(
                (self.request_count / 300) * 100, 100
            ),  # Conservative estimate
        }

    def log_usage_summary(self):
        """Log a comprehensive usage summary."""
        stats = self.get_api_usage_stats()

        logger.info("📊 Google Sheets API Usage Summary:")
        logger.info(f"  📞 Total Requests: {stats['total_requests']}")
        logger.info(f"  ⏳ Rate Limit Hits: {stats['rate_limit_hits']}")
        logger.info(
            f"  🕐 Session Duration: {stats['session_duration_minutes']} minutes"
        )
        logger.info(f"  📈 Requests/Minute: {stats['requests_per_minute']}")
        logger.info(f"  💾 Quota Health: {stats['quota_health']}")
        logger.info(
            f"  📊 Estimated Quota Used: {stats['estimated_quota_used_percent']:.1f}%"
        )

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

            # Add current data with enhanced status indicators
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            team_mapping = {
                "main_team": "🏆 Main Team",
                "team_2": "🥈 Team 2",
                "team_3": "🥉 Team 3",
            }

            team_rows = []
            for team_key, players in events_data.items():
                team_name = team_mapping.get(
                    team_key, team_key.replace("_", " ").title()
                )
                player_count = len(players)
                player_list = (
                    ", ".join(str(p) for p in players) if players else "No signups"
                )

                # Enhanced status with emojis
                if player_count >= 8:
                    status = "🟢 Ready"
                elif player_count >= 5:
                    status = "🟡 Partial"
                elif player_count > 0:
                    status = "🟠 Low"
                else:
                    status = "🔴 Empty"

                row = [timestamp, team_name, player_count, player_list, status]
                team_rows.append(row)

            # Add all team data
            for row in team_rows:
                self.rate_limited_request(worksheet.append_row, row)

            # Apply formatting
            self._apply_teams_formatting(worksheet, len(team_rows) + 1)

            logger.info("✅ Synced current teams to Google Sheets with formatting")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def _apply_teams_formatting(self, worksheet, max_row):
        """Apply formatting to current teams worksheet."""
        try:
            # Header formatting
            self.rate_limited_request(
                worksheet.format,
                "A1:E1",
                {
                    "backgroundColor": {"red": 0.1, "green": 0.7, "blue": 0.1},
                    "textFormat": {
                        "bold": True,
                        "fontSize": 12,
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    },
                    "horizontalAlignment": "CENTER",
                },
            )

            # Freeze header
            self.rate_limited_request(worksheet.freeze, rows=1)

            # Status column conditional formatting with simpler approach
            status_range = f"E2:E{max_row + 10}"

            # Apply status formatting using batch requests
            format_requests = []

            # Green for Ready status
            format_requests.append(
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 1,
                                    "endRowIndex": max_row + 10,
                                    "startColumnIndex": 4,
                                    "endColumnIndex": 5,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": "TEXT_CONTAINS",
                                    "values": [{"userEnteredValue": "🟢"}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 0.8,
                                        "green": 1.0,
                                        "blue": 0.8,
                                    }
                                },
                            },
                        },
                        "index": 0,
                    }
                }
            )

            # Yellow for Partial status
            format_requests.append(
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 1,
                                    "endRowIndex": max_row + 10,
                                    "startColumnIndex": 4,
                                    "endColumnIndex": 5,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": "TEXT_CONTAINS",
                                    "values": [{"userEnteredValue": "🟡"}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 1.0,
                                        "green": 1.0,
                                        "blue": 0.8,
                                    }
                                },
                            },
                        },
                        "index": 1,
                    }
                }
            )

            # Red for Low/Empty status
            format_requests.append(
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 1,
                                    "endRowIndex": max_row + 10,
                                    "startColumnIndex": 4,
                                    "endColumnIndex": 5,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": "TEXT_CONTAINS",
                                    "values": [{"userEnteredValue": "🔴"}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 1.0,
                                        "green": 0.8,
                                        "blue": 0.8,
                                    }
                                },
                            },
                        },
                        "index": 2,
                    }
                }
            )

            # Execute batch formatting
            try:
                self.rate_limited_request(
                    self.spreadsheet.batch_update, {"requests": format_requests}
                )
            except Exception as batch_error:
                logger.warning(
                    f"Batch formatting failed, using fallback: {batch_error}"
                )
                # Fallback to simple background colors
                try:
                    self.rate_limited_request(
                        worksheet.format, status_range, {"textFormat": {"bold": True}}
                    )
                except Exception as fallback_error:
                    logger.warning(f"Fallback formatting also failed: {fallback_error}")

            # Auto-resize columns
            self.rate_limited_request(worksheet.columns_auto_resize, 0, 5)

            logger.info("✅ Applied formatting to Current Teams sheet")

        except Exception as e:
            logger.warning(f"⚠️ Failed to apply teams formatting: {e}")

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

            # Add history data with enhanced formatting
            history = results_data.get("history", [])
            team_mapping = {
                "main_team": "🏆 Main Team",
                "team_2": "🥈 Team 2",
                "team_3": "🥉 Team 3",
            }

            for entry in history:
                # Format date
                try:
                    date = entry.get("date", entry.get("timestamp", "Unknown"))
                    if "T" in str(date):  # ISO format
                        date = datetime.fromisoformat(
                            date.replace("Z", "+00:00")
                        ).strftime("%Y-%m-%d %H:%M")
                except:
                    date = str(entry.get("date", "Unknown"))

                # Format team and result
                team = entry.get("team", "Unknown")
                team_display = team_mapping.get(team, team.replace("_", " ").title())

                result = entry.get("result", "Unknown").lower()
                if result == "win":
                    result_display = "✅ Victory"
                elif result == "loss":
                    result_display = "❌ Defeat"
                else:
                    result_display = result.capitalize()

                players = ", ".join(entry.get("players", []))
                recorded_by = entry.get("by", entry.get("recorded_by", "Unknown"))
                notes = entry.get("notes", "")

                row = [
                    date,
                    team_display,
                    result_display,
                    players,
                    recorded_by,
                    notes,
                    results_data.get("total_wins", 0),
                    results_data.get("total_losses", 0),
                ]
                self.rate_limited_request(worksheet.append_row, row)

            # Apply formatting
            self._apply_results_formatting(worksheet, len(history) + 1)

            logger.info(
                f"✅ Synced {len(history)} results to Google Sheets with formatting"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync results history: {e}")
            return False

    def _apply_results_formatting(self, worksheet, max_row):
        """Apply formatting to results history worksheet."""
        try:
            # Header formatting
            self.rate_limited_request(
                worksheet.format,
                "A1:H1",
                {
                    "backgroundColor": {"red": 0.6, "green": 0.2, "blue": 0.8},
                    "textFormat": {
                        "bold": True,
                        "fontSize": 12,
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    },
                    "horizontalAlignment": "CENTER",
                },
            )

            # Freeze header
            self.rate_limited_request(worksheet.freeze, rows=1)

            # Result column conditional formatting with batch requests
            result_range = f"C2:C{max_row + 20}"

            format_requests = []

            # Green for victories
            format_requests.append(
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 1,
                                    "endRowIndex": max_row + 20,
                                    "startColumnIndex": 2,
                                    "endColumnIndex": 3,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": "TEXT_CONTAINS",
                                    "values": [{"userEnteredValue": "✅"}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 0.8,
                                        "green": 1.0,
                                        "blue": 0.8,
                                    },
                                    "textFormat": {"bold": True},
                                },
                            },
                        },
                        "index": 0,
                    }
                }
            )

            # Red for defeats
            format_requests.append(
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 1,
                                    "endRowIndex": max_row + 20,
                                    "startColumnIndex": 2,
                                    "endColumnIndex": 3,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": "TEXT_CONTAINS",
                                    "values": [{"userEnteredValue": "❌"}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 1.0,
                                        "green": 0.8,
                                        "blue": 0.8,
                                    },
                                    "textFormat": {"bold": True},
                                },
                            },
                        },
                        "index": 1,
                    }
                }
            )

            # Execute batch formatting
            try:
                self.rate_limited_request(
                    self.spreadsheet.batch_update, {"requests": format_requests}
                )
            except Exception as batch_error:
                logger.warning(f"Results batch formatting failed: {batch_error}")
                # Apply basic formatting as fallback
                try:
                    self.rate_limited_request(
                        worksheet.format, result_range, {"textFormat": {"bold": True}}
                    )
                except Exception as fallback_error:
                    logger.warning(
                        f"Results fallback formatting failed: {fallback_error}"
                    )

            # Format totals columns
            totals_range = f"G2:H{max_row + 20}"
            self.rate_limited_request(
                worksheet.format,
                totals_range,
                {
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 1.0},
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER",
                },
            )

            # Auto-resize columns
            self.rate_limited_request(worksheet.columns_auto_resize, 0, 8)

            logger.info("✅ Applied formatting to Results History sheet")

        except Exception as e:
            logger.warning(f"⚠️ Failed to apply results formatting: {e}")

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
        """Create all sheet templates for manual data entry."""
        if not self.is_connected():
            logger.warning("Google Sheets not initialized, skipping template creation")
            return False

        try:
            success_count = 0

            # Create current teams template
            if self.sync_current_teams(all_data.get("events", {})):
                success_count += 1
                logger.info("✅ Current Teams template created")

            # Create results history template
            if self.sync_results_history(all_data.get("results", {})):
                success_count += 1
                logger.info("✅ Results History template created")

            # Create player stats template with proper formatting
            if self.create_player_stats_template(all_data.get("player_stats", {})):
                success_count += 1
                logger.info("✅ Player Stats template created")

            # Create additional templates if methods exist
            try:
                if hasattr(self, "create_match_statistics_template"):
                    if self.create_match_statistics_template():
                        success_count += 1
                        logger.info("✅ Match Statistics template created")

                if hasattr(self, "create_alliance_tracking_sheet"):
                    if self.create_alliance_tracking_sheet():
                        success_count += 1
                        logger.info("✅ Alliance Tracking template created")
            except Exception as template_error:
                logger.warning(
                    f"⚠️ Additional template creation failed: {template_error}"
                )

            # Add new template creation methods here
            if self.create_error_summary_template():
                success_count += 1
                logger.info("✅ Error Summary template created")

            if self.create_dashboard_summary_template():
                success_count += 1
                logger.info("✅ Dashboard Summary template created")

            logger.info(
                f"✅ Template creation completed: {success_count} operations successful"
            )
            return success_count >= 3  # Consider successful if most operations work

        except Exception as e:
            logger.error(f"❌ Failed to create templates: {e}")
            return False

    def create_player_stats_template(self, player_stats):
        """Create player stats template with current players for manual data entry."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Player Stats", 300, 21)
            if not worksheet:
                return False

            # Check if sheet already has data to avoid overwriting
            existing_data = self.rate_limited_request(worksheet.get_all_values)
            headers = [
                "User ID",
                "Display Name",
                "Main Team Role",
                "Main Wins",
                "Main Losses",
                "Team2 Wins",
                "Team2 Losses",
                "Team3 Wins",
                "Team3 Losses",
                "Total Wins",
                "Total Losses",
                "Win Rate",
                "Absents",
                "Blocked",
                "Power Rating",
                "Cavalry",
                "Mages",
                "Archers",
                "Infantry",
                "Whale Status",
                "Last Updated",
            ]

            # Only recreate if empty or headers don't match
            if len(existing_data) <= 1 or (
                existing_data and existing_data[0] != headers
            ):
                logger.info(
                    "Creating new player stats template with correct headers and formatting"
                )

                # Clear and set headers
                self.rate_limited_request(worksheet.clear)
                self.rate_limited_request(worksheet.append_row, headers)

                # Add template rows for current players with formulas
                if player_stats:
                    row_num = 2  # Start from row 2
                    for user_id, stats in player_stats.items():
                        row = [
                            user_id,
                            stats.get(
                                "name", stats.get("display_name", f"User_{user_id}")
                            ),
                            "No",  # Manual entry required
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,  # Win/Loss stats - manual entry
                            f"=D{row_num}+F{row_num}+H{row_num}",  # Total Wins formula
                            f"=E{row_num}+G{row_num}+I{row_num}",  # Total Losses formula
                            f"=IF(K{row_num}+J{row_num}=0,0,J{row_num}/(J{row_num}+K{row_num}))",  # Win Rate formula
                            stats.get("absents", 0),
                            "Yes" if stats.get("blocked", False) else "No",
                            "",  # Power rating - manual entry
                            "No",
                            "No",
                            "No",
                            "No",
                            "No",  # Specializations - manual entry
                            datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                        ]
                        self.rate_limited_request(worksheet.append_row, row)
                        row_num += 1

                # Apply comprehensive formatting
                self._apply_player_stats_formatting(
                    worksheet, len(player_stats) + 1 if player_stats else 2
                )

                logger.info(
                    "✅ Created player stats template with formulas and formatting"
                )
            else:
                logger.info("✅ Player stats sheet already exists with correct format")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create player stats template: {e}")
            return False

    def _apply_player_stats_formatting(self, worksheet, max_row):
        """Apply comprehensive formatting to player stats worksheet."""
        try:
            # Header formatting with professional colors
            self.rate_limited_request(
                worksheet.format,
                "A1:U1",
                {
                    "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                    "textFormat": {
                        "bold": True,
                        "fontSize": 12,
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                },
            )

            # Freeze header row
            self.rate_limited_request(worksheet.freeze, rows=1)

            # Data range formatting
            data_range = f"A2:U{max_row + 50}"  # Extra buffer for future entries
            self.rate_limited_request(
                worksheet.format,
                data_range,
                {
                    "textFormat": {"fontSize": 10},
                    "horizontalAlignment": "CENTER",
                    "borders": {
                        "top": {
                            "style": "SOLID",
                            "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                        },
                        "bottom": {
                            "style": "SOLID",
                            "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                        },
                        "left": {
                            "style": "SOLID",
                            "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                        },
                        "right": {
                            "style": "SOLID",
                            "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                        },
                    },
                },
            )

            # Win/Loss columns - green for wins, red for losses
            win_columns = [
                "D",
                "F",
                "H",
                "J",
            ]  # Main Wins, Team2 Wins, Team3 Wins, Total Wins
            for col in win_columns:
                self.rate_limited_request(
                    worksheet.format,
                    f"{col}2:{col}{max_row + 50}",
                    {
                        "backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85},
                        "textFormat": {"bold": True},
                    },
                )

            loss_columns = [
                "E",
                "G",
                "I",
                "K",
            ]  # Main Losses, Team2 Losses, Team3 Losses, Total Losses
            for col in loss_columns:
                self.rate_limited_request(
                    worksheet.format,
                    f"{col}2:{col}{max_row + 50}",
                    {
                        "backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85},
                        "textFormat": {"bold": True},
                    },
                )

            # Win Rate column with conditional formatting
            self.rate_limited_request(
                worksheet.format,
                f"L2:L{max_row + 50}",
                {
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 1.0},
                    "textFormat": {"bold": True},
                    "numberFormat": {"type": "PERCENT", "pattern": "0.0%"},
                },
            )

            # Power Rating column
            self.rate_limited_request(
                worksheet.format,
                f"O2:O{max_row + 50}",
                {
                    "backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.6},
                    "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
                },
            )

            # Specialization columns with distinct colors
            spec_colors = [
                {"red": 0.9, "green": 0.7, "blue": 0.7},  # Cavalry - reddish
                {"red": 0.7, "green": 0.7, "blue": 0.9},  # Mages - blueish
                {"red": 0.7, "green": 0.9, "blue": 0.7},  # Archers - greenish
                {"red": 0.9, "green": 0.9, "blue": 0.7},  # Infantry - yellowish
                {"red": 0.9, "green": 0.7, "blue": 0.9},  # Whale - purplish
            ]

            spec_columns = ["P", "Q", "R", "S", "T"]
            for i, col in enumerate(spec_columns):
                self.rate_limited_request(
                    worksheet.format,
                    f"{col}2:{col}{max_row + 50}",
                    {"backgroundColor": spec_colors[i], "textFormat": {"bold": True}},
                )

            # Auto-resize columns for better readability
            self.rate_limited_request(worksheet.columns_auto_resize, 0, 21)

            logger.info("✅ Applied comprehensive formatting to Player Stats sheet")

        except Exception as e:
            logger.warning(f"⚠️ Failed to apply comprehensive formatting: {e}")
            # Fall back to basic formatting
            try:
                self.rate_limited_request(
                    worksheet.format,
                    "A1:U1",
                    {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    },
                )
                self.rate_limited_request(worksheet.freeze, rows=1)
                logger.info("✅ Applied basic formatting as fallback")
            except Exception as basic_error:
                logger.error(f"❌ Even basic formatting failed: {basic_error}")

    async def full_sync_and_create_templates(self, bot, all_data, guild_id):
        """Perform a full sync and create all templates."""
        if not self.is_connected():
            return {"success": False, "error": "Sheets not available"}

        try:
            logger.info("🚀 Starting full sync and template creation...")

            # Get Discord members for enhanced data
            guild = bot.get_guild(guild_id)
            discord_members = {}
            new_members_added = 0
            existing_members_updated = 0

            if guild:
                for member in guild.members:
                    if not member.bot:
                        user_id = str(member.id)
                        discord_members[user_id] = {
                            "name": member.display_name,
                            "display_name": member.display_name,
                            "username": member.name,
                            "joined_at": member.joined_at.isoformat()
                            if member.joined_at
                            else None,
                        }

                        # Add to player_stats if not exists
                        if user_id not in all_data.get("player_stats", {}):
                            all_data.setdefault("player_stats", {})[user_id] = (
                                discord_members[user_id]
                            )
                            new_members_added += 1
                        else:
                            existing_members_updated += 1

            # Create all templates
            templates_success = self.create_all_templates(all_data)

            result = {
                "success": templates_success,
                "member_sync": {
                    "new_members_added": new_members_added,
                    "existing_members_updated": existing_members_updated,
                    "total_discord_members": len(discord_members),
                },
                "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None,
            }

            logger.info(
                f"✅ Full sync complete: {new_members_added} new members, {existing_members_updated} updated"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Full sync failed: {e}")
            return {"success": False, "error": str(e)}

    def create_match_statistics_template(self):
        """Create match statistics template for manual data entry."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Match Statistics", 500, 25)
            if not worksheet:
                return False

            # Only create template if sheet is empty
            existing_data = self.rate_limited_request(worksheet.get_all_values)
            if len(existing_data) <= 1:
                headers = [
                    "Match ID",
                    "Date",
                    "Team",
                    "Result",
                    "Enemy Alliance Name",
                    "Enemy Alliance Tag",
                    "Our Matchmaking Power",
                    "Our Lifestone Points",
                    "Our Occupation Points",
                    "Our Gathering Points",
                    "Our Total Kills",
                    "Our Total Wounded",
                    "Our Total Healed",
                    "Our Lifestone Obtained",
                    "Enemy Matchmaking Power",
                    "Enemy Lifestone Points",
                    "Enemy Occupation Points",
                    "Enemy Gathering Points",
                    "Enemy Total Kills",
                    "Enemy Total Wounded",
                    "Enemy Total Healed",
                    "Enemy Lifestone Obtained",
                    "Players Participated",
                    "Recorded By",
                    "Notes",
                ]

                self.rate_limited_request(worksheet.clear)
                self.rate_limited_request(worksheet.append_row, headers)

                # Add example row
                example_row = [
                    "MATCH_001",
                    "2025-08-10",
                    "main_team",
                    "Win",
                    "Enemy Alliance",
                    "EA",
                    "2500000000",
                    "1500",
                    "800",
                    "200",
                    "150",
                    "50",
                    "100",
                    "75",
                    "2400000000",
                    "1200",
                    "600",
                    "180",
                    "120",
                    "60",
                    "80",
                    "50",
                    "Player1, Player2, Player3",
                    "AdminUser",
                    "Great teamwork!",
                ]
                self.rate_limited_request(worksheet.append_row, example_row)

                # Format headers
                try:
                    self.rate_limited_request(
                        worksheet.format,
                        "A1:Y1",
                        {
                            "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                            },
                        },
                    )
                except Exception as format_error:
                    logger.warning(
                        f"Failed to format match statistics headers: {format_error}"
                    )

                logger.info("✅ Created match statistics template")
            else:
                logger.info("✅ Match statistics sheet already exists")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create match statistics template: {e}")
            return False

    def create_alliance_tracking_sheet(self):
        """Create alliance tracking sheet for enemy alliance performance."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.get_or_create_worksheet("Alliance Tracking", 200, 15)
            if not worksheet:
                return False

            # Only create template if sheet is empty
            existing_data = self.rate_limited_request(worksheet.get_all_values)
            if len(existing_data) <= 1:
                headers = [
                    "Alliance Name",
                    "Alliance Tag",
                    "Matches Against",
                    "Wins Against Them",
                    "Losses Against Them",
                    "Win Rate vs Them",
                    "Average Enemy Power",
                    "Difficulty Rating",
                    "Strategy Notes",
                    "Last Fought",
                    "Server/Kingdom",
                    "Alliance Level",
                    "Activity Level",
                    "Threat Level",
                    "Additional Notes",
                ]

                self.rate_limited_request(worksheet.clear)
                self.rate_limited_request(worksheet.append_row, headers)

                # Add example row
                example_row = [
                    "Example Alliance",
                    "EX",
                    5,
                    3,
                    2,
                    "60%",
                    "2400000000",
                    "Hard",
                    "They focus on cavalry rushes",
                    "2025-08-01",
                    "K123",
                    "High",
                    "Very Active",
                    "High",
                    "Strong in KvK events, watch out for their coordination",
                ]
                self.rate_limited_request(worksheet.append_row, example_row)

                # Format headers
                try:
                    self.rate_limited_request(
                        worksheet.format,
                        "A1:O1",
                        {
                            "backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.2},
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                            },
                        },
                    )
                except Exception as format_error:
                    logger.warning(
                        f"Failed to format alliance tracking headers: {format_error}"
                    )

                logger.info("✅ Created alliance tracking template")
            else:
                logger.info("✅ Alliance tracking sheet already exists")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create alliance tracking sheet: {e}")
            return False

    def create_error_summary_template(self):
        """Create error summary worksheet for bot diagnostics."""
        try:
            logger.info("Creating Error Summary worksheet...")

            worksheet = self.get_or_create_worksheet("Error Summary")

            # Headers for error tracking
            headers = [
                "Timestamp",
                "Error Type",
                "Command",
                "User ID",
                "Error Message",
                "Traceback",
                "Severity",
                "Status",
                "Notes",
            ]

            # Set headers
            worksheet.update("A1:I1", [headers])

            # Format headers
            worksheet.format(
                "A1:I1",
                {
                    "backgroundColor": {"red": 0.8, "green": 0.2, "blue": 0.2},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                },
            )

            # Add some sample data to show format
            sample_data = [
                [
                    "2025-01-05 20:00:00",
                    "CommandError",
                    "!formatsheets",
                    "123456789",
                    "Method not found",
                    "AttributeError: 'SheetsManager' object has no attribute...",
                    "Medium",
                    "Resolved",
                    "Added missing method",
                ]
            ]

            worksheet.update("A2:I2", sample_data)

            logger.info("✅ Error Summary worksheet created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create Error Summary worksheet: {e}")
            return False

    def create_dashboard_summary_template(self):
        """Create dashboard summary worksheet for bot overview."""
        try:
            logger.info("Creating Dashboard Summary worksheet...")

            worksheet = self.get_or_create_worksheet("Dashboard Summary")

            # Create overview section
            overview_headers = ["Metric", "Value", "Last Updated"]

            worksheet.update("A1:C1", [overview_headers])

            # Format headers
            worksheet.format(
                "A1:C1",
                {
                    "backgroundColor": {"red": 0.2, "green": 0.8, "blue": 0.2},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                },
            )

            # Add dashboard metrics
            dashboard_data = [
                ["Total Players", "0", "2025-01-05"],
                ["Total Wins", "0", "2025-01-05"],
                ["Total Losses", "0", "2025-01-05"],
                ["Win Rate", "0%", "2025-01-05"],
                ["Active Teams", "3", "2025-01-05"],
                ["Blocked Users", "0", "2025-01-05"],
                ["Recent Activity", "No recent activity", "2025-01-05"],
            ]

            worksheet.update("A2:C8", dashboard_data)

            # Add team status section
            worksheet.update("E1:G1", [["Team", "Members", "Status"]])
            worksheet.format(
                "E1:G1",
                {
                    "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.8},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                },
            )

            team_data = [
                ["Main Team", "0", "Active"],
                ["Team 2", "0", "Active"],
                ["Team 3", "0", "Active"],
            ]

            worksheet.update("E2:G4", team_data)

            logger.info("✅ Dashboard Summary worksheet created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create Dashboard Summary worksheet: {e}")
            return False

    def __del__(self):
        """Log usage summary when object is destroyed."""
        try:
            if hasattr(self, "request_count") and self.request_count > 0:
                self.log_usage_summary()
        except:
            pass


# For backward compatibility
class BaseSheetsManager(RateLimitedSheetsManager):
    """Alias for backward compatibility."""

    pass

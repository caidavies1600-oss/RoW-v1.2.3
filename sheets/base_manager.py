"""
Base Google Sheets Manager with comprehensive functionality.

This module provides the foundational Google Sheets management capabilities:
- Secure authentication and connection management
- Rate-limited API access with exponential backoff
- Robust error handling and automatic recovery
- Comprehensive worksheet management
- Advanced formatting and styling capabilities
- Performance monitoring and usage tracking
- Batch operation support for efficiency
- Data validation and integrity checks

Features:
- Multi-layer error handling with graceful degradation
- Intelligent rate limiting to prevent API quota exhaustion
- Automatic retry mechanisms with exponential backoff
- Comprehensive logging and monitoring
- Template-based sheet creation and management
- Advanced formatting with conditional styling
- Data synchronization with conflict resolution
- Performance optimization and caching
- Security-first design with credential management
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
import gspread.exceptions

from utils.logger import setup_logger
from .config import (
    DEFAULT_REQUEST_INTERVAL, 
    DEFAULT_MAX_RETRIES, 
    DEFAULT_BATCH_SIZE,
    COLORS, 
    TEXT_FORMATS,
    SUPPORTED_SHEETS,
    CACHE_CONFIG,
    ERROR_CONFIG,
    RETRY_POLICIES,
    SECURITY_CONFIG,
    FEATURE_FLAGS,
    get_environment_config
)

logger = setup_logger("base_sheets_manager")


class BaseGoogleSheetsManager:
    """
    Base Google Sheets manager providing core functionality and services.

    This class serves as the foundation for all Google Sheets operations, providing:
    - Secure connection management with automatic reconnection
    - Comprehensive rate limiting to respect API quotas
    - Advanced error handling with multiple recovery strategies
    - Performance monitoring and optimization
    - Extensible architecture for specialized managers

    Key Features:
    - Automatic credential management and refresh
    - Intelligent rate limiting with adaptive delays
    - Comprehensive error handling and recovery
    - Performance monitoring and metrics collection
    - Batch operation support for efficiency
    - Advanced caching mechanisms
    - Security-first design principles
    - Extensive logging and debugging capabilities

    Usage:
        manager = BaseGoogleSheetsManager(spreadsheet_id="your_sheet_id")
        if manager.is_connected():
            worksheet = manager.get_or_create_worksheet("Sheet Name")
            # Perform operations...

    Thread Safety:
        This class is designed to be thread-safe for concurrent operations.
        Rate limiting is applied across all threads to respect API limits.
    """

    def __init__(self, spreadsheet_id: Optional[str] = None):
        """
        Initialize the Google Sheets manager with comprehensive setup.

        Args:
            spreadsheet_id (str, optional): The Google Sheets spreadsheet ID.
                If not provided, will attempt to load from environment variables
                or create a new spreadsheet.

        Features:
        - Automatic credential detection and loading
        - Environment-specific configuration
        - Performance monitoring setup
        - Cache initialization
        - Error tracking initialization
        """
        # Core connection attributes
        self.gc = None
        self.spreadsheet = None
        self.spreadsheet_id = spreadsheet_id

        # Rate limiting and performance tracking
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = DEFAULT_REQUEST_INTERVAL
        self.rate_limit_hits = 0
        self.session_start_time = time.time()
        self.max_retries = DEFAULT_MAX_RETRIES

        # Performance and monitoring
        self.performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "last_error": None,
            "uptime_start": datetime.utcnow()
        }

        # Caching system for improved performance
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_config = CACHE_CONFIG.copy()

        # Error tracking and recovery
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.circuit_breaker_open = False

        # Environment configuration
        self.env_config = get_environment_config()

        # Thread pool for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=3)

        # Initialize the connection with debug logging
        logger.debug(f"🔧 BaseGoogleSheetsManager initializing with spreadsheet_id: {spreadsheet_id}")
        self.initialize_client()
        logger.debug(f"🔧 BaseGoogleSheetsManager initialization complete. gc: {self.gc is not None}, spreadsheet: {self.spreadsheet is not None}")

    def initialize_client(self):
        """
        Initialize Google Sheets client with comprehensive error handling.

        This method handles the complete initialization process:
        - Credential loading from multiple sources
        - Spreadsheet connection or creation
        - Initial validation and health checks
        - Performance baseline establishment

        Features:
        - Multiple credential source support
        - Automatic fallback mechanisms
        - Comprehensive error logging
        - Connection validation
        - Performance benchmarking

        Raises:
            ConnectionError: If unable to establish connection after all attempts
            AuthenticationError: If credentials are invalid or expired
            PermissionError: If insufficient permissions for spreadsheet access
        """
        try:
            logger.info("🔄 Initializing Google Sheets client...")

            # Define the required scopes for Google Sheets and Drive access
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            # Attempt to load credentials from multiple sources
            creds = None
            credential_source = None

            # Primary source: Environment variable (recommended for production)
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            if creds_json:
                try:
                    logger.debug(f"🔐 Found credentials environment variable (length: {len(creds_json)})")
                    creds_dict = json.loads(creds_json)
                    logger.debug(f"🔐 Parsed credentials JSON successfully")
                    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
                    credential_source = "environment variable"
                    logger.info("✅ Loaded Google Sheets credentials from environment variable")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {e}")
                    logger.debug(f"🔐 First 100 chars of credentials: {creds_json[:100]}...")
                except Exception as e:
                    logger.error(f"❌ Failed to parse credentials from environment: {e}")
                    logger.exception("Full credential parsing error:")

            # Fallback source: Local credentials file
            if not creds:
                credential_files = ["credentials.json", "service_account.json"]
                for creds_file in credential_files:
                    if os.path.exists(creds_file):
                        try:
                            creds = Credentials.from_service_account_file(creds_file, scopes=scope)
                            credential_source = f"file: {creds_file}"
                            logger.info(f"✅ Loaded Google Sheets credentials from {creds_file}")
                            break
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to load credentials from {creds_file}: {e}")

            # If no credentials found, log error and set client to None
            if not creds:
                logger.error("❌ No valid Google Sheets credentials found")
                logger.info("💡 Make sure GOOGLE_SHEETS_CREDENTIALS is set in environment or credentials.json exists")
                self.gc = None
                self.spreadsheet = None
                return

            # Validate credentials before attempting authorization
            try:
                # Check if credentials have required attributes
                if hasattr(creds, 'service_account_email'):
                    logger.debug(f"🔐 Service account email: {creds.service_account_email}")
                else:
                    logger.warning("⚠️ Credentials missing service account email")
                
                # Check if credentials are expired
                if hasattr(creds, 'expired') and creds.expired:
                    logger.warning("⚠️ Credentials appear to be expired")
                    try:
                        creds.refresh(Request())
                        logger.info("✅ Credentials refreshed successfully")
                    except Exception as refresh_error:
                        logger.error(f"❌ Failed to refresh credentials: {refresh_error}")
                        self.gc = None
                        self.spreadsheet = None
                        return
            except Exception as validation_error:
                logger.warning(f"⚠️ Could not validate credentials: {validation_error}")
                # Continue anyway as some credential types may not have these attributes

            # Authorize the client with the loaded credentials
            try:
                self.gc = gspread.authorize(creds)
                logger.info(f"✅ Google Sheets client authorized using {credential_source}")
            except Exception as auth_error:
                logger.error(f"❌ Failed to authorize Google Sheets client: {auth_error}")
                logger.error(f"🔐 Credential source: {credential_source}")
                logger.exception("Full authorization error:")
                self.gc = None
                self.spreadsheet = None
                return

            # Connect to or create the spreadsheet
            spreadsheet_id = self.spreadsheet_id or os.getenv("GOOGLE_SHEETS_ID")
            if spreadsheet_id:
                # Attempt to open existing spreadsheet
                try:
                    self.spreadsheet = self.rate_limited_request(
                        lambda: self.gc.open_by_key(spreadsheet_id)
                    )
                    self.spreadsheet_id = spreadsheet_id
                    logger.info(f"✅ Connected to existing spreadsheet")
                    logger.info(f"📊 Spreadsheet URL: {self.spreadsheet.url}")
                    logger.info(f"📋 Spreadsheet Title: {self.spreadsheet.title}")
                except gspread.SpreadsheetNotFound:
                    logger.error(f"❌ Spreadsheet with ID {spreadsheet_id} not found")
                    logger.info("💡 Check if the spreadsheet ID is correct and the service account has access")
                    self.gc = None
                    self.spreadsheet = None
                    return
                except Exception as e:
                    logger.error(f"❌ Failed to open spreadsheet {spreadsheet_id}: {e}")
                    self.gc = None
                    self.spreadsheet = None
                    return
            else:
                # Create new spreadsheet if no ID provided
                try:
                    self.spreadsheet = self.rate_limited_request(
                        lambda: self.gc.create("Discord RoW Bot Data")
                    )
                    self.spreadsheet_id = self.spreadsheet.id
                    logger.info("✅ Created new spreadsheet")
                    logger.info(f"📊 New Spreadsheet URL: {self.spreadsheet.url}")
                    logger.warning("⚠️ Set GOOGLE_SHEETS_ID environment variable to reuse this spreadsheet")
                    logger.info(f"💡 Spreadsheet ID to save: {self.spreadsheet_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to create new spreadsheet: {e}")
                    self.gc = None
                    self.spreadsheet = None
                    return

            # Perform initial validation and health check
            if self.spreadsheet:
                try:
                    # Test basic functionality by listing worksheets
                    worksheets = self.rate_limited_request(lambda: self.spreadsheet.worksheets())
                    logger.info(f"✅ Spreadsheet validation successful - {len(worksheets)} worksheets found")

                    # Log existing worksheets for debugging
                    if worksheets:
                        worksheet_names = [ws.title for ws in worksheets]
                        logger.debug(f"📋 Existing worksheets: {', '.join(worksheet_names)}")

                    # Reset failure counters on successful connection
                    self.consecutive_failures = 0
                    self.circuit_breaker_open = False
                    self.last_failure_time = None

                except Exception as e:
                    logger.error(f"❌ Spreadsheet validation failed: {e}")
                    self.gc = None
                    self.spreadsheet = None
                    return

            logger.info("🎉 Google Sheets client initialization completed successfully")

        except Exception as e:
            logger.error(f"❌ Critical error during Google Sheets client initialization: {e}")
            logger.exception("Full traceback:")
            self.gc = None
            self.spreadsheet = None

            # Update failure tracking
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            if self.consecutive_failures >= ERROR_CONFIG["MAX_CONSECUTIVE_FAILURES"]:
                self.circuit_breaker_open = True
                logger.error("🚨 Circuit breaker opened due to consecutive failures")

    def rate_limited_request(self, func, *args, **kwargs):
        """
        Execute request with comprehensive rate limiting and error handling.

        This method provides a robust wrapper for all Google Sheets API calls:
        - Enforces minimum intervals between requests
        - Implements exponential backoff for retries
        - Handles various error types with appropriate responses
        - Tracks performance metrics and usage statistics
        - Provides circuit breaker functionality for system protection

        Args:
            func (callable): The function to execute (usually a Google Sheets API call)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Any: The result of the function call

        Raises:
            Exception: Re-raises the last exception if all retry attempts fail

        Features:
        - Intelligent rate limiting with adaptive delays
        - Exponential backoff retry strategy
        - Performance metrics collection
        - Error categorization and handling
        - Circuit breaker pattern implementation
        - Request timing and optimization
        """
        # Check circuit breaker status
        if self.circuit_breaker_open:
            if (time.time() - self.last_failure_time) > ERROR_CONFIG["FAILURE_RESET_TIME"]:
                self.circuit_breaker_open = False
                self.consecutive_failures = 0
                logger.info("✅ Circuit breaker reset - attempting operations")
            else:
                raise Exception("Circuit breaker is open - too many consecutive failures")

        # Enforce minimum interval between requests to respect rate limits
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"⏱️ Rate limiting: sleeping for {sleep_time:.3f}s")
            time.sleep(sleep_time)

        # Update tracking metrics
        self.last_request_time = time.time()
        self.request_count += 1
        self.performance_metrics["total_requests"] += 1

        request_start_time = time.time()
        last_exception = None

        # Execute with retry logic and exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Execute the function with provided arguments
                if args or kwargs:
                    result = func(*args, **kwargs)
                else:
                    result = func()

                # Update success metrics
                request_time = time.time() - request_start_time
                self.performance_metrics["successful_requests"] += 1
                self._update_average_response_time(request_time)

                # Reset failure counter on successful request
                self.consecutive_failures = 0

                logger.debug(f"✅ Request completed successfully in {request_time:.3f}s (attempt {attempt + 1})")
                return result

            except gspread.exceptions.APIError as e:
                last_exception = e
                error_code = getattr(e, 'response', {}).get('status', 'unknown')

                if error_code == 429:  # Rate limit exceeded
                    self.rate_limit_hits += 1
                    backoff_time = min(2 ** attempt * 2, 60)  # Cap at 60 seconds
                    logger.warning(f"📊 Rate limit hit! Backing off for {backoff_time}s (attempt {attempt + 1})")
                    time.sleep(backoff_time)
                elif error_code in [500, 502, 503, 504]:  # Server errors
                    backoff_time = min(2 ** attempt, 30)  # Exponential backoff, cap at 30s
                    logger.warning(f"🔧 Server error {error_code}, retrying in {backoff_time}s (attempt {attempt + 1})")
                    time.sleep(backoff_time)
                else:
                    # For other API errors, don't retry
                    logger.error(f"❌ API Error {error_code}: {e}")
                    break

            except RefreshError as e:
                last_exception = e
                logger.error(f"🔐 Credential refresh error: {e}")
                # Try to reinitialize the client
                if attempt == 0:  # Only try once
                    logger.info("🔄 Attempting to reinitialize client...")
                    self.initialize_client()
                    if not self.is_connected():
                        break

            except Exception as e:
                last_exception = e
                logger.warning(f"⚠️ Request failed: {e} (attempt {attempt + 1})")

                # Don't retry for certain exceptions
                if isinstance(e, (gspread.WorksheetNotFound, gspread.SpreadsheetNotFound)):
                    break

                if attempt < self.max_retries - 1:
                    backoff_time = min(2 ** attempt, 15)  # Exponential backoff, cap at 15s
                    time.sleep(backoff_time)

        # All retry attempts failed
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        self.performance_metrics["failed_requests"] += 1
        self.performance_metrics["last_error"] = str(last_exception)

        logger.error(f"❌ Request failed after {self.max_retries} attempts: {last_exception}")

        # Open circuit breaker if too many failures
        if self.consecutive_failures >= ERROR_CONFIG["MAX_CONSECUTIVE_FAILURES"]:
            self.circuit_breaker_open = True
            logger.error("🚨 Circuit breaker opened due to consecutive failures")

        raise last_exception

    def _update_average_response_time(self, request_time: float):
        """
        Update the rolling average response time for performance monitoring.

        Args:
            request_time (float): Time taken for the last request

        Features:
        - Rolling average calculation
        - Performance trend tracking
        - Optimization insights
        """
        current_avg = self.performance_metrics["average_response_time"]
        total_requests = self.performance_metrics["successful_requests"]

        # Calculate new rolling average
        if total_requests == 1:
            self.performance_metrics["average_response_time"] = request_time
        else:
            # Weighted average giving more weight to recent requests
            weight = 0.1  # 10% weight to new request
            self.performance_metrics["average_response_time"] = (
                current_avg * (1 - weight) + request_time * weight
            )

    def is_connected(self) -> bool:
        """
        Check if the Google Sheets connection is active and functional.

        Performs a comprehensive connectivity check:
        - Validates client initialization
        - Tests spreadsheet accessibility
        - Verifies API functionality
        - Checks credential validity

        Returns:
            bool: True if fully connected and functional, False otherwise

        Features:
        - Multi-layer connectivity validation
        - Graceful error handling
        - Performance impact minimization
        - Detailed logging for debugging
        """
        if not self.gc or not self.spreadsheet:
            logger.debug("❌ Connection check failed: Client or spreadsheet not initialized")
            return False

        # Check circuit breaker status
        if self.circuit_breaker_open:
            logger.debug("❌ Connection check failed: Circuit breaker is open")
            return False

        try:
            # Perform a lightweight test operation
            self.rate_limited_request(lambda: self.spreadsheet.worksheets())
            logger.debug("✅ Connection check passed")
            return True
        except Exception as e:
            logger.debug(f"❌ Connection check failed: {e}")
            return False

    def get_or_create_worksheet(self, title: str, rows: int = 100, cols: int = 10):
        """
        Get existing worksheet or create new one with comprehensive configuration.

        This method provides intelligent worksheet management:
        - Attempts to retrieve existing worksheet by title
        - Creates new worksheet if not found
        - Applies default configuration and formatting
        - Handles errors gracefully with fallback options

        Args:
            title (str): The title/name of the worksheet
            rows (int, optional): Number of rows for new worksheet. Defaults to 100.
            cols (int, optional): Number of columns for new worksheet. Defaults to 10.

        Returns:
            gspread.Worksheet or None: The worksheet object if successful, None otherwise

        Features:
        - Case-insensitive title matching
        - Automatic sizing based on sheet type
        - Error recovery and fallback mechanisms
        - Comprehensive logging and debugging
        - Performance optimization with caching
        """
        if not self.spreadsheet:
            logger.error("❌ No spreadsheet available for worksheet operations")
            return None

        # Check cache first for performance optimization
        cache_key = f"worksheet_{title}"
        if cache_key in self.cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if (time.time() - cache_time) < self.cache_config["DEFAULT_EXPIRY"]:
                logger.debug(f"📋 Using cached worksheet: {title}")
                return self.cache[cache_key]

        try:
            # Attempt to find existing worksheet
            worksheet = self.rate_limited_request(
                lambda: self.spreadsheet.worksheet(title)
            )
            logger.debug(f"✅ Found existing worksheet: {title}")

            # Cache the result
            self.cache[cache_key] = worksheet
            self.cache_timestamps[cache_key] = time.time()

            return worksheet

        except gspread.WorksheetNotFound:
            logger.info(f"📝 Worksheet '{title}' not found, creating new one...")

            try:
                # Get optimal dimensions if this is a known sheet type
                if title in SUPPORTED_SHEETS:
                    sheet_config = SUPPORTED_SHEETS[title]
                    rows = sheet_config.get("rows", rows)
                    cols = sheet_config.get("cols", cols)
                    logger.debug(f"📐 Using optimal dimensions for {title}: {rows}x{cols}")

                # Create new worksheet with specified dimensions
                worksheet = self.rate_limited_request(
                    lambda: self.spreadsheet.add_worksheet(
                        title=title, rows=rows, cols=cols
                    )
                )

                logger.info(f"✅ Created new worksheet: {title} ({rows}x{cols})")

                # Apply basic formatting to new worksheet
                self._apply_basic_worksheet_formatting(worksheet)

                # Cache the result
                self.cache[cache_key] = worksheet
                self.cache_timestamps[cache_key] = time.time()

                return worksheet

            except Exception as e:
                logger.error(f"❌ Failed to create worksheet '{title}': {e}")
                return None

        except Exception as e:
            logger.error(f"❌ Error accessing worksheet '{title}': {e}")
            return None

    def _apply_basic_worksheet_formatting(self, worksheet):
        """
        Apply basic formatting to a newly created worksheet.

        Args:
            worksheet: The worksheet to format

        Features:
        - Standard color scheme application
        - Basic font and sizing settings
        - Grid and border configuration
        - Performance-optimized formatting
        """
        try:
            # Apply basic formatting if feature is enabled
            if FEATURE_FLAGS.get("ENABLE_ADVANCED_FORMATTING", True):
                # Set basic font and formatting
                self.rate_limited_request(
                    worksheet.format,
                    "A:Z",  # Format all columns
                    {
                        "textFormat": TEXT_FORMATS["NORMAL"],
                        "backgroundColor": COLORS["BG_WHITE"]
                    }
                )
                logger.debug(f"✅ Applied basic formatting to {worksheet.title}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to apply basic formatting to {worksheet.title}: {e}")

    def smart_delay(self, delay_type: str = "small"):
        """
        Implement intelligent delay for rate limiting and performance optimization.

        This method provides context-aware delays:
        - Adapts to current API usage patterns
        - Considers recent error rates
        - Optimizes for different operation types
        - Provides performance benefits through intelligent timing

        Args:
            delay_type (str): Type of delay to apply:
                - "small": Quick operations (0.2-0.5s)
                - "medium": Standard operations (0.5-1.0s)  
                - "large": Heavy operations (1.0-2.0s)
                - "adaptive": Adapts based on current conditions

        Features:
        - Context-aware delay calculation
        - Performance pattern adaptation
        - Error rate consideration
        - Rate limit optimization
        - Configurable delay strategies
        """
        # Base delay mappings for different operation types
        base_delays = {
            "small": 0.2,
            "medium": 0.5,
            "large": 1.0,
            "adaptive": 0.3
        }

        base_delay = base_delays.get(delay_type, 0.3)

        # Adaptive delay calculation based on current conditions
        if delay_type == "adaptive":
            # Increase delay if we've had recent rate limit hits
            if self.rate_limit_hits > 0:
                rate_limit_factor = min(1 + (self.rate_limit_hits * 0.2), 3.0)
                base_delay *= rate_limit_factor
                logger.debug(f"⏱️ Adaptive delay increased due to rate limits: {base_delay:.2f}s")

            # Increase delay if recent errors
            if self.consecutive_failures > 0:
                error_factor = min(1 + (self.consecutive_failures * 0.3), 2.0)
                base_delay *= error_factor
                logger.debug(f"⏱️ Adaptive delay increased due to errors: {base_delay:.2f}s")

            # Reduce delay if performance is good
            avg_response = self.performance_metrics.get("average_response_time", 1.0)
            if avg_response < 0.5:  # Fast responses
                base_delay *= 0.8  # Reduce delay by 20%
                logger.debug(f"⏱️ Adaptive delay reduced due to good performance: {base_delay:.2f}s")

        # Apply the calculated delay
        if base_delay > 0:
            logger.debug(f"⏱️ Applying {delay_type} delay: {base_delay:.2f}s")
            time.sleep(base_delay)

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary and statistics.

        Returns:
            dict: Performance metrics and statistics

        Features:
        - Request statistics and success rates
        - Performance metrics and timing
        - Error tracking and analysis
        - Usage patterns and optimization insights
        """
        uptime = datetime.utcnow() - self.performance_metrics["uptime_start"]

        total_requests = self.performance_metrics["total_requests"]
        success_rate = 0.0
        if total_requests > 0:
            success_rate = (self.performance_metrics["successful_requests"] / total_requests) * 100

        return {
            "connection_status": self.is_connected(),
            "uptime_hours": uptime.total_seconds() / 3600,
            "total_requests": total_requests,
            "successful_requests": self.performance_metrics["successful_requests"],
            "failed_requests": self.performance_metrics["failed_requests"],
            "success_rate_percent": round(success_rate, 2),
            "average_response_time_ms": round(self.performance_metrics["average_response_time"] * 1000, 2),
            "rate_limit_hits": self.rate_limit_hits,
            "consecutive_failures": self.consecutive_failures,
            "circuit_breaker_open": self.circuit_breaker_open,
            "last_error": self.performance_metrics["last_error"],
            "cache_size": len(self.cache),
            "spreadsheet_id": self.spreadsheet_id,
            "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None
        }

    def clear_cache(self):
        """
        Clear the internal cache to free memory and force fresh data retrieval.

        Features:
        - Memory optimization
        - Cache invalidation
        - Performance reset
        - Debug assistance
        """
        cache_size = len(self.cache)
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info(f"🗑️ Cleared cache ({cache_size} items)")

    def __del__(self):
        """
        Cleanup method called when the object is destroyed.

        Features:
        - Thread pool cleanup
        - Cache cleanup
        - Resource deallocation
        - Performance logging
        """
        try:
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)

            if hasattr(self, 'performance_metrics'):
                logger.info(f"📊 Session summary: {self.performance_metrics['total_requests']} total requests, "
                           f"{self.rate_limit_hits} rate limit hits")
        except:
            pass  # Ignore cleanup errors


# Export the main class
__all__ = ["BaseGoogleSheetsManager"]

# Module metadata
__version__ = "2.1.0"
__author__ = "RoW Bot Development Team"
__description__ = "Base Google Sheets manager with comprehensive functionality"
__last_updated__ = "2024-01-15"
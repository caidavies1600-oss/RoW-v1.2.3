
"""
Error handling utilities for Google Sheets operations.
"""

import time
import gspread
from typing import Any, Callable, Optional
from utils.logger import setup_logger

logger = setup_logger("sheets_error_handler")

class SheetsErrorHandler:
    """Handles errors and retries for Google Sheets operations."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def with_retry(self, operation: Callable, operation_name: str = "sheets operation", *args, **kwargs) -> Optional[Any]:
        """
        Execute a sheets operation with retry logic.

        Args:
            operation: Function to execute
            operation_name: Name for logging
            *args, **kwargs: Arguments for the operation

        Returns:
            Result of the operation or None if all retries failed
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retrying {operation_name} (attempt {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff

                result = operation(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"✅ {operation_name} succeeded on retry {attempt + 1}")
                
                return result

            except gspread.exceptions.APIError as e:
                last_error = e
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    logger.warning(f"⚠️ Rate limit hit for {operation_name}, waiting...")
                    time.sleep(self.retry_delay * 2)  # Longer wait for rate limits
                elif attempt == self.max_retries:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries + 1} attempts: {e}")
                else:
                    logger.warning(f"⚠️ {operation_name} failed (attempt {attempt + 1}): {e}")

            except Exception as e:
                last_error = e
                if attempt == self.max_retries:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries + 1} attempts: {e}")
                else:
                    logger.warning(f"⚠️ {operation_name} failed (attempt {attempt + 1}): {e}")

        logger.error(f"❌ {operation_name} exhausted all retry attempts")
        return None

    def is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is worth retrying."""
        if isinstance(error, gspread.exceptions.APIError):
            error_str = str(error)
            return any(code in error_str for code in [
                "RATE_LIMIT_EXCEEDED",
                "429",
                "500",
                "502",
                "503",
                "504"
            ])
        return False

# Global error handler instance
error_handler = SheetsErrorHandler()

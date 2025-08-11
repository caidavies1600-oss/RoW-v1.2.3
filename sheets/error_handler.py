
import gspread
from utils.logger import setup_logger
import time
from functools import wraps

logger = setup_logger("sheets_errors")

class SheetsErrorHandler:
    """Centralized error handling for Google Sheets operations."""
    
    @staticmethod
    def handle_rate_limit(func):
        """Decorator to handle Google Sheets API rate limiting."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = 3
            base_delay = 2
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except gspread.exceptions.APIError as e:
                    if "RATE_LIMIT_EXCEEDED" in str(e) or "Quota exceeded" in str(e):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"⚠️ Rate limit hit, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Rate limit exceeded after {max_retries} attempts")
                            return False
                    else:
                        logger.error(f"❌ Google Sheets API error: {e}")
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Unexpected error in {func.__name__}: {e}")
                    return False
                    
            return False
        return wrapper
    
    @staticmethod
    def validate_data(data, expected_type=dict):
        """Validate data before sending to sheets."""
        if data is None:
            logger.warning("⚠️ Attempting to sync None data to sheets")
            return False
            
        if not isinstance(data, expected_type):
            logger.warning(f"⚠️ Data type mismatch: expected {expected_type}, got {type(data)}")
            return False
            
        return True
    
    @staticmethod
    def log_sync_operation(operation_name, success, items_count=None, error=None):
        """Standardized logging for sync operations."""
        if success:
            count_msg = f" ({items_count} items)" if items_count is not None else ""
            logger.info(f"✅ {operation_name} sync completed{count_msg}")
        else:
            error_msg = f": {error}" if error else ""
            logger.error(f"❌ {operation_name} sync failed{error_msg}")
import gspread
import time
from functools import wraps
from utils.logger import setup_logger

logger = setup_logger("sheets_errors")

class SheetsErrorHandler:
    """Centralized error handling for Google Sheets operations."""
    
    @staticmethod
    def handle_rate_limit(func):
        """Decorator to handle Google Sheets API rate limiting."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = 3
            base_delay = 2
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except gspread.exceptions.APIError as e:
                    if "RATE_LIMIT_EXCEEDED" in str(e) or "Quota exceeded" in str(e):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"⚠️ Rate limit hit, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Rate limit exceeded after {max_retries} attempts")
                            return False
                    else:
                        logger.error(f"❌ Google Sheets API error: {e}")
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Unexpected error in {func.__name__}: {e}")
                    return False
                    
            return False
        return wrapper
    
    @staticmethod
    def validate_data(data, expected_type=dict):
        """Validate data before sending to sheets."""
        if data is None:
            logger.warning("⚠️ Attempting to sync None data to sheets")
            return False
            
        if not isinstance(data, expected_type):
            logger.warning(f"⚠️ Data type mismatch: expected {expected_type}, got {type(data)}")
            return False
            
        return True
    
    @staticmethod
    def log_sync_operation(operation_name, success, items_count=None, error=None):
        """Standardized logging for sync operations."""
        if success:
            count_msg = f" ({items_count} items)" if items_count is not None else ""
            logger.info(f"✅ {operation_name} sync completed{count_msg}")
        else:
            error_msg = f": {error}" if error else ""
            logger.error(f"❌ {operation_name} sync failed{error_msg}")

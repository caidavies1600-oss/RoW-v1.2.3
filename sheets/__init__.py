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

from .base_manager import RateLimitedSheetsManager

# Main export - this is what should be imported
class SheetsManager(RateLimitedSheetsManager):
    """Enhanced SheetsManager with all required methods."""
    pass


# Export the main class
__all__ = ["SheetsManager"]

# Module metadata
__version__ = "2.0.2"
__author__ = "RoW Bot Team"
__description__ = "Google Sheets integration with comprehensive features"
__requirements__ = ["gspread", "google-auth", "google-auth-oauthlib"]
__min_python_version__ = "3.8"
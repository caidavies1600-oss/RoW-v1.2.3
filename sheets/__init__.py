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


class SheetsManager(RateLimitedSheetsManager):
    """
    Complete Google Sheets Manager combining all functionality.

    Features:
    - Rate limited API access
    - Error handling and retries
    - Template creation and formatting
    - Data synchronization
    - Sheet formatting
    - Formula management

    Configuration:
    - Uses GOOGLE_SHEETS_CREDENTIALS from environment
    - Uses GOOGLE_SHEETS_ID for spreadsheet
    - Automatically creates required worksheets
    """

    # Rate limiting settings
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 1.5
    REQUEST_TIMEOUT = 30

    def __init__(self):
        """
        Initialize sheets manager with rate limiting and error handling.

        Establishes connection to Google Sheets API and
        verifies credentials and permissions.
        """
        super().__init__()

    async def full_sync_and_create_templates(self, bot, all_data, guild_id=None):
        """Enhanced full sync with all template creation and formatting."""
        if not self.is_connected():
            return {"success": False, "error": "Sheets not available"}

        try:
            # Create all templates with proper formatting
            success = self.create_all_templates(all_data)

            result = {
                "success": success,
                "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None,
                "templates_created": [
                    "Player Stats (with formulas and formatting)",
                    "Current Teams",
                    "Results History",
                    "Match Statistics",
                    "Alliance Tracking",
                ],
            }

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}


# For backward compatibility, export the main class
__all__ = ["SheetsManager"]

# Module metadata with descriptions
__version__ = "2.0.2"
__author__ = "RoW Bot Team"
__description__ = "Google Sheets integration with MRO conflict resolved"
__requirements__ = ["gspread", "google-auth", "google-auth-oauthlib"]
__min_python_version__ = "3.8"

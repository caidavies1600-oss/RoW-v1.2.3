"""
Redirect module for Google Sheets functionality.

This module redirects all sheets operations to the main sheets/ directory
to avoid duplication and conflicts.
"""

# Import everything from the main sheets directory
try:
    from sheets import SheetsManager
    from utils.logger import setup_logger

    logger = setup_logger("sheets_redirect")
    logger.info("✅ Redirecting to main sheets/ directory")

    # Re-export the main SheetsManager
    __all__ = ["SheetsManager"]

except ImportError as e:
    from utils.logger import setup_logger
    logger = setup_logger("sheets_redirect")
    logger.error(f"❌ Failed to import from sheets/: {e}")

    # Fallback dummy class
    class SheetsManager:
        def __init__(self, *args, **kwargs):
            self.spreadsheet = None

        def is_connected(self):
            return False

        async def scan_and_sync_all_members(self, *args, **kwargs):
            return {"success": False, "error": "Sheets not available"}

        async def sync_current_teams(self, *args, **kwargs):
            return False

        async def sync_events_history(self, *args, **kwargs):
            return False

        async def sync_blocked_users(self, *args, **kwargs):
            return False

        async def sync_results_history(self, *args, **kwargs):
            return False

        def create_all_templates(self, *args, **kwargs):
            return False

        def get_spreadsheet_url(self):
            return ""

        async def sync_data(self, *args, **kwargs):
            return False
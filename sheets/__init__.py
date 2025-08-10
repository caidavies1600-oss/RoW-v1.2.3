
"""
Google Sheets Integration Module for Discord RoW Bot.
Provides both basic and enhanced sheets functionality.
"""

from .base_manager import RateLimitedSheetsManager

# Create a comprehensive sheets manager that combines all functionality
class SheetsManager(RateLimitedSheetsManager):
    """
    Complete Google Sheets Manager that combines:
    - Rate limiting and error handling (RateLimitedSheetsManager)
    - Template creation with formatting
    - Data synchronization
    """
    
    def __init__(self):
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
                    "Alliance Tracking"
                ]
            }
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# For backward compatibility, export the main class
__all__ = ['SheetsManager']

# Version and module info
__version__ = "2.0.2"
__author__ = "RoW Bot Team"
__description__ = "Google Sheets integration with MRO conflict resolved"

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

    async def scan_and_sync_all_members(self, bot):
        """
        Scan all Discord members and sync to Google Sheets.

        Args:
            bot: Discord bot instance

        Returns:
            dict: Sync results with success status and member count
        """
        try:
            if not self.is_connected():
                return {"success": False, "error": "Not connected to Google Sheets"}

            from utils.logger import setup_logger
            logger = setup_logger("sheets_sync")
            logger.info(" Syncing Discord members to Google Sheets...")

            # Get all members from all guilds
            all_members = []
            for guild in bot.guilds:
                for member in guild.members:
                    if not member.bot:  # Exclude bots
                        all_members.append({
                            "id": str(member.id),
                            "username": member.name,
                            "display_name": member.display_name,
                            "guild": guild.name,
                            "joined_at": member.joined_at.isoformat() if member.joined_at else None
                        })

            # Sync to sheets (using the inherited method from base_manager)
            success = await self._sync_members_to_sheets(all_members)

            if success:
                logger.info(f"✅ Successfully synced {len(all_members)} members to Google Sheets")
                return {"success": True, "member_count": len(all_members)}
            else:
                logger.error("❌ Failed to sync members to Google Sheets")
                return {"success": False, "error": "Sync operation failed"}

        except Exception as e:
            from utils.logger import setup_logger
            logger = setup_logger("sheets_sync")
            logger.error(f"❌ Error in scan_and_sync_all_members: {e}")
            return {"success": False, "error": str(e)}


# Export the main class
__all__ = ["SheetsManager"]

# Module metadata
__version__ = "2.0.2"
__author__ = "RoW Bot Team"
__description__ = "Google Sheets integration with comprehensive features"
__requirements__ = ["gspread", "google-auth", "google-auth-oauthlib"]
__min_python_version__ = "3.8"
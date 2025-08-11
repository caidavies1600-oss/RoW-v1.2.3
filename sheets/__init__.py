
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

    async def scan_and_sync_all_members(self, bot, guild_id=None):
        """
        Scan all Discord members and sync to Google Sheets.

        Args:
            bot: Discord bot instance
            guild_id: Optional guild ID to scan (if None, scans all guilds)

        Returns:
            dict: Sync results with success status and member count
        """
        try:
            if not self.is_connected():
                return {"success": False, "error": "Not connected to Google Sheets"}

            from utils.logger import setup_logger
            logger = setup_logger("sheets_sync")
            logger.info("🔄 Syncing Discord members to Google Sheets...")

            # Get members from specified guild or all guilds
            all_members = []
            if guild_id:
                guild = bot.get_guild(guild_id)
                if not guild:
                    return {"success": False, "error": f"Guild {guild_id} not found"}
                guilds_to_scan = [guild]
            else:
                guilds_to_scan = bot.guilds

            for guild in guilds_to_scan:
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

# Features provided by this module
__features__ = [
    "Rate-limited API access",
    "Comprehensive error handling",
    "Template creation and formatting",
    "Data synchronization",
    "Batch operations",
    "Usage tracking",
    "Auto-reconnection"
]

# Configuration constants
DEFAULT_REQUEST_INTERVAL = 0.1  # 100ms between requests
DEFAULT_MAX_RETRIES = 5
DEFAULT_BATCH_SIZE = 50

# Supported sheet types
SUPPORTED_SHEETS = [
    "Current Teams",
    "Events History", 
    "Player Stats",
    "Results History",
    "Blocked Users",
    "Discord Members",
    "Match Statistics",
    "Alliance Tracking",
    "Error Summary",
    "Dashboard Summary"
]

# Version history
__changelog__ = {
    "2.0.2": "Added scan_and_sync_all_members method",
    "2.0.1": "Enhanced error handling and logging",
    "2.0.0": "Complete rewrite with rate limiting and templates",
    "1.0.0": "Initial release"
}

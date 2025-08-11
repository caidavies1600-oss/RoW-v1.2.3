
import asyncio
import time
import random
from typing import Any, Optional, Dict, List
from utils.logger import setup_logger
from contextlib import asynccontextmanager
from datetime import datetime

logger = setup_logger("sheets_manager")

try:
    import gspread
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

class SheetsManager:
    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.client = None
        self.spreadsheet = None
        self.last_request = 0
        self.min_request_interval = 1.1  # Seconds between requests
        self.max_retries = 3
        self.spreadsheet_id = spreadsheet_id
        self._initialize(spreadsheet_id)

    def _initialize(self, spreadsheet_id: Optional[str]):
        try:
            if GSPREAD_AVAILABLE:
                self.client = gspread.service_account()
                if spreadsheet_id:
                    self.spreadsheet = self.client.open_by_key(spreadsheet_id)
                else:
                    # Try to get from environment
                    import os
                    sheets_id = os.getenv("GOOGLE_SHEETS_ID")
                    if sheets_id:
                        self.spreadsheet = self.client.open_by_key(sheets_id)
                        self.spreadsheet_id = sheets_id
                    else:
                        logger.warning("No spreadsheet ID provided and GOOGLE_SHEETS_ID not found")
            else:
                logger.warning("gspread not available, sheets functionality disabled")
        except Exception as e:
            logger.error(f"Failed to initialize sheets manager: {e}")
            self.client = None
            self.spreadsheet = None

    def is_connected(self) -> bool:
        """Check if sheets client is properly connected."""
        return self.client is not None and GSPREAD_AVAILABLE and self.spreadsheet is not None

    async def _rate_limited_request(self, func):
        """Execute request with rate limiting and retries."""
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                now = time.time()
                if now - self.last_request < self.min_request_interval:
                    await asyncio.sleep(self.min_request_interval)
                
                result = await asyncio.to_thread(func)
                self.last_request = time.time()
                return result

            except Exception as e:
                if "gspread" in str(type(e)) and hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                    wait_time = (2 ** attempt) + random.random()
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                    
                if attempt == self.max_retries - 1:
                    raise
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)

    def _get_or_create_sheet(self, name: str):
        """Get existing worksheet or create new one."""
        if not self.spreadsheet:
            raise ValueError("No spreadsheet available")
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(name, 1000, 26)

    async def scan_and_sync_all_members(self, bot, guild_id: int) -> Dict[str, Any]:
        """Scan Discord guild members and sync to Google Sheets."""
        if not self.is_connected():
            return {"success": False, "error": "Sheets not available"}

        try:
            guild = bot.get_guild(guild_id)
            if not guild:
                return {"success": False, "error": f"Guild {guild_id} not found"}

            def _sync_members():
                worksheet = self._get_or_create_sheet("Discord Members")
                
                # Clear existing data and add headers
                worksheet.clear()
                headers = ["User ID", "Username", "Display Name", "Joined At", "Is Bot", "Roles", "Last Updated"]
                worksheet.append_row(headers)
                
                members_data = []
                new_count = 0
                updated_count = 0
                
                for member in guild.members:
                    roles = ", ".join([role.name for role in member.roles if role.name != "@everyone"])
                    joined_str = member.joined_at.isoformat() if member.joined_at else "Unknown"
                    
                    row = [
                        str(member.id),
                        member.name,
                        member.display_name,
                        joined_str,
                        "Yes" if member.bot else "No",
                        roles,
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    ]
                    members_data.append(row)
                    
                    if not member.bot:
                        new_count += 1
                
                # Add all member data in batches
                if members_data:
                    # Split into batches of 100 to avoid API limits
                    batch_size = 100
                    for i in range(0, len(members_data), batch_size):
                        batch = members_data[i:i + batch_size]
                        worksheet.append_rows(batch)
                        time.sleep(1)  # Rate limiting
                
                return {
                    "success": True,
                    "guild_name": guild.name,
                    "total_discord_members": len([m for m in guild.members if not m.bot]),
                    "new_members_added": new_count,
                    "existing_members_updated": updated_count
                }

            result = await self._rate_limited_request(_sync_members)
            logger.info(f"✅ Synced {result['total_discord_members']} members to sheets")
            return result

        except Exception as e:
            logger.error(f"Failed to sync members: {e}")
            return {"success": False, "error": str(e)}

    async def sync_current_teams(self, data: Dict[str, Any]) -> bool:
        """Sync current teams to Google Sheets."""
        if not self.is_connected():
            return False
            
        try:
            def _update():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                
                worksheet = self._get_or_create_sheet("Current Teams")
                worksheet.clear()
                
                headers = ["Team", "Players", "Count", "Last Updated"]
                worksheet.append_row(headers)
                
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                for team, players in data.items():
                    player_list = ", ".join(str(p) for p in players) if players else "No signups"
                    worksheet.append_row([
                        team.replace("_", " ").title(),
                        player_list,
                        len(players),
                        timestamp
                    ])
                
            await self._rate_limited_request(_update)
            logger.info("✅ Synced current teams")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync current teams: {e}")
            return False

    async def sync_events_history(self, data: List[Dict]) -> bool:
        """Sync events history to Google Sheets."""
        if not self.is_connected():
            return False
            
        try:
            def _update():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                
                worksheet = self._get_or_create_sheet("Events History")
                worksheet.clear()
                
                headers = ["Timestamp", "Main Team", "Team 2", "Team 3", "Total Players"]
                worksheet.append_row(headers)
                
                for entry in data[-50:]:  # Only sync last 50 entries
                    timestamp = entry.get("timestamp", "")
                    teams = entry.get("teams", {})
                    
                    main_count = len(teams.get("main_team", []))
                    team2_count = len(teams.get("team_2", []))
                    team3_count = len(teams.get("team_3", []))
                    total = main_count + team2_count + team3_count
                    
                    worksheet.append_row([
                        timestamp.split("T")[0] if "T" in timestamp else timestamp,
                        main_count,
                        team2_count,
                        team3_count,
                        total
                    ])
                
            await self._rate_limited_request(_update)
            logger.info("✅ Synced events history")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync events history: {e}")
            return False

    async def sync_blocked_users(self, data: Dict[str, Any]) -> bool:
        """Sync blocked users to Google Sheets."""
        if not self.is_connected():
            return False
            
        try:
            def _update():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                
                worksheet = self._get_or_create_sheet("Blocked Users")
                worksheet.clear()
                
                headers = ["User ID", "Blocked By", "Blocked At", "Duration Days", "Status"]
                worksheet.append_row(headers)
                
                for user_id, info in data.items():
                    worksheet.append_row([
                        user_id,
                        info.get("blocked_by", "Unknown"),
                        info.get("blocked_at", ""),
                        info.get("ban_duration_days", 0),
                        "Active"
                    ])
                
            await self._rate_limited_request(_update)
            logger.info("✅ Synced blocked users")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync blocked users: {e}")
            return False

    async def sync_results_history(self, data: Dict[str, Any]) -> bool:
        """Sync results history to Google Sheets."""
        if not self.is_connected():
            return False
            
        try:
            def _update():
                if not self.spreadsheet:
                    raise ValueError("Spreadsheet not initialized")
                
                worksheet = self._get_or_create_sheet("Results History")
                worksheet.clear()
                
                headers = ["Date", "Result", "Team", "Notes"]
                worksheet.append_row(headers)
                
                for entry in data.get("history", [])[-50:]:  # Last 50 results
                    worksheet.append_row([
                        entry.get("timestamp", "").split("T")[0],
                        entry.get("result", ""),
                        entry.get("team", ""),
                        entry.get("notes", "")
                    ])
                
            await self._rate_limited_request(_update)
            logger.info("✅ Synced results history")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync results history: {e}")
            return False

    def create_all_templates(self, data: Dict[str, Any]) -> bool:
        """Create all necessary worksheet templates."""
        if not self.is_connected():
            return False

        try:
            templates = [
                ("Current Teams", lambda: self._create_teams_template()),
                ("Events History", lambda: self._create_history_template()),
                ("Blocked Users", lambda: self._create_blocked_template()),
                ("Results History", lambda: self._create_results_template()),
                ("Discord Members", lambda: self._create_members_template())
            ]

            success_count = 0
            for name, create_func in templates:
                try:
                    if create_func():
                        success_count += 1
                        logger.info(f"✅ Created template: {name}")
                except Exception as e:
                    logger.error(f"Failed to create {name} template: {e}")

            return success_count >= len(templates) // 2

        except Exception as e:
            logger.error(f"Failed to create templates: {e}")
            return False

    def _create_teams_template(self) -> bool:
        """Create Current Teams sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Current Teams")
            headers = ["Team", "Players", "Count", "Last Updated"]
            worksheet.clear()
            worksheet.append_row(headers)
            return True
        except Exception as e:
            logger.error(f"Failed to create teams template: {e}")
            return False

    def _create_history_template(self) -> bool:
        """Create Events History sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Events History")
            headers = ["Timestamp", "Main Team", "Team 2", "Team 3", "Total Players"]
            worksheet.clear()
            worksheet.append_row(headers)
            return True
        except Exception as e:
            logger.error(f"Failed to create history template: {e}")
            return False

    def _create_blocked_template(self) -> bool:
        """Create Blocked Users sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Blocked Users")
            headers = ["User ID", "Blocked By", "Blocked At", "Duration Days", "Status"]
            worksheet.clear()
            worksheet.append_row(headers)
            return True
        except Exception as e:
            logger.error(f"Failed to create blocked template: {e}")
            return False

    def _create_results_template(self) -> bool:
        """Create Results History sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Results History")
            headers = ["Date", "Result", "Team", "Notes"]
            worksheet.clear()
            worksheet.append_row(headers)
            return True
        except Exception as e:
            logger.error(f"Failed to create results template: {e}")
            return False

    def _create_members_template(self) -> bool:
        """Create Discord Members sheet template."""
        try:
            worksheet = self._get_or_create_sheet("Discord Members")
            headers = ["User ID", "Username", "Display Name", "Joined At", "Is Bot", "Roles", "Last Updated"]
            worksheet.clear()
            worksheet.append_row(headers)
            return True
        except Exception as e:
            logger.error(f"Failed to create members template: {e}")
            return False

    def get_spreadsheet_url(self) -> str:
        """Get the URL of the managed spreadsheet."""
        if self.spreadsheet and hasattr(self.spreadsheet, 'url'):
            return self.spreadsheet.url
        elif self.spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return ""

    async def sync_data(self, filepath: str, data: Any) -> bool:
        """Smart sync based on file type."""
        try:
            import os
            filename = os.path.basename(filepath)
            
            if filename == "events.json":
                return await self.sync_current_teams(data)
            elif filename == "events_history.json":
                return await self.sync_events_history(data)
            elif filename == "blocked_users.json":
                return await self.sync_blocked_users(data)
            elif filename == "event_results.json":
                return await self.sync_results_history(data)
            
            return True
        except Exception as e:
            logger.error(f"Sheet sync failed for {filepath}: {e}")
            return False

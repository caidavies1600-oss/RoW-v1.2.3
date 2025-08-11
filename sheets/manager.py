
from .data_sync import DataSync
from .error_handler import SheetsErrorHandler
from utils.logger import setup_logger

logger = setup_logger("sheets_manager")

class SheetsManager(DataSync):
    """
    Main Google Sheets Manager - Clean Architecture
    
    Inherits from DataSync which provides:
    - BaseSheetsConnection (authentication & connection)
    - TemplateCreator (template creation)
    - Data sync operations (sync_player_stats, sync_results_history, etc.)
    """
    
    def __init__(self):
        """Initialize the sheets manager with all capabilities."""
        super().__init__()
        logger.info("🔧 SheetsManager initialized with clean architecture")
    
    async def scan_and_sync_all_members(self, bot, guild_id: int = None):
        """Scan Discord members and sync to Google Sheets with batch processing."""
        if not self.is_connected():
            return {"success": False, "error": "Sheets not initialized"}

        try:
            # Get guild
            guild = bot.get_guild(guild_id) if guild_id else bot.guilds[0]
            if not guild:
                return {"success": False, "error": "No guild found"}

            logger.info(f"🔍 Syncing members from {guild.name}")

            # Cache members
            if not guild.chunked:
                await guild.chunk(cache=True)

            # Get existing data and IGN map
            existing_players = self._load_existing_players_from_sheets()
            ign_map = self._load_ign_map()

            # Process members
            new_members, updated_members, total = self._process_members(
                guild, existing_players, ign_map
            )

            # Sync to sheets
            sync_success = self._sync_members_to_sheets(new_members, updated_members)

            return {
                "success": True,
                "guild_name": guild.name,
                "total_discord_members": total,
                "new_members_added": len(new_members),
                "existing_members_updated": len(updated_members),
                "sheets_sync_success": sync_success
            }

        except Exception as e:
            logger.error(f"Member sync failed: {e}")
            return {"success": False, "error": str(e)}

    async def full_sync_and_create_templates(self, bot, all_data: dict, guild_id: int = None):
        """Complete sync: members + templates."""
        if not self.is_connected():
            return {"success": False, "error": "Sheets not initialized"}

        try:
            # Step 1: Sync members
            member_result = await self.scan_and_sync_all_members(bot, guild_id)
            if not member_result["success"]:
                return {"success": False, "error": f"Member sync failed: {member_result.get('error')}"}

            # Step 2: Create templates
            templates_created = self.create_all_templates(all_data)

            return {
                "success": True,
                "member_sync": member_result,
                "templates_created": templates_created,
                "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None
            }

        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            return {"success": False, "error": str(e)}

    def _load_existing_players_from_sheets(self):
        """Load existing players from sheets."""
        try:
            worksheet = self.spreadsheet.worksheet("Player Stats")
            rows = worksheet.get_all_records()
            return {str(row.get("User ID", "")): row for row in rows if row.get("User ID")}
        except:
            return {}

    def _load_ign_map(self):
        """Load IGN mappings from file."""
        try:
            import json
            with open("data/ign_map.json", "r") as f:
                return json.load(f)
        except:
            return {}

    def _process_members(self, guild, existing_players, ign_map):
        """Process Discord members and determine changes needed."""
        from config.constants import MAIN_TEAM_ROLE_ID, ROW_NOTIFICATION_ROLE_ID

        new_members = []
        updated_members = []
        total_members = 0

        for member in guild.members:
            if member.bot:
                continue

            # Filter: Only sync members with ROW_NOTIFICATION_ROLE_ID to avoid API limits
            has_row_role = any(role.id == ROW_NOTIFICATION_ROLE_ID for role in member.roles)
            if not has_row_role:
                continue

            total_members += 1
            user_id = str(member.id)
            display_name = member.display_name
            ign = ign_map.get(user_id, display_name)

            try:
                has_main_role = any(role.id == MAIN_TEAM_ROLE_ID for role in member.roles)
            except:
                has_main_role = False

            if user_id not in existing_players:
                # New member
                new_members.append({
                    "user_id": user_id,
                    "name": ign,
                    "display_name": display_name,
                    "has_main_team_role": has_main_role,
                    "main_wins": 0, "main_losses": 0,
                    "team2_wins": 0, "team2_losses": 0,
                    "team3_wins": 0, "team3_losses": 0,
                    "absents": 0, "blocked": "No", "power_rating": 0,
                    "cavalry": "No", "mages": "No", "archers": "No",
                    "infantry": "No", "whale": "No"
                })
            else:
                # Check if update needed (including IGN changes)
                existing = existing_players[user_id]
                existing_ign = existing.get("Name", "")
                if (existing.get("Display Name") != display_name or
                    (existing.get("Main Team Role") == "Yes") != has_main_role or
                    existing_ign != ign):
                    updated_members.append({
                        "user_id": user_id,
                        "display_name": display_name,
                        "has_main_team_role": has_main_role,
                        "ign": ign
                    })

        logger.info(f"📊 Filtered {total_members} members with ROW role from {len(guild.members)} total guild members")
        return new_members, updated_members, total_members

    @SheetsErrorHandler.handle_rate_limit
    def _sync_members_to_sheets(self, new_members, updated_members):
        """Sync member data to Google Sheets with rate limiting."""
        if not self.is_connected():
            return False

        try:
            from .config import SHEET_CONFIGS
            config = SHEET_CONFIGS["Player Stats"]
            worksheet = self.get_or_create_worksheet("Player Stats", config["rows"], config["cols"])
            
            if not worksheet:
                return False

            # Add new members
            if new_members:
                logger.info(f"📥 Adding {len(new_members)} new members...")
                
                # Ensure headers exist
                try:
                    existing_data = worksheet.get_all_values()
                    if not existing_data or len(existing_data) == 0:
                        worksheet.append_row(config["headers"])
                except:
                    worksheet.append_row(config["headers"])

                for i, member in enumerate(new_members):
                    # Rate limiting: pause every 10 additions
                    if i > 0 and i % 10 == 0:
                        logger.info(f"Added {i} members, pausing 3s for rate limit...")
                        import time
                        time.sleep(3)

                    row_data = [
                        member["user_id"],
                        member["name"],
                        member["display_name"],
                        "Yes" if member["has_main_team_role"] else "No",
                        member["main_wins"], member["main_losses"],
                        member["team2_wins"], member["team2_losses"],
                        member["team3_wins"], member["team3_losses"],
                        member["main_wins"] + member["team2_wins"] + member["team3_wins"],  # Total wins
                        member["main_losses"] + member["team2_losses"] + member["team3_losses"],  # Total losses
                        member["absents"],
                        member["blocked"],
                        member["power_rating"],
                        member["cavalry"], member["mages"], member["archers"],
                        member["infantry"], member["whale"]
                    ]
                    worksheet.append_row(row_data)

            # Update existing members
            if updated_members:
                logger.info(f"🔄 Updating {len(updated_members)} existing members...")
                all_data = worksheet.get_all_records()

                for i, updated in enumerate(updated_members):
                    # Rate limiting: pause every 5 updates
                    if i > 0 and i % 5 == 0:
                        logger.info(f"Updated {i} members, pausing 2s...")
                        import time
                        time.sleep(2)

                    # Find the row to update
                    for row_idx, row_data in enumerate(all_data):
                        if str(row_data.get("User ID", "")) == updated["user_id"]:
                            row_num = row_idx + 2  # +2 because sheets are 1-indexed and we have headers
                            
                            # Update specific cells
                            worksheet.update_cell(row_num, 2, updated.get("ign", updated["display_name"]))  # Name
                            worksheet.update_cell(row_num, 3, updated["display_name"])  # Display Name
                            worksheet.update_cell(row_num, 4, "Yes" if updated["has_main_team_role"] else "No")  # Main Team Role
                            break

            logger.info(f"✅ Member sync complete: {len(new_members)} new, {len(updated_members)} updated")
            return True

        except Exception as e:
            logger.error(f"❌ Member sync failed: {e}")
            return False

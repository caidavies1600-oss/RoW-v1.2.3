
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("sheets_manager")

class SheetsManager:
    """Google Sheets integration for Discord bot - streamlined version."""

    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.initialize_client()

    def initialize_client(self):
        """Initialize Google Sheets client."""
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            else:
                creds = Credentials.from_service_account_file('credentials.json', scopes=scope)

            self.gc = gspread.authorize(creds)

            spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
            if spreadsheet_id:
                self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            else:
                self.spreadsheet = self.gc.create("Discord RoW Bot Data")
                logger.info(f"Created new spreadsheet: {self.spreadsheet.url}")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            self.gc = None
            self.spreadsheet = None

    async def scan_and_sync_all_members(self, bot, guild_id: int = None):
        """Scan Discord members and sync to Google Sheets."""
        if not self.spreadsheet:
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
            with open("data/ign_map.json", "r") as f:
                return json.load(f)
        except:
            return {}

    def _process_members(self, guild, existing_players, ign_map):
        """Process Discord members and determine changes needed."""
        from config.constants import MAIN_TEAM_ROLE_ID

        new_members = []
        updated_members = []
        total_members = 0

        for member in guild.members:
            if member.bot:
                continue

            total_members += 1
            user_id = str(member.id)
            display_name = member.display_name
            ign = ign_map.get(user_id, display_name)
            has_main_role = any(role.id == MAIN_TEAM_ROLE_ID for role in member.roles)

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
                # Check if update needed
                existing = existing_players[user_id]
                if (existing.get("Display Name") != display_name or 
                    (existing.get("Main Team Role") == "Yes") != has_main_role):
                    updated_members.append({
                        "user_id": user_id,
                        "display_name": display_name,
                        "has_main_team_role": has_main_role
                    })

        return new_members, updated_members, total_members

    def _sync_members_to_sheets(self, new_members, updated_members):
        """Sync member data to Google Sheets."""
        try:
            worksheet = self._get_or_create_player_sheet()

            # Add new members
            for member in new_members:
                row = [
                    member["user_id"], member["name"], member["display_name"],
                    "Yes" if member["has_main_team_role"] else "No",
                    member["main_wins"], member["main_losses"],
                    member["team2_wins"], member["team2_losses"],
                    member["team3_wins"], member["team3_losses"],
                    member["main_wins"] + member["team2_wins"] + member["team3_wins"],
                    member["main_losses"] + member["team2_losses"] + member["team3_losses"],
                    member["absents"], member["blocked"], member["power_rating"],
                    member["cavalry"], member["mages"], member["archers"],
                    member["infantry"], member["whale"],
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                ]
                worksheet.append_row(row)

            # Update existing members
            if updated_members:
                all_data = worksheet.get_all_records()
                for i, row_data in enumerate(all_data):
                    user_id = str(row_data.get("User ID", ""))
                    for updated in updated_members:
                        if updated["user_id"] == user_id:
                            row_num = i + 2
                            worksheet.update_cell(row_num, 3, updated["display_name"])
                            worksheet.update_cell(row_num, 4, "Yes" if updated["has_main_team_role"] else "No")
                            worksheet.update_cell(row_num, 21, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
                            break

            logger.info(f"✅ Synced {len(new_members)} new, {len(updated_members)} updated")
            return True

        except Exception as e:
            logger.error(f"Failed to sync to sheets: {e}")
            return False

    def _get_or_create_player_sheet(self):
        """Get or create Player Stats worksheet."""
        try:
            return self.spreadsheet.worksheet("Player Stats")
        except:
            worksheet = self.spreadsheet.add_worksheet(title="Player Stats", rows="500", cols="25")
            headers = [
                "User ID", "Name", "Display Name", "Main Team Role",
                "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
                "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses",
                "Absents", "Blocked", "Power Rating", "Cavalry", "Mages",
                "Archers", "Infantry", "Whale Status", "Last Updated"
            ]
            worksheet.append_row(headers)
            return worksheet

    async def full_sync_and_create_templates(self, bot, all_data: dict, guild_id: int = None):
        """Complete sync: members + templates."""
        if not self.spreadsheet:
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

    def sync_current_teams(self, events_data):
        """Sync current team signups to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            try:
                worksheet = self.spreadsheet.worksheet("Current Teams")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Current Teams", rows="10", cols="5")

            worksheet.clear()
            headers = ["Timestamp", "Team", "Player Count", "Players", "Status"]
            worksheet.append_row(headers)

            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            team_mapping = {"main_team": "Main Team", "team_2": "Team 2", "team_3": "Team 3"}

            for team_key, players in events_data.items():
                team_name = team_mapping.get(team_key, team_key)
                player_list = ", ".join(str(p) for p in players) if players else ""
                row = [timestamp, team_name, len(players), player_list, "Active"]
                worksheet.append_row(row)

            logger.info("✅ Synced current teams to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync current teams: {e}")
            return False

    def create_all_templates(self, all_data):
        """Create all sheet templates."""
        if not self.spreadsheet:
            return False

        try:
            success_count = 0
            templates = [
                ("Current Teams", lambda: self.sync_current_teams(all_data.get("events", {}))),
                ("Player Stats", lambda: self.sync_player_stats(all_data.get("player_stats", {}))),
                ("Results History", lambda: self.sync_results_history(all_data.get("results", {}))),
                ("Dashboard", self.create_dashboard),
            ]

            for name, func in templates:
                try:
                    if func():
                        success_count += 1
                        logger.info(f"✅ Created {name}")
                except Exception as e:
                    logger.error(f"❌ Error creating {name}: {e}")

            return success_count >= len(templates) // 2

        except Exception as e:
            logger.error(f"Template creation failed: {e}")
            return False

    def sync_results_history(self, results_data):
        """Sync results history to sheets."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Results History", rows="200", cols="7")

            worksheet.clear()
            headers = ["Date", "Team", "Result", "Players", "Recorded By", "Total Wins", "Total Losses"]
            worksheet.append_row(headers)

            for entry in results_data.get("history", [])[-50:]:  # Last 50 only
                date = entry.get("date", entry.get("timestamp", "Unknown"))
                if "T" in str(date):
                    try:
                        date = datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                worksheet.append_row([
                    date,
                    entry.get("team", "Unknown").replace("_", " ").title(),
                    entry.get("result", "Unknown").capitalize(),
                    ", ".join(entry.get("players", [])),
                    entry.get("by", entry.get("recorded_by", "Unknown")),
                    results_data.get("total_wins", 0),
                    results_data.get("total_losses", 0)
                ])

            return True
        except:
            return False

    def sync_player_stats(self, player_stats):
        """Create player stats template."""
        return True  # Already handled by member sync

    def create_dashboard(self):
        """Create simple dashboard."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Dashboard")
                worksheet.clear()
            except:
                worksheet = self.spreadsheet.add_worksheet(title="Dashboard", rows="20", cols="5")

            worksheet.update('A1', 'RoW Bot Dashboard')
            worksheet.update('A3', 'Team Performance Summary')
            worksheet.update('A5', 'Recent Activity')

            return True
        except:
            return False

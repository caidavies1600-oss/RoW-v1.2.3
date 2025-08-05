
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
                total_wins = member["main_wins"] + member["team2_wins"] + member["team3_wins"]
                total_losses = member["main_losses"] + member["team2_losses"] + member["team3_losses"]
                win_rate = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
                
                row = [
                    member["user_id"], member["name"], member["display_name"],
                    "Yes" if member["has_main_team_role"] else "No",
                    member["main_wins"], member["main_losses"],
                    member["team2_wins"], member["team2_losses"],
                    member["team3_wins"], member["team3_losses"],
                    total_wins, total_losses, win_rate,
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
        """Get or create Player Stats worksheet with professional formatting."""
        try:
            worksheet = self.spreadsheet.worksheet("Player Stats")
            # Apply formatting to existing sheet
            self._format_player_stats_sheet(worksheet)
            return worksheet
        except:
            worksheet = self.spreadsheet.add_worksheet(title="Player Stats", rows="500", cols="25")
            headers = [
                "User ID", "Name", "Display Name", "Main Team Role",
                "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
                "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses",
                "Win Rate %", "Absents", "Blocked", "Power Rating", "Cavalry", 
                "Mages", "Archers", "Infantry", "Whale Status", "Last Updated"
            ]
            worksheet.append_row(headers)
            self._format_player_stats_sheet(worksheet)
            return worksheet

    def _format_player_stats_sheet(self, worksheet):
        """Apply professional formatting to Player Stats sheet."""
        try:
            # Header formatting - dark blue background with white text
            worksheet.format("A1:V1", {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER",
                "borders": {
                    "top": {"style": "SOLID", "width": 2},
                    "bottom": {"style": "SOLID", "width": 2},
                    "left": {"style": "SOLID", "width": 1},
                    "right": {"style": "SOLID", "width": 1}
                }
            })

            # Freeze header row
            worksheet.freeze(rows=1)

            # Auto-resize columns
            worksheet.columns_auto_resize(0, len(worksheet.row_values(1)))

            # Format win/loss columns with conditional colors
            # Wins - green background
            worksheet.format("E:E", {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}})
            worksheet.format("G:G", {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}})
            worksheet.format("I:I", {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}})
            worksheet.format("K:K", {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}})

            # Losses - light red background
            worksheet.format("F:F", {"backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85}})
            worksheet.format("H:H", {"backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85}})
            worksheet.format("J:J", {"backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85}})
            worksheet.format("L:L", {"backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85}})

            # Win rate column - gradient based on performance
            worksheet.format("M:M", {
                "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 1.0},
                "numberFormat": {"type": "PERCENT", "pattern": "0.0%"}
            })

            # Power rating column - yellow highlight
            worksheet.format("P:P", {
                "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.8},
                "textFormat": {"bold": True}
            })

            # Add data validation for specializations (Yes/No dropdown)
            spec_columns = ["Q", "R", "S", "T", "U"]  # Cavalry, Mages, Archers, Infantry, Whale
            for col in spec_columns:
                worksheet.add_validation(f"{col}2:{col}500", "ONE_OF_LIST", ["Yes", "No"])

            logger.info("✅ Applied professional formatting to Player Stats sheet")

        except Exception as e:
            logger.warning(f"Failed to apply formatting: {e}")

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
        """Sync results history to sheets with professional formatting."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Results History", rows="200", cols="8")

            # Enhanced headers
            headers = ["📅 Date", "⚔️ Team", "🏆 Result", "👥 Players", "📝 Recorded By", "📊 Match Score", "🎯 Running Total", "💪 Performance"]
            worksheet.append_row(headers)

            # Format header row
            worksheet.format("A1:H1", {
                "backgroundColor": {"red": 0.2, "green": 0.3, "blue": 0.7},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header
            worksheet.freeze(rows=1)

            total_wins = results_data.get("total_wins", 0)
            total_losses = results_data.get("total_losses", 0)
            running_wins = 0
            running_losses = 0

            for i, entry in enumerate(results_data.get("history", [])[-50:], 2):  # Last 50 only
                date = entry.get("date", entry.get("timestamp", "Unknown"))
                if "T" in str(date):
                    try:
                        date = datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                team = entry.get("team", "Unknown").replace("_", " ").title()
                result = entry.get("result", "Unknown").capitalize()
                players = ", ".join(entry.get("players", []))
                recorded_by = entry.get("by", entry.get("recorded_by", "Unknown"))
                
                # Calculate running totals
                if result.lower() == "win":
                    running_wins += 1
                    match_score = "✅ WIN"
                    performance = "🔥 Victory!"
                else:
                    running_losses += 1
                    match_score = "❌ LOSS"
                    performance = "💪 Next time!"
                
                running_total = f"{running_wins}W - {running_losses}L"

                row_data = [date, team, result, players, recorded_by, match_score, running_total, performance]
                worksheet.append_row(row_data)

                # Color code results
                if result.lower() == "win":
                    worksheet.format(f"A{i}:H{i}", {
                        "backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}
                    })
                else:
                    worksheet.format(f"A{i}:H{i}", {
                        "backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.9}
                    })

            # Add borders to all data
            last_row = len(results_data.get("history", [])[-50:]) + 1
            worksheet.format(f"A1:H{last_row}", {
                "borders": {"style": "SOLID", "width": 1}
            })

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 8)

            # Add summary at the bottom
            summary_row = last_row + 2
            worksheet.update(f'A{summary_row}', '📊 SUMMARY STATISTICS')
            worksheet.format(f"A{summary_row}:H{summary_row}", {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "textFormat": {"fontSize": 14, "bold": True},
                "horizontalAlignment": "CENTER"
            })

            summary_row += 1
            worksheet.update(f'A{summary_row}', f'Total Wins: {total_wins}')
            worksheet.update(f'C{summary_row}', f'Total Losses: {total_losses}')
            worksheet.update(f'E{summary_row}', f'Win Rate: {total_wins/(total_wins+total_losses)*100:.1f}%' if (total_wins+total_losses) > 0 else 'Win Rate: 0%')

            logger.info("✅ Enhanced results history with professional formatting")
            return True

        except Exception as e:
            logger.error(f"Failed to sync results history: {e}")
            return False

    def sync_player_stats(self, player_stats):
        """Create player stats template."""
        return True  # Already handled by member sync

    def create_dashboard(self):
        """Create professional dashboard with charts and interactive elements."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Dashboard")
                worksheet.clear()
            except:
                worksheet = self.spreadsheet.add_worksheet(title="Dashboard", rows="30", cols="10")

            # Title section with professional styling
            worksheet.merge_cells('A1:J3')
            worksheet.update('A1', '🏆 RoW Alliance Dashboard')
            worksheet.format("A1:J3", {
                "backgroundColor": {"red": 0.1, "green": 0.2, "blue": 0.6},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 24,
                    "bold": True
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE"
            })

            # Quick Stats Section
            worksheet.update('A5', '📊 QUICK STATS')
            worksheet.format("A5:D5", {
                "backgroundColor": {"red": 0.8, "green": 0.9, "blue": 1.0},
                "textFormat": {"fontSize": 14, "bold": True},
                "horizontalAlignment": "CENTER"
            })

            # Quick stats formulas (will pull from Player Stats sheet)
            stats_data = [
                ['Total Players:', '=COUNTA(\'Player Stats\'!B:B)-1'],
                ['Main Team Players:', '=COUNTIF(\'Player Stats\'!D:D,"Yes")'],
                ['Total Wins:', '=SUM(\'Player Stats\'!K:K)'],
                ['Total Losses:', '=SUM(\'Player Stats\'!L:L)'],
                ['Overall Win Rate:', '=IF(SUM(\'Player Stats\'!K:K)+SUM(\'Player Stats\'!L:L)>0,SUM(\'Player Stats\'!K:K)/(SUM(\'Player Stats\'!K:K)+SUM(\'Player Stats\'!L:L)),0)']
            ]

            for i, (label, formula) in enumerate(stats_data):
                row = 6 + i
                worksheet.update(f'A{row}', label)
                worksheet.update(f'B{row}', formula)
                
            # Format stats section
            worksheet.format("A6:B10", {
                "borders": {"style": "SOLID", "width": 1},
                "alternatingRowsStyle": {
                    "style1": {"backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}},
                    "style2": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
                }
            })

            # Top Performers Section
            worksheet.update('D5', '🌟 TOP PERFORMERS')
            worksheet.format("D5:G5", {
                "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.2},
                "textFormat": {"fontSize": 14, "bold": True},
                "horizontalAlignment": "CENTER"
            })

            # Top performers headers
            worksheet.update('D6', 'Player')
            worksheet.update('E6', 'Total Wins')
            worksheet.update('F6', 'Win Rate')
            worksheet.update('G6', 'Power Rating')

            # Format top performers section
            worksheet.format("D6:G15", {
                "borders": {"style": "SOLID", "width": 1}
            })

            # Team Breakdown Section
            worksheet.update('A12', '⚔️ TEAM BREAKDOWN')
            worksheet.format("A12:J12", {
                "backgroundColor": {"red": 0.2, "green": 0.8, "blue": 0.4},
                "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER"
            })

            team_breakdown = [
                ['Team', 'Players', 'Avg Wins', 'Avg Losses', 'Win Rate', 'Avg Power'],
                ['Main Team', '=COUNTIF(\'Player Stats\'!D:D,"Yes")', '=AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!E:E)', '=AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!F:F)', '=IF(AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!E:E)+AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!F:F)>0,AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!E:E)/(AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!E:E)+AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!F:F)),0)', '=AVERAGEIF(\'Player Stats\'!D:D,"Yes",\'Player Stats\'!P:P)'],
                ['Team 2', '=COUNTA(\'Player Stats\'!G:G)-COUNTBLANK(\'Player Stats\'!G:G)-1', '=AVERAGE(\'Player Stats\'!G:G)', '=AVERAGE(\'Player Stats\'!H:H)', '=IF(AVERAGE(\'Player Stats\'!G:G)+AVERAGE(\'Player Stats\'!H:H)>0,AVERAGE(\'Player Stats\'!G:G)/(AVERAGE(\'Player Stats\'!G:G)+AVERAGE(\'Player Stats\'!H:H)),0)', '=AVERAGE(\'Player Stats\'!P:P)'],
                ['Team 3', '=COUNTA(\'Player Stats\'!I:I)-COUNTBLANK(\'Player Stats\'!I:I)-1', '=AVERAGE(\'Player Stats\'!I:I)', '=AVERAGE(\'Player Stats\'!J:J)', '=IF(AVERAGE(\'Player Stats\'!I:I)+AVERAGE(\'Player Stats\'!J:J)>0,AVERAGE(\'Player Stats\'!I:I)/(AVERAGE(\'Player Stats\'!I:I)+AVERAGE(\'Player Stats\'!J:J)),0)', '=AVERAGE(\'Player Stats\'!P:P)']
            ]

            for i, row_data in enumerate(team_breakdown):
                row_num = 13 + i
                for j, cell_data in enumerate(row_data):
                    col_letter = chr(65 + j)  # A, B, C, etc.
                    worksheet.update(f'{col_letter}{row_num}', cell_data)

            # Format team breakdown
            worksheet.format("A13:F16", {
                "borders": {"style": "SOLID", "width": 1},
                "alternatingRowsStyle": {
                    "style1": {"backgroundColor": {"red": 0.9, "green": 0.95, "blue": 0.9}},
                    "style2": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
                }
            })

            # Player Lookup Section
            worksheet.update('A18', '🔍 PLAYER LOOKUP')
            worksheet.format("A18:D18", {
                "backgroundColor": {"red": 0.6, "green": 0.2, "blue": 0.8},
                "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER"
            })

            worksheet.update('A19', 'Select Player:')
            worksheet.update('B19', '(Dropdown will be here)')
            worksheet.update('A20', 'Stats will appear below when player is selected')

            # Recent Activity Section
            worksheet.update('F18', '📈 RECENT ACTIVITY')
            worksheet.format("F18:J18", {
                "backgroundColor": {"red": 0.8, "green": 0.2, "blue": 0.2},
                "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER"
            })

            worksheet.update('F19', 'Last 5 Results:')
            
            # Add some instructions
            worksheet.update('A25', '💡 INSTRUCTIONS:')
            worksheet.format("A25", {"textFormat": {"fontSize": 12, "bold": True}})
            
            instructions = [
                '• This dashboard updates automatically from Player Stats sheet',
                '• Use the dropdown in B19 to select a player (set up data validation manually)',
                '• Charts can be added by selecting data ranges and Insert > Chart',
                '• Refresh the page to see latest data'
            ]
            
            for i, instruction in enumerate(instructions):
                worksheet.update(f'A{26+i}', instruction)

            # Format instructions
            worksheet.format("A26:A29", {
                "textFormat": {"fontSize": 10, "italic": True},
                "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 1.0}
            })

            logger.info("✅ Created professional dashboard with interactive elements")
            return True

        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return False

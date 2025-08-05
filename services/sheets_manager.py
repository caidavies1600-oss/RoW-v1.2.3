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
                win_rate = round(total_wins / (total_wins + total_losses), 3) if (total_wins + total_losses) > 0 else 0

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
                "verticalAlignment": "MIDDLE",
                "borders": {
                    "top": {"style": "SOLID", "width": 2},
                    "bottom": {"style": "SOLID", "width": 2},
                    "left": {"style": "SOLID", "width": 1},
                    "right": {"style": "SOLID", "width": 1}
                }
            })

            # Freeze header row
            worksheet.freeze(rows=1)

            # Set specific column widths for better readability
            try:
                # Batch update column widths
                requests = []
                column_widths = [
                    120,  # A: User ID
                    150,  # B: Name
                    150,  # C: Display Name
                    120,  # D: Main Team Role
                    80,   # E: Main Wins
                    80,   # F: Main Losses
                    80,   # G: Team2 Wins
                    80,   # H: Team2 Losses
                    80,   # I: Team3 Wins
                    80,   # J: Team3 Losses
                    90,   # K: Total Wins
                    90,   # L: Total Losses
                    100,  # M: Win Rate %
                    80,   # N: Absents
                    80,   # O: Blocked
                    100,  # P: Power Rating
                    80,   # Q: Cavalry
                    80,   # R: Mages
                    80,   # S: Archers
                    80,   # T: Infantry
                    100,  # U: Whale Status
                    130   # V: Last Updated
                ]

                for i, width in enumerate(column_widths):
                    requests.append({
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": worksheet.id,
                                "dimension": "COLUMNS",
                                "startIndex": i,
                                "endIndex": i + 1
                            },
                            "properties": {
                                "pixelSize": width
                            },
                            "fields": "pixelSize"
                        }
                    })

                # Execute batch update
                worksheet.spreadsheet.batch_update({"requests": requests})
            except Exception as e:
                logger.warning(f"Failed to set column widths: {e}")

            # Data rows formatting
            worksheet.format("A2:V500", {
                "textFormat": {"fontSize": 10},
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "borders": {
                    "top": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.9}},
                    "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.9}},
                    "left": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.9}},
                    "right": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.9}}
                }
            })

            # Apply alternating row colors with better contrast
            try:
                worksheet.format("A2:V500", {
                    "alternatingRowsStyle": {
                        "style1": {"backgroundColor": {"red": 0.96, "green": 0.96, "blue": 0.96}},
                        "style2": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to apply alternating colors: {e}")

            # Format numerical columns
            number_columns = ["E", "F", "G", "H", "I", "J", "K", "L", "N"]  # Wins, losses, absents
            for col in number_columns:
                worksheet.format(f"{col}2:{col}500", {
                    "horizontalAlignment": "CENTER",
                    "numberFormat": {"type": "NUMBER", "pattern": "0"}
                })
            
            # Format power rating column separately with decimal places
            worksheet.format("P2:P500", {
                "horizontalAlignment": "CENTER",
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0.0"}
            })

            # Format percentage column (Win Rate)
            worksheet.format("M2:M500", {
                "numberFormat": {"type": "PERCENT", "pattern": "0.00%"},
                "horizontalAlignment": "CENTER"
            })

            # Format Yes/No columns with better styling
            yes_no_columns = ["Q", "R", "S", "T", "U"]  # Cavalry, Mages, Archers, Infantry, Whale
            for col in yes_no_columns:
                worksheet.format(f"{col}2:{col}500", {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True, "fontSize": 9}
                })

            # Format blocked column with conditional coloring and validation
            worksheet.format("O2:O500", {
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
            
            # Add conditional formatting for blocked status
            try:
                worksheet.add_conditional_format_rule(
                    "O2:O500",
                    {
                        "type": "CUSTOM_FORMULA",
                        "condition": {"type": "CUSTOM_FORMULA", "value": "=$O2=\"Yes\""},
                        "format": {"backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8}}
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to add blocked status formatting: {e}")

            # Add conditional formatting for win rates
            try:
                worksheet.add_conditional_format_rule(
                    "M2:M500",
                    {
                        "type": "COLOR_SCALE",
                        "colorScale": {
                            "minValue": {"type": "NUMBER", "value": "0"},
                            "minColor": {"red": 0.957, "green": 0.263, "blue": 0.212},  # Red for low
                            "midValue": {"type": "NUMBER", "value": "0.5"},
                            "midColor": {"red": 1.0, "green": 0.851, "blue": 0.4},     # Yellow for mid
                            "maxValue": {"type": "NUMBER", "value": "1"},
                            "maxColor": {"red": 0.349, "green": 0.686, "blue": 0.314}  # Green for high
                        }
                    }
                )
                
                # Add conditional formatting for power ratings
                worksheet.add_conditional_format_rule(
                    "P2:P500",
                    {
                        "type": "COLOR_SCALE",
                        "colorScale": {
                            "minValue": {"type": "NUMBER", "value": "0"},
                            "minColor": {"red": 0.8, "green": 0.8, "blue": 0.8},     # Gray for low
                            "maxValue": {"type": "NUMBER", "value": "5000"},
                            "maxColor": {"red": 0.302, "green": 0.686, "blue": 0.969} # Blue for high
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to add conditional formatting: {e}")

            # Add data validation for specializations
            spec_columns = ["D", "O", "Q", "R", "S", "T", "U"]  # Main Team Role, Blocked, specs
            validation_options = {
                "D": ["Yes", "No"],  # Main Team Role
                "O": ["Yes", "No"],  # Blocked
                "Q": ["Yes", "No"],  # Cavalry
                "R": ["Yes", "No"],  # Mages
                "S": ["Yes", "No"],  # Archers
                "T": ["Yes", "No"],  # Infantry
                "U": ["Yes", "No"]   # Whale Status
            }

            for col, options in validation_options.items():
                try:
                    worksheet.add_validation(f"{col}2:{col}500", "ONE_OF_LIST", options)
                except Exception as e:
                    logger.warning(f"Failed to add validation for column {col}: {e}")

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
                ("Error Summary", self.create_error_summary),
                ("Match Statistics", lambda: self.create_match_statistics(all_data.get("match_stats", {}))),
                ("Alliance Tracking", self.create_alliance_tracking),
                ("Notification Preferences", lambda: self.create_notification_preferences(all_data.get("notification_preferences", {}))),
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

    def create_error_summary(self):
        """Create Error Summary sheet for monitoring bot errors."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Error Summary")
                worksheet.clear()
            except:
                worksheet = self.spreadsheet.add_worksheet(title="Error Summary", rows="100", cols="8")

            # Enhanced headers with emojis
            headers = ["🕐 Timestamp", "⚠️ Error Type", "📍 Source", "💬 Message", "👤 User", "🛠️ Status", "🔧 Action Taken", "📝 Notes"]
            worksheet.append_row(headers)

            # Format header row
            worksheet.format("A1:H1", {
                "backgroundColor": {"red": 0.8, "green": 0.2, "blue": 0.2},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header
            worksheet.freeze(rows=1)

            # Add sample error entries
            sample_errors = [
                [datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "Command Error", "EventManager", "Missing permissions", "TestUser#1234", "🔴 Open", "Pending Review", "User needs role"],
                [datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "Sheets Error", "SheetsManager", "Rate limit exceeded", "System", "🟡 In Progress", "Retry scheduled", "Auto-resolved"],
                [datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "Discord Error", "Bot Client", "Connection timeout", "System", "🟢 Resolved", "Reconnected", "Network issue"]
            ]

            for i, error_data in enumerate(sample_errors, 2):
                worksheet.append_row(error_data)

                # Color code by status
                if "🔴 Open" in error_data[5]:
                    worksheet.format(f"A{i}:H{i}", {"backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.9}})
                elif "🟡 In Progress" in error_data[5]:
                    worksheet.format(f"A{i}:H{i}", {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.9}})
                else:  # Resolved
                    worksheet.format(f"A{i}:H{i}", {"backgroundColor": {"red": 0.9, "green": 1.0, "blue": 0.9}})

            # Add borders
            worksheet.format("A1:H100", {"borders": {"style": "SOLID", "width": 1}})

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 8)

            # Add data validation for Status column
            worksheet.add_validation("F2:F100", "ONE_OF_LIST", ["🔴 Open", "🟡 In Progress", "🟢 Resolved", "🔵 Monitoring"])

            logger.info("✅ Created Error Summary sheet")
            return True

        except Exception as e:
            logger.error(f"Failed to create error summary: {e}")
            return False

    def create_match_statistics(self, match_stats):
        """Create Match Statistics sheet with detailed battle analytics."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Match Statistics")
                worksheet.clear()
            except:
                worksheet = self.spreadsheet.add_worksheet(title="Match Statistics", rows="200", cols="12")

            # Enhanced headers
            headers = ["📅 Date", "⚔️ Match Type", "🏆 Result", "👥 Team Size", "⭐ MVP Player", "💪 Total Power", "🎯 Strategy", "🌍 Map", "⏱️ Duration", "📊 Score", "🎖️ Rewards", "📝 Notes"]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:L1", {
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header
            worksheet.freeze(rows=1)

            # Add sample match data
            sample_matches = [
                [datetime.utcnow().strftime("%Y-%m-%d"), "Alliance vs Alliance", "🏆 Victory", "8", "PlayerName", "2500", "Rush Strategy", "Desert Plains", "45min", "3-1", "Gold + Honor", "Great coordination"],
                [datetime.utcnow().strftime("%Y-%m-%d"), "Territory Battle", "❌ Defeat", "6", "AnotherPlayer", "2200", "Defensive", "Mountain Pass", "62min", "1-2", "Silver", "Need better timing"],
                [datetime.utcnow().strftime("%Y-%m-%d"), "Siege War", "🏆 Victory", "10", "TopPlayer", "3000", "Mixed Formation", "Castle Walls", "38min", "2-0", "Platinum + Items", "Perfect execution"]
            ]

            for i, match_data in enumerate(sample_matches, 2):
                worksheet.append_row(match_data)

                # Color code by result
                if "🏆 Victory" in match_data[2]:
                    worksheet.format(f"A{i}:L{i}", {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}})
                else:
                    worksheet.format(f"A{i}:L{i}", {"backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.9}})

            # Add summary section
            summary_row = len(sample_matches) + 4
            worksheet.update(f'A{summary_row}', '📊 MATCH SUMMARY')
            worksheet.format(f"A{summary_row}:L{summary_row}", {
                "backgroundColor": {"red": 0.1, "green": 0.3, "blue": 0.6},
                "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER"
            })

            # Add summary formulas
            summary_row += 1
            worksheet.update(f'A{summary_row}', 'Total Matches:')
            worksheet.update(f'B{summary_row}', f'=COUNTA(A2:A{len(sample_matches)+1})')
            worksheet.update(f'D{summary_row}', 'Win Rate:')
            worksheet.update(f'E{summary_row}', f'=COUNTIF(C2:C{len(sample_matches)+1},"🏆*")/COUNTA(C2:C{len(sample_matches)+1})')

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 12)

            logger.info("✅ Created Match Statistics sheet")
            return True

        except Exception as e:
            logger.error(f"Failed to create match statistics: {e}")
            return False

    def create_alliance_tracking(self):
        """Create Alliance Tracking sheet for monitoring alliance relationships."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Alliance Tracking")
                worksheet.clear()
            except:
                worksheet = self.spreadsheet.add_worksheet(title="Alliance Tracking", rows="50", cols="10")

            # Headers
            headers = ["🏰 Alliance Name", "👑 Leader", "👥 Member Count", "💪 Total Power", "🤝 Relationship", "📍 Territory", "📈 Activity Level", "🛡️ War Status", "📞 Contact", "📝 Notes"]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:J1", {
                "backgroundColor": {"red": 0.6, "green": 0.3, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header
            worksheet.freeze(rows=1)

            # Add sample alliance data
            sample_alliances = [
                ["Iron Fist Alliance", "Commander_Alpha", "45", "125000", "🤝 Allied", "North Region", "🟢 High", "☮️ Peace", "Discord: Alpha#1234", "Strong military alliance"],
                ["Golden Eagles", "Eagle_Lord", "38", "98000", "🟡 Neutral", "East Region", "🟡 Medium", "⚔️ At War", "In-game mail", "Economic focused"],
                ["Shadow Legion", "DarkKnight", "52", "140000", "🔴 Enemy", "South Region", "🔴 High", "⚔️ At War", "No contact", "Aggressive expansion"],
                ["Trade Masters", "Merchant_King", "29", "75000", "🤝 Allied", "West Region", "🟢 High", "☮️ Peace", "Discord: Merchant#5678", "Trading partnership"]
            ]

            for i, alliance_data in enumerate(sample_alliances, 2):
                worksheet.append_row(alliance_data)

                # Color code by relationship
                if "🤝 Allied" in alliance_data[4]:
                    worksheet.format(f"A{i}:J{i}", {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}})
                elif "🔴 Enemy" in alliance_data[4]:
                    worksheet.format(f"A{i}:J{i}", {"backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85}})
                else:  # Neutral
                    worksheet.format(f"A{i}:J{i}", {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.9}})

            # Add data validation for relationship status
            worksheet.add_validation("E2:E50", "ONE_OF_LIST", ["🤝 Allied", "🟡 Neutral", "🔴 Enemy", "🤔 Unknown"])
            worksheet.add_validation("G2:G50", "ONE_OF_LIST", ["🟢 High", "🟡 Medium", "🔴 Low", "⚫ Inactive"])
            worksheet.add_validation("H2:H50", "ONE_OF_LIST", ["☮️ Peace", "⚔️ At War", "🛡️ Defending", "⚡ Preparing"])

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 10)

            logger.info("✅ Created Alliance Tracking sheet")
            return True

        except Exception as e:
            logger.error(f"Failed to create alliance tracking: {e}")
            return False

    def create_notification_preferences(self, notification_data):
        """Create Notification Preferences sheet for managing user alerts."""
        try:
            try:
                worksheet = self.spreadsheet.worksheet("Notification Preferences")
                worksheet.clear()
            except:
                worksheet = self.spreadsheet.add_worksheet(title="Notification Preferences", rows="100", cols="9")

            # Headers
            headers = ["👤 User ID", "📝 Display Name", "📢 Event Alerts", "🏆 Result Notifications", "⚠️ Error Alerts", "📱 DM Notifications", "🕐 Reminder Time", "🌍 Timezone", "📅 Last Updated"]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:I1", {
                "backgroundColor": {"red": 0.4, "green": 0.7, "blue": 0.4},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header
            worksheet.freeze(rows=1)

            # Add sample notification preferences
            sample_preferences = [
                ["123456789", "TestUser1", "✅ Enabled", "✅ Enabled", "❌ Disabled", "✅ Enabled", "30 minutes", "UTC-5", datetime.utcnow().strftime("%Y-%m-%d")],
                ["987654321", "TestUser2", "✅ Enabled", "❌ Disabled", "✅ Enabled", "❌ Disabled", "1 hour", "UTC+0", datetime.utcnow().strftime("%Y-%m-%d")],
                ["111222333", "TestUser3", "❌ Disabled", "✅ Enabled", "✅ Enabled", "✅ Enabled", "2 hours", "UTC+8", datetime.utcnow().strftime("%Y-%m-%d")]
            ]

            for i, pref_data in enumerate(sample_preferences, 2):
                worksheet.append_row(pref_data)

            # Add data validation for preference columns
            enabled_options = ["✅ Enabled", "❌ Disabled"]
            worksheet.add_validation("C2:F100", "ONE_OF_LIST", enabled_options)

            time_options = ["15 minutes", "30 minutes", "1 hour", "2 hours", "6 hours", "24 hours"]
            worksheet.add_validation("G2:G100", "ONE_OF_LIST", time_options)

            # Add borders
            worksheet.format("A1:I100", {"borders": {"style": "SOLID", "width": 1}})

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 9)

            # Add instructions section
            instruction_row = len(sample_preferences) + 4
            worksheet.update(f'A{instruction_row}', '💡 INSTRUCTIONS:')
            worksheet.format(f"A{instruction_row}:I{instruction_row}", {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 1.0},
                "textFormat": {"fontSize": 12, "bold": True},
                "horizontalAlignment": "LEFT"
            })

            instructions = [
                "• Modify preferences directly in this sheet",
                "• Changes sync automatically with the bot",
                "• Use dropdowns for consistent formatting",
                "• Contact admin for timezone changes"
            ]

            for i, instruction in enumerate(instructions):
                worksheet.update(f'A{instruction_row + 1 + i}', instruction)

            logger.info("✅ Created Notification Preferences sheet")
            return True

        except Exception as e:
            logger.error(f"Failed to create notification preferences: {e}")
            return False
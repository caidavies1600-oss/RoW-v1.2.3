"""
Google Sheets manager for the RoW bot.

This module handles all interactions with Google Sheets for:
- Loading and saving event data
- Managing player signups and team assignments
- Storing and retrieving match results and statistics

Usage:
    Import and use the `SheetsManager` class in other parts of the bot to
    interact with Google Sheets for event management.

Requirements:
    - Google Sheets API credentials must be set up
    - Required scopes: `https://www.googleapis.com/auth/spreadsheets`
"""

import random
from datetime import datetime
import os
import asyncio
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.constants import GOOGLE_SHEET_ID, GOOGLE_SHEET_RANGE
from utils.logger import setup_logger

import gspread
from google.oauth2.service_account import Credentials
import json
import time

logger = setup_logger("sheets_manager")


class SheetsManager:
    def __init__(self, spreadsheet_id=GOOGLE_SHEET_ID, range_name=GOOGLE_SHEET_RANGE):
        """Initialize the SheetsManager.

        Args:
            spreadsheet_id (str): The ID of the Google Sheet to manage.
            range_name (str): The A1 notation of the range to access.
        """
        self.spreadsheet_id = spreadsheet_id
        self.range_name = range_name
        self.service = None
        self.spreadsheet = None # This will store the gspread client object

    def connect(self):
        """Connect to the Google Sheets API and open the spreadsheet."""
        try:
            # Using gspread for more robust sheet interaction
            scope = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope) # Assuming credentials.json is in root
            client = gspread.authorize(creds)
            self.spreadsheet = client.open_by_key(self.spreadsheet_id)
            logger.info(f"✅ Connected to Google Sheets: {self.spreadsheet.title}")
            
            # Keep the googleapiclient service for other potential uses, though gspread is preferred for direct data ops
            self.service = build("sheets", "v4")

        except FileNotFoundError:
            logger.error("❌ credentials.json not found. Please ensure it's in the root directory.")
            self.spreadsheet = None
            self.service = None
        except HttpError as e:
            logger.error(f"❌ Failed to connect to Google Sheets API: {e}")
            self.spreadsheet = None
            self.service = None
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during connection: {e}")
            self.spreadsheet = None
            self.service = None


    def is_connected(self) -> bool:
        """Check if the manager is connected to Google Sheets.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self.spreadsheet is not None

    def get_spreadsheet_url(self) -> str:
        """Get the URL of the current spreadsheet."""
        if self.spreadsheet:
            return self.spreadsheet.url
        return ""

    async def load_data(self) -> dict | None:
        """Load data from Google Sheets."""
        if not self.is_connected():
            self.connect()
            if not self.is_connected():
                logger.error("❌ Cannot load data, not connected to Google Sheets.")
                return None

        try:
            data = {
                "events": {"main_team": [], "team_2": [], "team_3": []},
                "blocked": {},
                "results": {"total_wins": 0, "total_losses": 0, "history": []},
                "player_stats": {},
                "ign_map": {},
                "absent": {}
            }

            # Load Current Teams using gspread
            try:
                worksheet = self.spreadsheet.worksheet("Current Teams")
                rows = worksheet.get_all_records()
                for row in rows:
                    team = row.get("Team", "").lower().replace(" ", "_")
                    players = row.get("Players", "")
                    if team in data["events"] and players:
                        player_list = [p.strip() for p in players.split(",") if p.strip()]
                        data["events"][team] = player_list
                logger.info("Loaded 'Current Teams' sheet.")
            except gspread.WorksheetNotFound:
                logger.info("Sheet 'Current Teams' not found, using defaults.")
            except Exception as e:
                logger.warning(f"Could not load 'Current Teams' sheet: {e}")

            # Load Blocked Users using gspread
            try:
                worksheet = self.spreadsheet.worksheet("Blocked Users")
                rows = worksheet.get_all_records()
                for row in rows:
                    user_id = str(row.get("User ID"))
                    if user_id:
                        data["blocked"][user_id] = {
                            "reason": row.get("Reason", "No reason provided"),
                            "timestamp": row.get("Timestamp", datetime.utcnow().isoformat())
                        }
                logger.info("Loaded 'Blocked Users' sheet.")
            except gspread.WorksheetNotFound:
                logger.info("Sheet 'Blocked Users' not found.")
            except Exception as e:
                logger.warning(f"Could not load 'Blocked Users' sheet: {e}")
                
            # Load Results History using gspread
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
                rows = worksheet.get_all_records()
                results_history = []
                total_wins = 0
                total_losses = 0
                
                for row in rows:
                    if "Total Wins" in row and "Total Losses" in row:
                        total_wins = row.get("Total Wins", 0)
                        total_losses = row.get("Total Losses", 0)
                    else:
                        results_history.append({
                            "date": row.get("Date"),
                            "team": row.get("Team"),
                            "result": row.get("Result"),
                            "players": row.get("Players", "").split(", "),
                            "by": row.get("Recorded By"),
                        })
                data["results"]["total_wins"] = total_wins
                data["results"]["total_losses"] = total_losses
                data["results"]["history"] = results_history
                logger.info("Loaded 'Results History' sheet.")
            except gspread.WorksheetNotFound:
                logger.info("Sheet 'Results History' not found.")
            except Exception as e:
                logger.warning(f"Could not load 'Results History' sheet: {e}")

            # Load Player Stats using gspread
            try:
                worksheet = self.spreadsheet.worksheet("Player Stats")
                rows = worksheet.get_all_records()
                player_stats = {}
                for row in rows:
                    user_id = str(row.get("User ID"))
                    if user_id:
                        player_stats[user_id] = {
                            "name": row.get("Name"),
                            "display_name": row.get("Display Name"),
                            "has_main_role": row.get("Main Team Role") == "Yes",
                            "team_results": {
                                "main_team": {"wins": row.get("Main Wins", 0), "losses": row.get("Main Losses", 0)},
                                "team_2": {"wins": row.get("Team2 Wins", 0), "losses": row.get("Team2 Losses", 0)},
                                "team_3": {"wins": row.get("Team3 Wins", 0), "losses": row.get("Team3 Losses", 0)}
                            },
                            "absents": row.get("Absents", 0),
                            "blocked": row.get("Blocked") == "Yes",
                            "power_rating": row.get("Power Rating", 0),
                            "specializations": {
                                "cavalry": row.get("Cavalry") == "Yes",
                                "mages": row.get("Mages") == "Yes",
                                "archers": row.get("Archers") == "Yes",
                                "infantry": row.get("Infantry") == "Yes",
                                "whale": row.get("Whale") == "Yes",
                            },
                            "notes": row.get("Notes", ""),
                            "last_updated": row.get("Last Updated"),
                        }
                data["player_stats"] = player_stats
                logger.info("Loaded 'Player Stats' sheet.")
            except gspread.WorksheetNotFound:
                logger.info("Sheet 'Player Stats' not found.")
            except Exception as e:
                logger.warning(f"Could not load 'Player Stats' sheet: {e}")

            # Load IGN Map (Assuming a sheet named 'IGN Map' with 'User ID' and 'IGN' columns)
            try:
                worksheet = self.spreadsheet.worksheet("IGN Map")
                rows = worksheet.get_all_records()
                ign_map = {}
                for row in rows:
                    user_id = str(row.get("User ID"))
                    ign = row.get("IGN")
                    if user_id and ign:
                        ign_map[user_id] = ign
                data["ign_map"] = ign_map
                logger.info("Loaded 'IGN Map' sheet.")
            except gspread.WorksheetNotFound:
                logger.info("Sheet 'IGN Map' not found.")
            except Exception as e:
                logger.warning(f"Could not load 'IGN Map' sheet: {e}")
            
            # Load Absent Users (Assuming a sheet named 'Absent Users' with 'User ID' and 'Date' columns)
            try:
                worksheet = self.spreadsheet.worksheet("Absent Users")
                rows = worksheet.get_all_records()
                absent_users = {}
                for row in rows:
                    user_id = str(row.get("User ID"))
                    date = row.get("Date", datetime.utcnow().date().isoformat())
                    if user_id:
                        if user_id not in absent_users:
                            absent_users[user_id] = []
                        absent_users[user_id].append(date)
                data["absent"] = absent_users
                logger.info("Loaded 'Absent Users' sheet.")
            except gspread.WorksheetNotFound:
                logger.info("Sheet 'Absent Users' not found.")
            except Exception as e:
                logger.warning(f"Could not load 'Absent Users' sheet: {e}")


            return data

        except Exception as e:
            logger.error(f"❌ Failed to load data from sheets: {e}")
            import traceback
            logger.error(f"Load data traceback: {traceback.format_exc()}")
            return None

    async def sync_data(self, filepath: str, data: Any):
        """Sync data to appropriate sheet based on filepath."""
        if not self.is_connected():
            logger.warning("Not connected to Google Sheets. Cannot sync data.")
            return

        filename = os.path.basename(filepath)

        try:
            if filename == "events.json":
                await self._run_sync_in_executor(lambda: self.sync_current_teams(data))
            elif filename == "events_history.json":
                await self._run_sync_in_executor(lambda: self.sync_events_history(data))
            elif filename == "blocked_users.json":
                await self._run_sync_in_executor(lambda: self.sync_blocked_users(data))
            elif filename == "event_results.json":
                await self._run_sync_in_executor(lambda: self.sync_results_history(data))
            elif filename == "player_stats.json":
                await self._run_sync_in_executor(lambda: self.sync_player_stats(data))
            elif filename == "notification_preferences.json":
                await self._run_sync_in_executor(lambda: self.sync_notification_preferences(data))
            else:
                logger.warning(f"No sync method defined for file: {filename}")
        except Exception as e:
            logger.error(f"Failed to sync {filename}: {e}")
            import traceback
            logger.error(f"Sync {filename} traceback: {traceback.format_exc()}")


    async def _run_sync_in_executor(self, sync_func):
        """Run sync operation in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_func)

    def sync_current_teams(self, data):
        """Sync current teams to the 'Current Teams' sheet."""
        if not self.spreadsheet:
            return False
        try:
            worksheet = self.spreadsheet.worksheet("Current Teams")
            worksheet.clear() # Clear existing data

            values = [["Team", "Players"]] # Headers
            for team, players in data.get("events", {}).items():
                values.append([team.replace("_", " ").title(), ", ".join(players)])
            
            worksheet.update("A1", values)
            logger.info("✅ Synced current teams")
            return True
        except gspread.WorksheetNotFound:
            logger.info("Sheet 'Current Teams' not found, creating it.")
            worksheet = self.spreadsheet.add_worksheet(title="Current Teams", rows="100", cols="2")
            values = [["Team", "Players"]]
            for team, players in data.get("events", {}).items():
                values.append([team.replace("_", " ").title(), ", ".join(players)])
            worksheet.update("A1", values)
            logger.info("✅ Created and synced current teams")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            import traceback
            logger.error(f"Sync current teams traceback: {traceback.format_exc()}")
            return False

    def sync_events_history(self, data):
        """Sync event history to the 'Event History' sheet."""
        if not self.spreadsheet:
            return False
        try:
            worksheet = self.spreadsheet.worksheet("Event History")
            worksheet.clear()

            values = [["Event Name", "Winner", "Date"]] # Example columns, adjust as needed
            for event in data.get("event_history", []): # Assuming data structure
                values.append([event.get("name"), event.get("winner"), event.get("date")])

            worksheet.update("A1", values)
            logger.info("✅ Synced event history")
            return True
        except gspread.WorksheetNotFound:
            logger.info("Sheet 'Event History' not found, creating it.")
            worksheet = self.spreadsheet.add_worksheet(title="Event History", rows="1000", cols="3")
            values = [["Event Name", "Winner", "Date"]]
            for event in data.get("event_history", []):
                values.append([event.get("name"), event.get("winner"), event.get("date")])
            worksheet.update("A1", values)
            logger.info("✅ Created and synced event history")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to sync event history: {e}")
            import traceback
            logger.error(f"Sync event history traceback: {traceback.format_exc()}")
            return False

    def sync_blocked_users(self, data):
        """Sync blocked users to the 'Blocked Users' sheet."""
        if not self.spreadsheet:
            return False
        try:
            worksheet = self.spreadsheet.worksheet("Blocked Users")
            worksheet.clear()

            values = [["User ID", "Reason", "Timestamp"]] # Example columns
            for user_id, info in data.get("blocked", {}).items():
                values.append([user_id, info.get("reason"), info.get("timestamp")])

            worksheet.update("A1", values)
            logger.info("✅ Synced blocked users")
            return True
        except gspread.WorksheetNotFound:
            logger.info("Sheet 'Blocked Users' not found, creating it.")
            worksheet = self.spreadsheet.add_worksheet(title="Blocked Users", rows="1000", cols="3")
            values = [["User ID", "Reason", "Timestamp"]]
            for user_id, info in data.get("blocked", {}).items():
                values.append([user_id, info.get("reason"), info.get("timestamp")])
            worksheet.update("A1", values)
            logger.info("✅ Created and synced blocked users")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to sync blocked users: {e}")
            import traceback
            logger.error(f"Sync blocked users traceback: {traceback.format_exc()}")
            return False

    def sync_results_history(self, results_data):
        """Sync results history to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            try:
                worksheet = self.spreadsheet.worksheet("Results History")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Results History", rows="1000", cols="7")

            # Headers
            headers = ["📅 Date", "🎯 Team", "🏆 Result", "👥 Players", "📝 Recorded By", "✅ Total Wins", "❌ Total Losses"]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:G1", {
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Add results data with proper rate limiting
            for i, entry in enumerate(results_data.get("history", [])):
                # Rate limiting: pause every 10 entries
                if i > 0 and i % 10 == 0:
                    logger.info(f"Processed {i} results, pausing 2s for rate limit...")
                    time.sleep(2)

                try:
                    # Handle date formatting
                    date = entry.get("date", entry.get("timestamp", "Unknown"))
                    if isinstance(date, str) and "T" in date:  # ISO format
                        try:
                            date = datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
                        except:
                            date = str(date)
                    elif isinstance(date, datetime):
                        date = date.strftime("%Y-%m-%d %H:%M")

                    team = entry.get("team", "Unknown")
                    team_display = {"main_team": "Main Team", "team_2": "Team 2", "team_3": "Team 3"}.get(team, team.title().replace('_', ' '))

                    result = entry.get("result", "Unknown").capitalize()
                    players = ", ".join(entry.get("players", []))
                    recorded_by = entry.get("by", entry.get("recorded_by", "Unknown"))

                    row_data = [
                        date,
                        team_display,
                        result,
                        players,
                        recorded_by,
                        results_data.get("total_wins", 0),
                        results_data.get("total_losses", 0)
                    ]

                    worksheet.append_row(row_data)

                    # Color code wins/losses
                    row_num = i + 2 # +1 for header, +1 for 0-based index
                    if result.lower() == "win":
                        worksheet.format(f"A{row_num}:G{row_num}", {
                            "backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}
                        })
                    elif result.lower() == "loss":
                        worksheet.format(f"A{row_num}:G{row_num}", {
                            "backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.9}
                        })

                except Exception as e:
                    logger.warning(f"Failed to sync result entry {i}: {e}")
                    continue

            logger.info(f"✅ Synced {len(results_data.get('history', []))} results to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync results history: {e}")
            import traceback
            logger.error(f"Results sync traceback: {traceback.format_exc()}")
            return False

    def sync_player_stats(self, player_stats_data):
        """Sync player statistics to Google Sheets with proper formatting."""
        if not self.spreadsheet:
            return False

        try:
            try:
                worksheet = self.spreadsheet.worksheet("Player Stats")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Player Stats", rows="300", cols="25")

            # Headers
            headers = [
                "👤 User ID", "🏷️ Name", "📱 Display Name", "🎯 Main Team Role", 
                "🏆 Main Wins", "❌ Main Losses", "🔥 Team2 Wins", "⚡ Team2 Losses",
                "⭐ Team3 Wins", "💫 Team3 Losses", "📊 Total Wins", "📉 Total Losses", 
                "📈 Win Rate", "🚫 Absents", "⛔ Blocked", "⚡ Power Rating",
                "🐎 Cavalry", "🧙 Mages", "🏹 Archers", "⚔️ Infantry", "🐋 Whale", 
                "📅 Last Updated", "📝 Notes", "🔗 Discord Link", "📊 Participation Score"
            ]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:Y1", {
                "backgroundColor": {"red": 0.1, "green": 0.4, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 11,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Freeze header row
            worksheet.freeze(rows=1)

            # Add player data
            if player_stats_data:
                for i, (user_id, stats) in enumerate(player_stats_data.items()):
                    # Rate limiting: pause every 15 players
                    if i > 0 and i % 15 == 0:
                        logger.info(f"Processed {i} players, pausing 3s for rate limit...")
                        time.sleep(3)

                    try:
                        # Calculate derived stats
                        main_wins = stats.get("team_results", {}).get("main_team", {}).get("wins", 0)
                        main_losses = stats.get("team_results", {}).get("main_team", {}).get("losses", 0)
                        team2_wins = stats.get("team_results", {}).get("team_2", {}).get("wins", 0)
                        team2_losses = stats.get("team_results", {}).get("team_2", {}).get("losses", 0)
                        team3_wins = stats.get("team_results", {}).get("team_3", {}).get("wins", 0)
                        team3_losses = stats.get("team_results", {}).get("team_3", {}).get("losses", 0)

                        total_wins = main_wins + team2_wins + team3_wins
                        total_losses = main_losses + team2_losses + team3_losses
                        total_games = total_wins + total_losses
                        win_rate = round((total_wins / total_games * 100), 1) if total_games > 0 else 0

                        # Get specializations
                        specs = stats.get("specializations", {})

                        row_data = [
                            user_id,
                            stats.get("name", f"Player_{user_id}"),
                            stats.get("display_name", "Unknown"),
                            "Yes" if stats.get("has_main_role", False) else "No",
                            main_wins, main_losses,
                            team2_wins, team2_losses,
                            team3_wins, team3_losses,
                            total_wins, total_losses,
                            f"{win_rate}%",
                            stats.get("absents", 0),
                            "Yes" if stats.get("blocked", False) else "No",
                            stats.get("power_rating", 0),
                            "Yes" if specs.get("cavalry", False) else "No",
                            "Yes" if specs.get("mages", False) else "No",
                            "Yes" if specs.get("archers", False) else "No",
                            "Yes" if specs.get("infantry", False) else "No",
                            "Yes" if specs.get("whale", False) else "No",
                            datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                            stats.get("notes", ""),
                            f"<@{user_id}>", # Discord link placeholder
                            total_games  # Participation score
                        ]

                        worksheet.append_row(row_data)

                    except Exception as e:
                        logger.warning(f"Failed to sync player {user_id}: {e}")
                        continue

            # Apply professional formatting
            try:
                # Auto-resize columns
                worksheet.columns_auto_resize(0, 25)

                # Add conditional formatting for win rates
                worksheet.add_conditional_format_rule(
                    "M2:M500", # Assuming max 500 players for now, adjust if needed
                    {
                        "type": "COLOR_SCALE",
                        "colorScale": {
                            "minValue": {"type": "NUMBER", "value": "0"},
                            "minColor": {"red": 1.0, "green": 0.4, "blue": 0.4},      # Red for low
                            "midValue": {"type": "NUMBER", "value": "50"},
                            "midColor": {"red": 1.0, "green": 1.0, "blue": 0.4},      # Yellow for mid
                            "maxValue": {"type": "NUMBER", "value": "100"},
                            "maxColor": {"red": 0.349, "green": 0.686, "blue": 0.314} # Green for high
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to apply formatting to Player Stats: {e}")

            logger.info(f"✅ Synced {len(player_stats_data) if player_stats_data else 0} players to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync player stats: {e}")
            import traceback
            logger.error(f"Player stats sync traceback: {traceback.format_exc()}")
            return False

    def sync_notification_preferences(self, notification_prefs):
        """Sync notification preferences to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            try:
                worksheet = self.spreadsheet.worksheet("Notification Preferences")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(title="Notification Preferences", rows="300", cols="12")

            # Headers
            headers = [
                "👤 User ID", "📝 Display Name", "📬 Method", "⏰ Event Reminders", 
                "🏆 Result Notifications", "👥 Team Updates", "⚠️ Error Alerts",
                "⏱️ Reminder Minutes", "🌅 Quiet Start", "🌙 Quiet End", 
                "🌍 Timezone Offset", "📅 Last Updated"
            ]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:L1", {
                "backgroundColor": {"red": 0.6, "green": 0.2, "blue": 0.8},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Add data
            users_data = notification_prefs.get("users", {})
            if users_data:
                for i, (user_id, prefs) in enumerate(users_data.items()):
                    # Rate limiting
                    if i > 0 and i % 20 == 0:
                        logger.info(f"Processed {i} notification prefs, pausing 2s for rate limit...")
                        time.sleep(2)

                    row_data = [
                        user_id,
                        prefs.get("display_name", f"User_{user_id}"),
                        prefs.get("method", "Discord DM"),
                        "Yes" if prefs.get("event_reminders", True) else "No",
                        "Yes" if prefs.get("result_notifications", True) else "No",
                        "Yes" if prefs.get("team_updates", True) else "No",
                        "Yes" if prefs.get("error_alerts", False) else "No",
                        prefs.get("reminder_times", [60])[0] if prefs.get("reminder_times") else 60, # Taking the first reminder time
                        prefs.get("quiet_hours", {}).get("start", "22:00"),
                        prefs.get("quiet_hours", {}).get("end", "08:00"),
                        prefs.get("timezone_offset", 0),
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    ]
                    worksheet.append_row(row_data)
            
            logger.info(f"✅ Synced {len(users_data)} notification preferences to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync notification preferences: {e}")
            import traceback
            logger.error(f"Notification prefs sync traceback: {traceback.format_exc()}")
            return False

    def sync_ign_map(self, ign_map_data):
        """Sync IGN map to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            worksheet = self.spreadsheet.worksheet("IGN Map")
            worksheet.clear()

            # Headers
            headers = ["User ID", "IGN"]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:B1", {
                "backgroundColor": {"red": 0.8, "green": 0.4, "blue": 0.1},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Add data
            if ign_map_data:
                for i, (user_id, ign) in enumerate(ign_map_data.items()):
                    row_data = [user_id, ign]
                    worksheet.append_row(row_data)
            
            logger.info(f"✅ Synced {len(ign_map_data) if ign_map_data else 0} IGN mappings to Google Sheets")
            return True

        except gspread.WorksheetNotFound:
            logger.info("Sheet 'IGN Map' not found, creating it.")
            worksheet = self.spreadsheet.add_worksheet(title="IGN Map", rows="500", cols="2")
            headers = ["User ID", "IGN"]
            worksheet.append_row(headers)
            worksheet.format("A1:B1", {
                "backgroundColor": {"red": 0.8, "green": 0.4, "blue": 0.1},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })
            if ign_map_data:
                for user_id, ign in ign_map_data.items():
                    worksheet.append_row([user_id, ign])
            logger.info("✅ Created and synced IGN Map sheet.")
            return True
        except Exception as e:
            logger.error(f"Failed to sync IGN map: {e}")
            import traceback
            logger.error(f"IGN map sync traceback: {traceback.format_exc()}")
            return False

    def sync_absent_users(self, absent_users_data):
        """Sync absent users to Google Sheets."""
        if not self.spreadsheet:
            return False

        try:
            worksheet = self.spreadsheet.worksheet("Absent Users")
            worksheet.clear()

            # Headers
            headers = ["User ID", "Date Absent"]
            worksheet.append_row(headers)

            # Format header
            worksheet.format("A1:B1", {
                "backgroundColor": {"red": 0.9, "green": 0.5, "blue": 0.2},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

            # Add data
            if absent_users_data:
                for user_id, dates in absent_users_data.items():
                    for date in dates:
                        row_data = [user_id, date]
                        worksheet.append_row(row_data)
            
            logger.info(f"✅ Synced {sum(len(d) for d in absent_users_data.values()) if absent_users_data else 0} absent user entries to Google Sheets")
            return True

        except gspread.WorksheetNotFound:
            logger.info("Sheet 'Absent Users' not found, creating it.")
            worksheet = self.spreadsheet.add_worksheet(title="Absent Users", rows="1000", cols="2")
            headers = ["User ID", "Date Absent"]
            worksheet.append_row(headers)
            worksheet.format("A1:B1", {
                "backgroundColor": {"red": 0.9, "green": 0.5, "blue": 0.2},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })
            if absent_users_data:
                for user_id, dates in absent_users_data.items():
                    for date in dates:
                        worksheet.append_row([user_id, date])
            logger.info("✅ Created and synced Absent Users sheet.")
            return True
        except Exception as e:
            logger.error(f"Failed to sync absent users: {e}")
            import traceback
            logger.error(f"Absent users sync traceback: {traceback.format_exc()}")
            return False
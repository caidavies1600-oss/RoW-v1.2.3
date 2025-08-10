from datetime import datetime
from .worksheet_handlers import WorksheetHandlers
from .config import SHEET_CONFIGS
from utils.logger import setup_logger

logger = setup_logger("template_creator")

class TemplateCreator(WorksheetHandlers):
    """Creates templates for manual data entry."""

    def create_match_statistics_template(self):
        """Create match statistics template for manual data entry."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Match Statistics"]
            worksheet = self.get_or_create_worksheet("Match Statistics", config["rows"], config["cols"])

            # Create template only if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                worksheet.clear()
                worksheet.append_row(config["headers"])

                # Add formatting instructions
                instructions = [
                    'Enter match data manually here',
                    'YYYY-MM-DD format',
                    'Main Team/Team 2/Team 3',
                    'Win/Loss',
                    'Enemy alliance name',
                    'Enemy alliance tag'
                ]

                for i, instruction in enumerate(instructions):
                    if i < len(config["headers"]):
                        worksheet.update_cell(2, i + 1, instruction)

                logger.info("✅ Created match statistics template for manual entry")
            else:
                logger.info("✅ Match statistics sheet already exists, skipping template creation")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create match statistics template: {e}")
            return False

    def create_alliance_tracking_sheet(self):
        """Create alliance tracking sheet for enemy alliance performance."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Alliance Tracking"]
            worksheet = self.get_or_create_worksheet("Alliance Tracking", config["rows"], config["cols"])

            # Create template only if sheet is empty
            if len(worksheet.get_all_values()) <= 1:
                worksheet.clear()
                worksheet.append_row(config["headers"])

                # Add example row
                example_row = [
                    "Example Alliance", "EX", 0, 0, 0, "0%", 0,
                    "Medium", "They focus on cavalry", "Never", "K123",
                    "High", "Very Active", "High", "Strong in KvK events"
                ]
                worksheet.append_row(example_row)

                logger.info("✅ Created alliance tracking template")
            else:
                logger.info("✅ Alliance tracking sheet already exists, skipping template creation")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create alliance tracking sheet: {e}")
            return False

    def create_dashboard(self):
        """Create an interactive dashboard with dropdowns and charts."""
        if not self.is_connected():
            return False

        try:
            config = SHEET_CONFIGS["Dashboard"]
            worksheet = self.get_or_create_worksheet("Dashboard", config["rows"], config["cols"])

            # Clear and set up dashboard structure
            worksheet.clear()

            # Title and instructions
            worksheet.update('A1', 'RoW Bot Dashboard')
            worksheet.update('A2', 'Select Player:')
            worksheet.update('A3', 'Player Stats will appear below')

            # Format headers
            worksheet.format('A1', {
                'textFormat': {'bold': True, 'fontSize': 16},
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 1.0}
            })

            # Add dropdown for player selection (Note: Requires manual setup in Sheets)
            worksheet.update('B2', 'Please add Data Validation dropdown manually pointing to Player Stats column A')

            # Stats display area
            stats_headers = ['Team', 'Wins', 'Losses', 'Win Rate', 'Total Events']
            for i, header in enumerate(stats_headers):
                worksheet.update_cell(5, i+1, header)

            # Chart placeholder
            worksheet.update('A15', 'Charts can be added manually using Insert > Chart')
            worksheet.update('A16', 'Suggested: Bar chart showing wins/losses per team')
            worksheet.update('A17', 'Suggested: Pie chart showing team participation distribution')

            logger.info("✅ Created dashboard template")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create dashboard: {e}")
            return False

    def create_all_templates(self, all_data):
        """Create all sheet templates for manual data entry."""
        if not self.is_connected():
            logger.warning("Google Sheets not initialized, skipping template creation")
            return False

        try:
            success_count = 0

            # Create current teams template
            if self.sync_current_teams(all_data.get("events", {})):
                success_count += 1

            # Create player stats template
            if self.create_player_stats_template(all_data.get("player_stats", {})):
                success_count += 1

            # Create results history template
            if self.sync_results_history(all_data.get("results", {})):
                success_count += 1

            # Create match statistics template
            if self.create_match_statistics_template():
                success_count += 1

            # Create alliance tracking template
            if self.create_alliance_tracking_sheet():
                success_count += 1

            # Create dashboard
            if self.create_dashboard():
                success_count += 1

            logger.info(f"✅ Template creation completed: {success_count}/6 operations successful")
            return success_count >= 4  # Consider successful if most operations work

        except Exception as e:
            logger.error(f"❌ Failed to create templates: {e}")
            return False

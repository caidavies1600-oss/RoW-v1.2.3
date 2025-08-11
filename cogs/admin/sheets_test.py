import discord
from discord.ext import commands

from config.constants import ADMIN_ROLE_IDS
from utils.logger import setup_logger

logger = setup_logger("sheets_test")


class SheetsTest(commands.Cog):
    """
    Commands to test Google Sheets integration.

    Features:
    - Connection testing and diagnostics
    - Template creation and verification
    - Sheet management and cleanup
    - Player Stats sheet repair
    """

    def __init__(self, bot):
        """
        Initialize the SheetsTest cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot

    @commands.command(name="sheetstest")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def test_sheets_connection(self, ctx):
        """
        Test Google Sheets connection and basic functionality.

        Args:
            ctx: Command context

        Tests:
            - Sheets connection status
            - Template creation
            - Worksheet listing
            - Basic data operations
        """
        try:
            await ctx.send("🔄 Testing Google Sheets connection...")

            # Try to import and initialize sheets manager
            try:
                # Use the bot's sheets manager or create new one
                if hasattr(self.bot, "sheets") and self.bot.sheets:
                    sheets_manager = self.bot.sheets
                else:
                    from sheets import SheetsManager

                    sheets_manager = SheetsManager()
                    self.bot.sheets = sheets_manager

                if not sheets_manager.is_connected():
                    await ctx.send(
                        "❌ Google Sheets connection failed. Check credentials and environment variables."
                    )
                    return

                embed = discord.Embed(
                    title="✅ Google Sheets Connection Test",
                    description="Successfully connected to Google Sheets!",
                    color=discord.Color.green(),
                )

                # Test basic operations
                if sheets_manager.spreadsheet:
                    embed.add_field(
                        name="📊 Spreadsheet Info",
                        value=f"**URL:** [Open Spreadsheet]({sheets_manager.spreadsheet.url})\n**ID:** {sheets_manager.spreadsheet.id}",
                        inline=False,
                    )

                    # List existing worksheets
                    worksheets = sheets_manager.spreadsheet.worksheets()
                    worksheet_names = [ws.title for ws in worksheets]
                    embed.add_field(
                        name="📋 Existing Worksheets",
                        value=", ".join(worksheet_names) if worksheet_names else "None",
                        inline=False,
                    )

                # Test template creation
                try:
                    test_data = {
                        "events": {
                            "main_team": ["TestUser1", "TestUser2"],
                            "team_2": [],
                            "team_3": [],
                        },
                        "player_stats": {
                            "123456789": {
                                "name": "TestPlayer",
                                "power_rating": 50000000,
                            }
                        },
                        "results": {"total_wins": 5, "total_losses": 3, "history": []},
                        "notification_preferences": {
                            "users": {},
                            "default_settings": {},
                        },
                    }

                    success = sheets_manager.create_all_templates(test_data)
                    if success:
                        embed.add_field(
                            name="🔧 Template Creation",
                            value="✅ All templates created successfully",
                            inline=False,
                        )
                    else:
                        embed.add_field(
                            name="🔧 Template Creation",
                            value="⚠️ Some templates may have failed. Check logs.",
                            inline=False,
                        )

                except Exception as e:
                    embed.add_field(
                        name="🔧 Template Creation",
                        value=f"❌ Template creation failed: {str(e)[:100]}",
                        inline=False,
                    )

                embed.set_footer(
                    text="Use this spreadsheet to manually enter player power ratings and match data"
                )
                await ctx.send(embed=embed)

            except ImportError as e:
                await ctx.send(f"❌ Failed to import sheets module: {e}")
            except Exception as e:
                await ctx.send(f"❌ Sheets connection error: {e}")
                logger.exception("Sheets test failed")

        except Exception as e:
            await ctx.send(f"❌ Test command failed: {e}")
            logger.exception("Sheets test command failed")

    @commands.command(name="validatecreds")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def validate_credentials(self, ctx):
        """
        Validate Google Sheets credentials for debugging connection issues.
        
        This command performs comprehensive validation of:
        - Environment variable presence and format
        - JSON credential structure and required fields
        - Service account authentication
        - Google Sheets API access
        - Specific spreadsheet permissions
        
        Args:
            ctx: Command context

        Returns:
            Detailed validation report
        """
        try:
            import os
            import json
            from datetime import datetime
            
            embed = discord.Embed(
                title="🔐 Google Sheets Credentials Validation",
                color=discord.Color.blue()
            )
            
            # Check if credentials exist
            creds_env = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            sheets_id = os.getenv("GOOGLE_SHEETS_ID")
            
            if not creds_env:
                embed.add_field(
                    name="❌ GOOGLE_SHEETS_CREDENTIALS",
                    value="Environment variable not found",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ GOOGLE_SHEETS_CREDENTIALS", 
                    value=f"Found ({len(creds_env)} characters)",
                    inline=False
                )
                
                # Try to parse JSON
                try:
                    creds_data = json.loads(creds_env)
                    embed.add_field(
                        name="✅ JSON Format",
                        value="Valid JSON structure",
                        inline=True
                    )
                    
                    # Check required fields
                    required_fields = [
                        "type", "project_id", "private_key_id", "private_key", 
                        "client_email", "client_id", "auth_uri", "token_uri"
                    ]
                    
                    missing_fields = [field for field in required_fields if field not in creds_data]
                    
                    if missing_fields:
                        embed.add_field(
                            name="❌ Missing Fields",
                            value=f"Missing: {', '.join(missing_fields)}",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="✅ Required Fields",
                            value="All required fields present",
                            inline=True
                        )
                    
                    # Check credential type
                    cred_type = creds_data.get("type", "unknown")
                    if cred_type == "service_account":
                        embed.add_field(
                            name="✅ Credential Type",
                            value="Service Account (correct)",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="❌ Credential Type",
                            value=f"{cred_type} (needs 'service_account')",
                            inline=True
                        )
                    
                    # Show service account email (safely)
                    if "client_email" in creds_data:
                        email = creds_data["client_email"]
                        safe_email = email[:10] + "..." + email[-20:] if len(email) > 30 else email
                        embed.add_field(
                            name="📧 Service Account",
                            value=safe_email,
                            inline=False
                        )
                        
                except json.JSONDecodeError as e:
                    embed.add_field(
                        name="❌ JSON Format",
                        value=f"Invalid JSON: {str(e)[:100]}",
                        inline=False
                    )
            
            if not sheets_id:
                embed.add_field(
                    name="❌ GOOGLE_SHEETS_ID",
                    value="Environment variable not found",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ GOOGLE_SHEETS_ID",
                    value=f"Found (ID: {sheets_id[:10]}...)",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Validation failed: {str(e)}")gs:
            ctx: Command context

        Returns:
            Detailed validation report
        """
        try:
            import os
            import json
            
            embed = discord.Embed(
                title="🔐 Google Sheets Credentials Validation",
                color=discord.Color.blue()
            )
            
            # Check if credentials exist
            creds_env = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            sheets_id = os.getenv("GOOGLE_SHEETS_ID")
            
            if not creds_env:
                embed.add_field(
                    name="❌ GOOGLE_SHEETS_CREDENTIALS",
                    value="Environment variable not found",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ GOOGLE_SHEETS_CREDENTIALS", 
                    value=f"Found ({len(creds_env)} characters)",
                    inline=False
                )
                
                # Try to parse JSON
                try:
                    creds_data = json.loads(creds_env)
                    embed.add_field(
                        name="✅ JSON Format",
                        value="Valid JSON structure",
                        inline=True
                    )
                    
                    # Check required fields
                    required_fields = [
                        "type", "project_id", "private_key_id", "private_key", 
                        "client_email", "client_id", "auth_uri", "token_uri"
                    ]
                    
                    missing_fields = [field for field in required_fields if field not in creds_data]
                    
                    if missing_fields:
                        embed.add_field(
                            name="❌ Missing Fields",
                            value=f"Missing: {', '.join(missing_fields)}",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="✅ Required Fields",
                            value="All required fields present",
                            inline=True
                        )
                    
                    # Check credential type
                    cred_type = creds_data.get("type", "unknown")
                    if cred_type == "service_account":
                        embed.add_field(
                            name="✅ Credential Type",
                            value="Service Account (correct)",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="❌ Credential Type",
                            value=f"{cred_type} (needs 'service_account')",
                            inline=True
                        )
                    
                    # Show service account email (safely)
                    if "client_email" in creds_data:
                        email = creds_data["client_email"]
                        safe_email = email[:10] + "..." + email[-20:] if len(email) > 30 else email
                        embed.add_field(
                            name="📧 Service Account",
                            value=safe_email,
                            inline=False
                        )
                        
                except json.JSONDecodeError as e:
                    embed.add_field(
                        name="❌ JSON Format",
                        value=f"Invalid JSON: {str(e)[:100]}",
                        inline=False
                    )
            
            if not sheets_id:
                embed.add_field(
                    name="❌ GOOGLE_SHEETS_ID",
                    value="Environment variable not found",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ GOOGLE_SHEETS_ID",
                    value=f"Found (ID: {sheets_id[:10]}...)",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Validation failed: {str(e)}")

    @commands.command(name="sheetsurl")
    @commands.has_any_role(*ADMIN_ROLE_IDS)  
    async def get_sheets_url(self, ctx):
        """
        Get the URL of the connected Google Sheets.

        Args:
            ctx: Command context

        Returns:
            Embedded message with spreadsheet URL and ID
        """
        try:
            from sheets.data_sync import DataSync

            sheets_manager = DataSync()

            if not sheets_manager.is_connected():
                await ctx.send("❌ Google Sheets not connected.")
                return

            if sheets_manager.spreadsheet:
                embed = discord.Embed(
                    title="📊 Google Sheets",
                    description=f"[📊 Open Spreadsheet]({sheets_manager.spreadsheet.url})",
                    color=discord.Color.blue(),
                )
                embed.add_field(
                    name="ID", value=sheets_manager.spreadsheet.id, inline=False
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No spreadsheet found.")

        except Exception as e:
            await ctx.send(f"❌ Error getting sheets URL: {e}")

    @commands.command(name="fixplayerstats")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def fix_player_stats_sheet(self, ctx):
        """
        Fix the broken Player Stats sheet with correct headers and alignment.

        Args:
            ctx: Command context

        Actions:
            - Clears existing data
            - Adds correct headers
            - Sets up formulas
            - Applies formatting
            - Adds example data
        """
        try:
            from sheets.enhanced_sheets_manager import EnhancedSheetsManager

            manager = EnhancedSheetsManager()

            if not manager.is_connected():
                await ctx.send("❌ Not connected to Google Sheets")
                return

            # Get the worksheet
            try:
                worksheet = manager.spreadsheet.worksheet("Player Stats")

                # Clear everything and start fresh
                worksheet.clear()

                # Add correct headers
                headers = [
                    "User ID",
                    "Display Name",
                    "Main Team Role",
                    "Main Wins",
                    "Main Losses",
                    "Team2 Wins",
                    "Team2 Losses",
                    "Team3 Wins",
                    "Team3 Losses",
                    "Total Wins",
                    "Total Losses",
                    "Win Rate",
                    "Absents",
                    "Blocked",
                    "Power Rating",
                    "Cavalry",
                    "Mages",
                    "Archers",
                    "Infantry",
                    "Whale Status",
                    "Last Updated",
                ]
                worksheet.append_row(headers)

                # Add example player data with proper alignment
                example_players = [
                    [
                        "123456789012345678",  # User ID
                        "Example Player 1",  # Display Name
                        "Yes",  # Main Team Role
                        5,
                        3,  # Main Wins/Losses
                        2,
                        1,  # Team2 Wins/Losses
                        0,
                        0,  # Team3 Wins/Losses
                        "=D2+F2+H2",  # Total Wins (formula)
                        "=E2+G2+I2",  # Total Losses (formula)
                        "=IF(K2+J2=0,0,J2/(J2+K2))",  # Win Rate (formula)
                        1,  # Absents
                        "No",  # Blocked
                        "125000000",  # Power Rating
                        "Yes",
                        "No",
                        "Yes",
                        "No",
                        "Yes",  # Specializations
                        "2025-08-10 12:00 UTC",  # Last Updated
                    ],
                    [
                        "987654321098765432",  # User ID
                        "Example Player 2",  # Display Name
                        "No",  # Main Team Role
                        3,
                        4,  # Main Wins/Losses
                        8,
                        2,  # Team2 Wins/Losses
                        1,
                        1,  # Team3 Wins/Losses
                        "=D3+F3+H3",  # Total Wins
                        "=E3+G3+I3",  # Total Losses
                        "=IF(K3+J3=0,0,J3/(J3+K3))",  # Win Rate
                        0,  # Absents
                        "No",  # Blocked
                        "89000000",  # Power Rating
                        "No",
                        "Yes",
                        "No",
                        "Yes",
                        "No",  # Specializations
                        "2025-08-10 12:00 UTC",  # Last Updated
                    ],
                ]

                for row in example_players:
                    worksheet.append_row(row)

                # Format headers with color and bold
                worksheet.format(
                    "A1:U1",
                    {
                        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    },
                )

                # Freeze header row
                worksheet.freeze(rows=1)

                embed = discord.Embed(
                    title="✅ Player Stats Sheet Fixed!",
                    description="Cleared broken data and created proper template with correct headers",
                    color=0x00FF00,
                )

                embed.add_field(
                    name="📋 What was fixed:",
                    value="• Proper column alignment\n• Correct headers\n• Formula columns for totals\n• Example data format\n• Header formatting",
                    inline=False,
                )

                embed.add_field(
                    name="📝 Next steps:",
                    value="Fill in real player data manually in the spreadsheet",
                    inline=False,
                )

                url = manager.get_spreadsheet_url()
                embed.add_field(
                    name="🔗 Spreadsheet",
                    value=f"[Open Player Stats]({url})",
                    inline=False,
                )

                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ Error fixing sheet: {e}")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            logger.exception("Failed to fix player stats sheet")

    @commands.command(name="clearsheet")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def clear_sheet(self, ctx, sheet_name: str):
        """
        Clear a specific sheet completely.

        Args:
            ctx: Command context
            sheet_name: Name of the sheet to clear

        Requires:
            Confirmation via reaction
        """
        try:
            from sheets.enhanced_sheets_manager import EnhancedSheetsManager

            manager = EnhancedSheetsManager()

            if not manager.is_connected():
                await ctx.send("❌ Not connected to Google Sheets")
                return

            # Confirm before clearing
            embed = discord.Embed(
                title="⚠️ Confirm Sheet Clear",
                description=f"Are you sure you want to clear the **{sheet_name}** sheet?\nThis will delete ALL data in that sheet!",
                color=0xFF0000,
            )

            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return (
                    user == ctx.author
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                if str(reaction.emoji) == "✅":
                    worksheet = manager.spreadsheet.worksheet(sheet_name)
                    worksheet.clear()
                    await ctx.send(f"✅ Cleared sheet: **{sheet_name}**")
                else:
                    await ctx.send("❌ Cancelled sheet clear")

            except Exception as e:
                await ctx.send(f"❌ Error clearing sheet: {e}")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="sheetsdiag")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def sheets_diagnostics(self, ctx):
        """
        Run comprehensive Google Sheets integration diagnostics.

        Args:
            ctx: Command context

        Checks:
            - Environment variables
            - Bot sheets manager
            - Module imports
            - Connection status
            - Provides recommendations
        """
        try:
            embed = discord.Embed(
                title="🔍 Google Sheets Diagnostics", color=discord.Color.blue()
            )

            # Check environment variables
            import os

            creds_exists = bool(os.getenv("GOOGLE_SHEETS_CREDENTIALS"))
            sheets_id_exists = bool(os.getenv("GOOGLE_SHEETS_ID"))

            env_status = (
                "✅ Complete"
                if (creds_exists and sheets_id_exists)
                else "❌ Incomplete"
            )
            embed.add_field(
                name="🔐 Environment Variables",
                value=f"**Status:** {env_status}\n**Credentials:** {'✅' if creds_exists else '❌'}\n**Sheet ID:** {'✅' if sheets_id_exists else '❌'}",
                inline=False,
            )

            # Check bot's sheets manager
            bot_sheets_status = (
                "✅ Available"
                if hasattr(self.bot, "sheets") and self.bot.sheets
                else "❌ Not Available"
            )
            embed.add_field(
                name="🤖 Bot Sheets Manager",
                value=f"**Status:** {bot_sheets_status}",
                inline=True,
            )

            # Test manual import
            try:
                from sheets import SheetsManager

                import_status = "✅ Success"
            except Exception as e:
                import_status = f"❌ Failed: {e}"

            embed.add_field(
                name="📦 Module Import",
                value=f"**Status:** {import_status}",
                inline=True,
            )

            # Test connection if possible
            if creds_exists and sheets_id_exists:
                try:
                    from sheets import SheetsManager

                    test_manager = SheetsManager()
                    if test_manager.is_connected():
                        connection_status = "✅ Connected"
                        if test_manager.spreadsheet:
                            connection_status += (
                                f"\n**URL:** [Open]({test_manager.spreadsheet.url})"
                            )
                    else:
                        connection_status = "❌ Failed to connect"
                except Exception as e:
                    connection_status = f"❌ Error: {e}"
            else:
                connection_status = "⚠️ Cannot test (missing credentials)"

            embed.add_field(
                name="🔗 Connection Test", value=connection_status, inline=False
            )

            # Recommendations
            recommendations = []
            if not creds_exists:
                recommendations.append("• Add GOOGLE_SHEETS_CREDENTIALS to Secrets")
            if not sheets_id_exists:
                recommendations.append("• Add GOOGLE_SHEETS_ID to Secrets")
            if not (hasattr(self.bot, "sheets") and self.bot.sheets):
                recommendations.append("• Restart bot to initialize sheets manager")

            if recommendations:
                embed.add_field(
                    name="💡 Recommendations",
                    value="\n".join(recommendations),
                    inline=False,
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="All checks passed! Sheets integration should be working.",
                    inline=False,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.exception("Error in sheets diagnostics")
            await ctx.send(f"❌ **Diagnostics error:** {e}")


async def setup(bot):
    """
    Set up the SheetsTest cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(SheetsTest(bot))

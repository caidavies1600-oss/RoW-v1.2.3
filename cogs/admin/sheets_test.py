import discord
from discord.ext import commands
from config.constants import ADMIN_ROLE_IDS
from utils.logger import setup_logger

logger = setup_logger("sheets_test")

class SheetsTest(commands.Cog):
    """Commands to test Google Sheets integration."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="sheetstest")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def test_sheets_connection(self, ctx):
        """Test Google Sheets connection and basic functionality."""
        try:
            await ctx.send("🔄 Testing Google Sheets connection...")

            # Try to import and initialize sheets manager
            try:
                from sheets.data_sync import DataSync
                sheets_manager = DataSync()

                if not sheets_manager.is_connected():
                    await ctx.send("❌ Google Sheets connection failed. Check credentials and environment variables.")
                    return

                embed = discord.Embed(
                    title="✅ Google Sheets Connection Test",
                    description="Successfully connected to Google Sheets!",
                    color=discord.Color.green()
                )

                # Test basic operations
                if sheets_manager.spreadsheet:
                    embed.add_field(
                        name="📊 Spreadsheet Info",
                        value=f"**URL:** [Open Spreadsheet]({sheets_manager.spreadsheet.url})\n**ID:** {sheets_manager.spreadsheet.id}",
                        inline=False
                    )

                    # List existing worksheets
                    worksheets = sheets_manager.spreadsheet.worksheets()
                    worksheet_names = [ws.title for ws in worksheets]
                    embed.add_field(
                        name="📋 Existing Worksheets",
                        value=", ".join(worksheet_names) if worksheet_names else "None",
                        inline=False
                    )

                # Test template creation
                try:
                    test_data = {
                        "events": {"main_team": ["TestUser1", "TestUser2"], "team_2": [], "team_3": []},
                        "player_stats": {
                            "123456789": {"name": "TestPlayer", "power_rating": 50000000}
                        },
                        "results": {"total_wins": 5, "total_losses": 3, "history": []},
                        "notification_preferences": {"users": {}, "default_settings": {}}
                    }

                    success = sheets_manager.create_all_templates(test_data)
                    if success:
                        embed.add_field(
                            name="🔧 Template Creation",
                            value="✅ All templates created successfully",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🔧 Template Creation",
                            value="⚠️ Some templates may have failed. Check logs.",
                            inline=False
                        )

                except Exception as e:
                    embed.add_field(
                        name="🔧 Template Creation",
                        value=f"❌ Template creation failed: {str(e)[:100]}",
                        inline=False
                    )

                embed.set_footer(text="Use this spreadsheet to manually enter player power ratings and match data")
                await ctx.send(embed=embed)

            except ImportError as e:
                await ctx.send(f"❌ Failed to import sheets module: {e}")
            except Exception as e:
                await ctx.send(f"❌ Sheets connection error: {e}")
                logger.exception("Sheets test failed")

        except Exception as e:
            await ctx.send(f"❌ Test command failed: {e}")
            logger.exception("Sheets test command failed")

    @commands.command(name="sheetsurl")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def get_sheets_url(self, ctx):
        """Get the URL of the connected Google Sheets."""
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
                    color=discord.Color.blue()
                )
                embed.add_field(name="ID", value=sheets_manager.spreadsheet.id, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No spreadsheet found.")

        except Exception as e:
            await ctx.send(f"❌ Error getting sheets URL: {e}")
            
@commands.command(name="fixplayerstats")
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def fix_player_stats_sheet(self, ctx):
    """Fix the broken Player Stats sheet with correct headers and alignment."""
    try:
        from sheets import SheetsManager
        manager = SheetsManager()

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
                "User ID", "Display Name", "Main Team Role", 
                "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
                "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses", 
                "Win Rate", "Absents", "Blocked", "Power Rating", 
                "Cavalry", "Mages", "Archers", "Infantry", "Whale Status", "Last Updated"
            ]
            worksheet.append_row(headers)

            # Add example player data with proper alignment
            example_players = [
                [
                    "123456789012345678",      # User ID
                    "Example Player 1",        # Display Name
                    "Yes",                     # Main Team Role
                    5, 3,                      # Main Wins/Losses
                    2, 1,                      # Team2 Wins/Losses  
                    0, 0,                      # Team3 Wins/Losses
                    "=D2+F2+H2",              # Total Wins (formula)
                    "=E2+G2+I2",              # Total Losses (formula)
                    "=IF(K2+J2=0,0,J2/(J2+K2))", # Win Rate (formula)
                    1,                         # Absents
                    "No",                      # Blocked
                    "125000000",               # Power Rating
                    "Yes", "No", "Yes", "No", "Yes",  # Specializations
                    "2025-08-10 12:00 UTC"    # Last Updated
                ],
                [
                    "987654321098765432",      # User ID
                    "Example Player 2",        # Display Name
                    "No",                      # Main Team Role
                    3, 4,                      # Main Wins/Losses
                    8, 2,                      # Team2 Wins/Losses
                    1, 1,                      # Team3 Wins/Losses
                    "=D3+F3+H3",              # Total Wins
                    "=E3+G3+I3",              # Total Losses
                    "=IF(K3+J3=0,0,J3/(J3+K3))", # Win Rate
                    0,                         # Absents
                    "No",                      # Blocked
                    "89000000",                # Power Rating
                    "No", "Yes", "No", "Yes", "No",  # Specializations
                    "2025-08-10 12:00 UTC"    # Last Updated
                ]
            ]

            for row in example_players:
                worksheet.append_row(row)

            # Format headers with color and bold
            worksheet.format("A1:U1", {
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
            })

            # Freeze header row
            worksheet.freeze(rows=1)

            embed = discord.Embed(
                title="✅ Player Stats Sheet Fixed!",
                description="Cleared broken data and created proper template with correct headers",
                color=0x00ff00
            )

            embed.add_field(
                name="📋 What was fixed:",
                value="• Proper column alignment\n• Correct headers\n• Formula columns for totals\n• Example data format\n• Header formatting",
                inline=False
            )

            embed.add_field(
                name="📝 Next steps:",
                value="Fill in real player data manually in the spreadsheet",
                inline=False
            )

            url = manager.get_spreadsheet_url()
            embed.add_field(name="🔗 Spreadsheet", value=f"[Open Player Stats]({url})", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error fixing sheet: {e}")

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        logger.exception("Failed to fix player stats sheet")

@commands.command(name="clearsheet")
@commands.has_any_role(*ADMIN_ROLE_IDS)
async def clear_sheet(self, ctx, sheet_name: str):
    """Clear a specific sheet completely."""
    try:
        from sheets import SheetsManager
        manager = SheetsManager()

        if not manager.is_connected():
            await ctx.send("❌ Not connected to Google Sheets")
            return

        # Confirm before clearing
        embed = discord.Embed(
            title="⚠️ Confirm Sheet Clear",
            description=f"Are you sure you want to clear the **{sheet_name}** sheet?\nThis will delete ALL data in that sheet!",
            color=0xff0000
        )

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)

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
        
async def setup(bot):
    await bot.add_cog(SheetsTest(bot))
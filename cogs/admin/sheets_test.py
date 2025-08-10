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
                from sheets import SheetsManager
                sheets_manager = SheetsManager()

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
            from sheets import SheetsManager
            sheets_manager = SheetsManager()

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

async def setup(bot):
    await bot.add_cog(SheetsTest(bot))
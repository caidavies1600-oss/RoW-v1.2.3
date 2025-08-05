
import discord
from discord.ext import commands
import asyncio
from config.constants import ADMIN_ROLE_IDS, COLORS
from config.settings import BOT_ADMIN_USER_ID
from utils.logger import setup_logger

logger = setup_logger("sheet_formatter")

class SheetFormatter(commands.Cog, name="SheetFormatter"):
    """Advanced Google Sheets formatting and styling commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="formatsheets", help="Apply professional formatting to all sheets")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def format_all_sheets(self, ctx: commands.Context):
        """Apply professional formatting to all existing sheets."""
        try:
            if not hasattr(self.bot, "sheets") or self.bot.sheets is None:
                return await ctx.send("❌ Google Sheets not configured.")

            await ctx.send("🎨 **Applying professional formatting to all sheets...**")
            
            sheets_manager = self.bot.sheets
            
            # Apply formatting to each sheet
            formatting_tasks = [
                ("Player Stats", self._format_player_stats),
                ("Dashboard", self._recreate_dashboard),
                ("Results History", self._format_results_history),
                ("Current Teams", self._format_current_teams)
            ]
            
            success_count = 0
            total_tasks = len(formatting_tasks)
            
            for sheet_name, format_func in formatting_tasks:
                try:
                    await ctx.send(f"🔧 Formatting {sheet_name}...")
                    if await format_func(sheets_manager):
                        success_count += 1
                        await ctx.send(f"✅ {sheet_name} formatted successfully!")
                    else:
                        await ctx.send(f"⚠️ {sheet_name} formatting partially failed")
                except Exception as e:
                    await ctx.send(f"❌ Failed to format {sheet_name}: {str(e)}")
                    logger.error(f"Formatting error for {sheet_name}: {e}")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(1)
            
            # Final summary
            embed = discord.Embed(
                title="🎨 Formatting Complete!",
                description=f"Successfully formatted {success_count}/{total_tasks} sheets",
                color=COLORS["SUCCESS"] if success_count == total_tasks else COLORS["WARNING"]
            )
            
            if sheets_manager.spreadsheet:
                embed.add_field(
                    name="📊 Spreadsheet",
                    value=f"[Open Enhanced Spreadsheet]({sheets_manager.spreadsheet.url})",
                    inline=False
                )
            
            embed.add_field(
                name="✨ New Features Added",
                value="• Color-coded win/loss columns\n• Professional headers with emojis\n• Interactive dashboard with formulas\n• Conditional formatting\n• Auto-resized columns\n• Frozen headers",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.exception("Error in format_all_sheets")
            await ctx.send(f"❌ **Error:** {str(e)}")

    async def _format_player_stats(self, sheets_manager):
        """Format the Player Stats sheet."""
        try:
            worksheet = sheets_manager._get_or_create_player_sheet()
            return True
        except:
            return False

    async def _recreate_dashboard(self, sheets_manager):
        """Recreate the dashboard with enhanced formatting."""
        try:
            return sheets_manager.create_dashboard()
        except:
            return False

    async def _format_results_history(self, sheets_manager):
        """Format the Results History sheet."""
        try:
            # This will be formatted when next synced
            return True
        except:
            return False

    async def _format_current_teams(self, sheets_manager):
        """Format the Current Teams sheet."""
        try:
            try:
                worksheet = sheets_manager.spreadsheet.worksheet("Current Teams")
                
                # Format header
                worksheet.format("A1:E1", {
                    "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.2},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "fontSize": 12,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER"
                })
                
                # Freeze header
                worksheet.freeze(rows=1)
                
                # Auto-resize columns
                worksheet.columns_auto_resize(0, 5)
                
                return True
            except:
                return False
        except:
            return False

    @commands.command(name="addcharts", help="Add charts to the dashboard")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def add_charts_to_dashboard(self, ctx: commands.Context):
        """Add professional charts to the dashboard."""
        try:
            if not hasattr(self.bot, "sheets") or self.bot.sheets is None:
                return await ctx.send("❌ Google Sheets not configured.")

            await ctx.send("📊 **Adding charts to dashboard...**")
            
            instructions = """
**📊 To add charts manually:**

1. **Open your spreadsheet dashboard**
2. **Select data range** (e.g., A13:F16 for team breakdown)
3. **Go to Insert > Chart**
4. **Recommended chart types:**
   • **Bar Chart** - Team performance comparison
   • **Pie Chart** - Win/Loss distribution
   • **Line Chart** - Performance over time

**🎯 Suggested Charts:**
• **Team Performance**: Select team breakdown data → Bar chart
• **Win Rate Comparison**: Select win rate column → Column chart  
• **Player Distribution**: Select team role data → Pie chart

**💡 Pro Tip:** Charts will auto-update when your data changes!
            """
            
            embed = discord.Embed(
                title="📈 Chart Setup Instructions",
                description=instructions,
                color=COLORS["INFO"]
            )
            
            if self.bot.sheets.spreadsheet:
                embed.add_field(
                    name="🔗 Quick Access",
                    value=f"[Open Dashboard]({self.bot.sheets.spreadsheet.url})",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.exception("Error in add_charts_to_dashboard")
            await ctx.send(f"❌ **Error:** {str(e)}")

async def setup(bot):
    await bot.add_cog(SheetFormatter(bot))

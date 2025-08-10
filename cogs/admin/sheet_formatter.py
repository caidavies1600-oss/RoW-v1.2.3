import discord
from discord.ext import commands
from config.constants import ADMIN_ROLE_IDS, COLORS
from utils.logger import setup_logger
from utils.data_manager import DataManager
import asyncio
import time

logger = setup_logger("sheet_formatter")

class SheetFormatter(commands.Cog):
    """Advanced Google Sheets formatting commands."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

    @commands.command(name="formatsheets")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def format_all_sheets(self, ctx):
        """Apply comprehensive formatting to all Google Sheets."""
        await ctx.send("🔍 **Debug:** Starting formatsheets command...")

        try:
            # Check if bot has sheets manager
            await ctx.send(f"🔍 **Debug:** Checking bot.sheets attribute... hasattr: {hasattr(self.bot, 'sheets')}")

            if not hasattr(self.bot, 'sheets'):
                await ctx.send("❌ **Error:** Bot has no 'sheets' attribute.")
                return

            await ctx.send(f"🔍 **Debug:** Bot.sheets exists: {self.bot.sheets is not None}")
            await ctx.send(f"🔍 **Debug:** Bot.sheets type: {type(self.bot.sheets)}")

            if not self.bot.sheets:
                await ctx.send("❌ **Error:** Google Sheets not initialized (sheets is None).")
                return

            sheets_manager = self.bot.sheets

            await ctx.send(f"🔍 **Debug:** Checking connection... has is_connected method: {hasattr(sheets_manager, 'is_connected')}")

            if hasattr(sheets_manager, 'is_connected'):
                is_connected = sheets_manager.is_connected()
                await ctx.send(f"🔍 **Debug:** sheets_manager.is_connected() returned: {is_connected}")

                if not is_connected:
                    await ctx.send("❌ **Error:** Google Sheets not connected.")
                    return
            else:
                await ctx.send("⚠️ **Warning:** sheets_manager has no is_connected method, continuing anyway...")

            # Check data manager
            await ctx.send(f"🔍 **Debug:** Checking data_manager... hasattr: {hasattr(self.bot, 'data_manager')}")

            if not hasattr(self.bot, 'data_manager'):
                await ctx.send("❌ **Error:** Bot has no data_manager attribute.")
                return

            # Load data with debug info
            await ctx.send("🔍 **Debug:** Loading all data from data_manager...")
            try:
                all_data = self.bot.data_manager.load_all_data_from_sheets()
                await ctx.send(f"🔍 **Debug:** Data loaded successfully. Keys: {list(all_data.keys())}")
                await ctx.send(f"🔍 **Debug:** Player stats count: {len(all_data.get('player_stats', {}))}")
                await ctx.send(f"🔍 **Debug:** Events data keys: {list(all_data.get('events', {}).keys())}")
                await ctx.send(f"🔍 **Debug:** Results data keys: {list(all_data.get('results', {}).keys())}")
            except Exception as data_error:
                await ctx.send(f"❌ **Error loading data:** {data_error}")
                return

            # Check available methods on sheets_manager
            methods_to_check = [
                'create_player_stats_template',
                'sync_current_teams',
                'sync_results_history',
                'create_match_statistics_template',
                'create_alliance_tracking_sheet'
            ]

            available_methods = []
            for method_name in methods_to_check:
                if hasattr(sheets_manager, method_name):
                    available_methods.append(f"✅ {method_name}")
                else:
                    available_methods.append(f"❌ {method_name}")

            await ctx.send(f"🔍 **Debug:** Available methods:\n" + "\n".join(available_methods))

            # Send initial message
            embed = discord.Embed(
                title="🎨 Formatting Google Sheets",
                description="Applying comprehensive formatting to all worksheets...",
                color=COLORS["INFO"]
            )
            message = await ctx.send(embed=embed)

            # Format each sheet with progress updates
            formatting_results = []

            # 1. Format Player Stats
            embed.add_field(name="📊 Player Stats", value="🔄 Formatting...", inline=False)
            await message.edit(embed=embed)

            try:
                await ctx.send("🔍 **Debug:** Calling create_player_stats_template...")
                await asyncio.sleep(0.5)  # Brief pause before operation
                success = sheets_manager.create_player_stats_template(all_data.get("player_stats", {}))
                await ctx.send(f"🔍 **Debug:** create_player_stats_template returned: {success}")
                time.sleep(2)  # Rate limiting between operations

                if success:
                    formatting_results.append("✅ Player Stats - Formatted with formulas, colors, and conditional formatting")
                    embed.set_field_at(-1, name="📊 Player Stats", value="✅ Complete", inline=False)
                else:
                    formatting_results.append("❌ Player Stats - Formatting failed")
                    embed.set_field_at(-1, name="📊 Player Stats", value="❌ Failed", inline=False)
                await message.edit(embed=embed)
            except Exception as e:
                logger.error(f"Player Stats formatting error: {e}")
                formatting_results.append(f"❌ Player Stats - Error: {str(e)[:50]}")
                embed.set_field_at(-1, name="📊 Player Stats", value="❌ Error", inline=False)
                await message.edit(embed=embed)

            # 2. Format Current Teams
            embed.add_field(name="👥 Current Teams", value="🔄 Formatting...", inline=False)
            await message.edit(embed=embed)

            try:
                await ctx.send("🔍 **Debug:** Calling sync_current_teams...")
                await asyncio.sleep(0.5)  # Brief pause before operation
                success = sheets_manager.sync_current_teams(all_data.get("events", {}))
                await ctx.send(f"🔍 **Debug:** sync_current_teams returned: {success}")
                time.sleep(2)  # Rate limiting between operations

                if success:
                    formatting_results.append("✅ Current Teams - Enhanced with status indicators and colors")
                    embed.set_field_at(-1, name="👥 Current Teams", value="✅ Complete", inline=False)
                else:
                    formatting_results.append("❌ Current Teams - Formatting failed")
                    embed.set_field_at(-1, name="👥 Current Teams", value="❌ Failed", inline=False)
                await message.edit(embed=embed)
            except Exception as e:
                logger.error(f"Current Teams formatting error: {e}")
                formatting_results.append(f"❌ Current Teams - Error: {str(e)[:50]}")
                embed.set_field_at(-1, name="👥 Current Teams", value="❌ Error", inline=False)
                await message.edit(embed=embed)

            # 3. Format Results History
            embed.add_field(name="📈 Results History", value="🔄 Formatting...", inline=False)
            await message.edit(embed=embed)

            try:
                await ctx.send("🔍 **Debug:** Calling sync_results_history...")
                await asyncio.sleep(0.5)  # Brief pause before operation
                success = sheets_manager.sync_results_history(all_data.get("results", {}))
                await ctx.send(f"🔍 **Debug:** sync_results_history returned: {success}")
                time.sleep(2)  # Rate limiting between operations

                if success:
                    formatting_results.append("✅ Results History - Win/Loss color coding and enhanced display")
                    embed.set_field_at(-1, name="📈 Results History", value="✅ Complete", inline=False)
                else:
                    formatting_results.append("❌ Results History - Formatting failed")
                    embed.set_field_at(-1, name="📈 Results History", value="❌ Failed", inline=False)
                await message.edit(embed=embed)
            except Exception as e:
                logger.error(f"Results History formatting error: {e}")
                formatting_results.append(f"❌ Results History - Error: {str(e)[:50]}")
                embed.set_field_at(-1, name="📈 Results History", value="❌ Error", inline=False)
                await message.edit(embed=embed)

            # 4. Create Enhanced Templates
            embed.add_field(name="🏗️ Additional Templates", value="🔄 Creating...", inline=False)
            await message.edit(embed=embed)

            try:
                await ctx.send("🔍 **Debug:** Creating additional templates...")

                # Match Statistics template
                if hasattr(sheets_manager, 'create_match_statistics_template'):
                    await ctx.send("🔍 **Debug:** Calling create_match_statistics_template...")
                    match_success = sheets_manager.create_match_statistics_template()
                    await ctx.send(f"🔍 **Debug:** create_match_statistics_template returned: {match_success}")
                else:
                    match_success = False
                    await ctx.send("🔍 **Debug:** create_match_statistics_template method not available")

                # Alliance Tracking template
                if hasattr(sheets_manager, 'create_alliance_tracking_sheet'):
                    await ctx.send("🔍 **Debug:** Calling create_alliance_tracking_sheet...")
                    alliance_success = sheets_manager.create_alliance_tracking_sheet()
                    await ctx.send(f"🔍 **Debug:** create_alliance_tracking_sheet returned: {alliance_success}")
                else:
                    alliance_success = False
                    await ctx.send("🔍 **Debug:** create_alliance_tracking_sheet method not available")

                # Error Summary template
                if hasattr(sheets_manager, 'create_error_summary_template'):
                    await ctx.send("🔍 **Debug:** Calling create_error_summary_template...")
                    error_summary_success = sheets_manager.create_error_summary_template()
                    await ctx.send(f"🔍 **Debug:** create_error_summary_template returned: {error_summary_success}")
                else:
                    error_summary_success = False
                    await ctx.send("🔍 **Debug:** create_error_summary_template method not available")

                # Dashboard Summary template
                if hasattr(sheets_manager, 'create_dashboard_summary_template'):
                    await ctx.send("🔍 **Debug:** Calling create_dashboard_summary_template...")
                    dashboard_success = sheets_manager.create_dashboard_summary_template()
                    await ctx.send(f"🔍 **Debug:** create_dashboard_summary_template returned: {dashboard_success}")
                else:
                    dashboard_success = False
                    await ctx.send("🔍 **Debug:** create_dashboard_summary_template method not available")

                additional_status = "✅ Created" if match_success and alliance_success and error_summary_success and dashboard_success else "❌ Failed"
                
                if match_success and alliance_success and error_summary_success and dashboard_success:
                    formatting_results.append("✅ Additional Templates - Match Statistics, Alliance Tracking, Error Summary & Dashboard created")
                    embed.set_field_at(-1, name="🏗️ Additional Templates", value="✅ Complete", inline=False)
                elif match_success or alliance_success or error_summary_success or dashboard_success:
                    formatting_results.append("⚠️ Additional Templates - Partially created")
                    embed.set_field_at(-1, name="🏗️ Additional Templates", value="⚠️ Partial", inline=False)
                else:
                    formatting_results.append("❌ Additional Templates - Creation failed")
                    embed.set_field_at(-1, name="🏗️ Additional Templates", value="❌ Failed", inline=False)
                await message.edit(embed=embed)
            except Exception as e:
                formatting_results.append(f"❌ Additional Templates - Error: {str(e)[:50]}")
                embed.set_field_at(-1, name="🏗️ Additional Templates", value="❌ Error", inline=False)
                await message.edit(embed=embed)

            # Debug formatting results
            await ctx.send(f"🔍 **Debug:** Formatting results count: {len(formatting_results)}")
            await ctx.send(f"🔍 **Debug:** Results: {formatting_results}")

            # Final summary
            successful_operations = len([r for r in formatting_results if r.startswith("✅")])
            total_operations = len(formatting_results)

            await ctx.send(f"🔍 **Debug:** Successful operations: {successful_operations}/{total_operations}")

            # Create final embed
            final_embed = discord.Embed(
                title="🎨 Sheet Formatting Complete",
                description=f"**Success Rate:** {successful_operations}/{total_operations} operations completed",
                color=COLORS["SUCCESS"] if successful_operations >= total_operations // 2 else COLORS["WARNING"]
            )

            # Add spreadsheet link
            await ctx.send(f"🔍 **Debug:** Checking spreadsheet... exists: {hasattr(sheets_manager, 'spreadsheet') and sheets_manager.spreadsheet is not None}")

            if hasattr(sheets_manager, 'spreadsheet') and sheets_manager.spreadsheet:
                spreadsheet_url = getattr(sheets_manager.spreadsheet, 'url', 'URL not available')
                await ctx.send(f"🔍 **Debug:** Spreadsheet URL: {spreadsheet_url}")
                final_embed.add_field(
                    name="📊 Spreadsheet",
                    value=f"[🔗 Open Formatted Sheets]({spreadsheet_url})",
                    inline=False
                )
            else:
                await ctx.send("🔍 **Debug:** No spreadsheet object available")

            # Add results summary
            results_text = "\n".join(formatting_results)
            if len(results_text) > 1000:
                results_text = results_text[:1000] + "..."

            final_embed.add_field(
                name="📋 Detailed Results",
                value=results_text,
                inline=False
            )

            final_embed.add_field(
                name="✨ Applied Enhancements",
                value="• Professional color schemes\n• Conditional formatting for wins/losses\n• Emoji-enhanced headers\n• Frozen header rows\n• Auto-resized columns\n• Formula-based calculations\n• Status indicators",
                inline=False
            )

            final_embed.set_footer(text="All sheets now have professional formatting and enhanced functionality!")
            await message.edit(embed=final_embed)

            # Log API usage
            if hasattr(sheets_manager, 'log_usage_summary'):
                sheets_manager.log_usage_summary()

        except Exception as e:
            logger.exception("Error in format_all_sheets")
            await ctx.send(f"❌ **Formatting Error:** {str(e)}")
            await ctx.send(f"🔍 **Debug:** Exception type: {type(e).__name__}")
            await ctx.send(f"🔍 **Debug:** Exception details: {repr(e)}")

            # Additional debug info about the bot state
            try:
                await ctx.send(f"🔍 **Debug:** Bot guilds: {len(self.bot.guilds)}")
                await ctx.send(f"🔍 **Debug:** Bot user: {self.bot.user}")
                await ctx.send(f"🔍 **Debug:** Bot is ready: {self.bot.is_ready()}")
            except Exception as debug_error:
                await ctx.send(f"🔍 **Debug:** Could not get bot info: {debug_error}")

    @commands.command(name="resetformatting")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def reset_sheet_formatting(self, ctx):
        """Reset all sheet formatting to basic style."""
        try:
            if not hasattr(self.bot, 'sheets') or not self.bot.sheets:
                await ctx.send("❌ **Error:** Google Sheets not initialized.")
                return

            sheets_manager = self.bot.sheets

            if not sheets_manager.is_connected():
                await ctx.send("❌ **Error:** Google Sheets not connected.")
                return

            embed = discord.Embed(
                title="🔄 Resetting Sheet Formatting",
                description="Clearing all formatting and recreating basic sheets...",
                color=COLORS["INFO"]
            )
            message = await ctx.send(embed=embed)

            # Get all worksheets and clear formatting
            worksheets = sheets_manager.spreadsheet.worksheets()
            cleared_sheets = []

            for worksheet in worksheets:
                try:
                    # Clear all formatting but keep data
                    worksheet.format("1:1000", {
                        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "textFormat": {"bold": False, "fontSize": 10},
                        "borders": {"style": "NONE"}
                    })
                    cleared_sheets.append(f"✅ {worksheet.title}")
                except Exception as e:
                    cleared_sheets.append(f"❌ {worksheet.title} - {str(e)[:30]}")

            final_embed = discord.Embed(
                title="🔄 Formatting Reset Complete",
                description="All sheets have been reset to basic formatting.",
                color=COLORS["SUCCESS"]
            )

            final_embed.add_field(
                name="📋 Reset Results",
                value="\n".join(cleared_sheets),
                inline=False
            )

            final_embed.add_field(
                name="💡 Next Steps",
                value="Use `!formatsheets` to reapply professional formatting.",
                inline=False
            )

            await message.edit(embed=final_embed)

        except Exception as e:
            logger.exception("Error in reset_sheet_formatting")
            await ctx.send(f"❌ **Reset Error:** {str(e)}")

async def setup(bot):
    await bot.add_cog(SheetFormatter(bot))
import discord
from discord.ext import commands
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from config.constants import FILES, EMOJIS, COLORS
from config.settings import BOT_ADMIN_USER_ID
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("owner_actions")


class OwnerActions(commands.Cog):
    """Owner-only commands for bot maintenance and Google Sheets management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_manager = DataManager()

    def _is_owner(self, user_id: int) -> bool:
        """Check if user is the bot owner."""
        return user_id == BOT_ADMIN_USER_ID

    def _get_expected_structure(self, file_key: str) -> Any:
        """Get expected JSON structure for each file."""
        structures = {
            "EVENTS": {"main_team": [], "team_2": [], "team_3": []},
            "BLOCKED": {},
            "IGN_MAP": {},
            "RESULTS": {"total_wins": 0, "total_losses": 0, "history": []},
            "HISTORY": [],
            "TIMES": {
                "main_team": "14:00 UTC Saturday",
                "team_2": "14:00 UTC Sunday",
                "team_3": "20:00 UTC Sunday"
            },
            "ABSENT": {}
        }
        return structures.get(file_key, {})

    def _validate_json_structure(self, file_key: str, data: Any) -> Tuple[bool, List[str]]:
        """Validate JSON data structure and return issues found."""
        issues: List[str] = []

        if file_key == "EVENTS":
            if not isinstance(data, dict):
                issues.append("Events data should be a dictionary")
            else:
                for team in ("main_team", "team_2", "team_3"):
                    if team not in data:
                        issues.append(f"Missing team: {team}")
                    elif not isinstance(data[team], list):
                        issues.append(f"Team {team} should be a list, got {type(data[team]).__name__}")
                    else:
                        for idx, member in enumerate(data[team]):
                            # Accept both IGN strings and user IDs for backward compatibility
                            if isinstance(member, int):
                                if member <= 0:
                                    issues.append(f"Invalid user ID in {team}[{idx}]: {member}")
                            elif isinstance(member, str):
                                if not member.strip():
                                    issues.append(f"Empty IGN in {team}[{idx}]")
                            else:
                                issues.append(f"Invalid member type in {team}[{idx}]: {type(member).__name__}")

        elif file_key == "BLOCKED":
            if not isinstance(data, dict):
                issues.append("Blocked users data should be a dictionary")
            else:
                for user_id, info in data.items():
                    if not user_id.isdigit():
                        issues.append(f"Invalid user ID key: {user_id}")
                    if not isinstance(info, dict):
                        issues.append(f"User {user_id} info should be a dictionary")
                        continue
                    for field in ("blocked_by", "blocked_at", "ban_duration_days"):
                        if field not in info:
                            issues.append(f"User {user_id} missing field: {field}")
                    if "blocked_at" in info:
                        try:
                            datetime.fromisoformat(info["blocked_at"])
                        except ValueError:
                            issues.append(f"User {user_id} has invalid timestamp format")

        elif file_key == "RESULTS":
            if not isinstance(data, dict):
                issues.append("Results data should be a dictionary")
            else:
                if "total_wins" not in data or not isinstance(data["total_wins"], int):
                    issues.append("Missing or invalid total_wins")
                if "total_losses" not in data or not isinstance(data["total_losses"], int):
                    issues.append("Missing or invalid total_losses")
                if "history" not in data or not isinstance(data["history"], list):
                    issues.append("Missing or invalid history array")

        elif file_key == "HISTORY":
            if not isinstance(data, list):
                issues.append("History data should be a list")
            else:
                for idx, entry in enumerate(data):
                    if not isinstance(entry, dict):
                        issues.append(f"History entry {idx} should be a dictionary")
                        continue
                    if "timestamp" not in entry:
                        issues.append(f"History entry {idx} missing timestamp")
                    if "teams" not in entry or not isinstance(entry["teams"], dict):
                        issues.append(f"History entry {idx} missing or invalid teams data")

        elif file_key == "IGN_MAP":
            if not isinstance(data, dict):
                issues.append("IGN map should be a dictionary")
            else:
                for user_id, ign in data.items():
                    if not user_id.isdigit():
                        issues.append(f"Invalid user ID key: {user_id}")
                    if not isinstance(ign, str) or not ign.strip():
                        issues.append(f"Invalid IGN for user {user_id}: {ign}")

        elif file_key == "TIMES":
            if not isinstance(data, dict):
                issues.append("Times data should be a dictionary")
            else:
                for team in ("main_team", "team_2", "team_3"):
                    if team not in data:
                        issues.append(f"Missing time for team: {team}")
                    elif not isinstance(data[team], str):
                        issues.append(f"Time for {team} should be a string")

        elif file_key == "ABSENT":
            if not isinstance(data, dict):
                issues.append("Absent data should be a dictionary")

        return (len(issues) == 0, issues)

    # ============================================
    # GOOGLE SHEETS COMMANDS
    # ============================================

    @commands.command(name="syncmembers", help="Sync Discord members to Google Sheets")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def sync_discord_members(self, ctx: commands.Context, guild_id: int = None):
        """Sync Discord members to Google Sheets."""
        try:
            await ctx.send("🔄 **Syncing Discord members to Google Sheets...**")

            if not hasattr(self.bot, "sheets") or self.bot.sheets is None:
                return await ctx.send("❌ Google Sheets not configured.")

            result = await self.bot.sheets.scan_and_sync_all_members(
                self.bot, guild_id or ctx.guild.id
            )

            if result["success"]:
                embed = discord.Embed(
                    title="✅ Member Sync Complete",
                    color=COLORS["SUCCESS"]
                )
                embed.add_field(
                    name="📊 Results",
                    value=(
                        f"**Guild:** {result['guild_name']}\n"
                        f"**Total Members:** {result['total_discord_members']}\n"
                        f"**New Added:** {result['new_members_added']}\n"
                        f"**Updated:** {result['existing_members_updated']}"
                    )
                )

                if self.bot.sheets.spreadsheet:
                    embed.add_field(
                        name="🔗 Sheets",
                        value=f"[Open Spreadsheet]({self.bot.sheets.spreadsheet.url})",
                        inline=False
                    )

                await ctx.send(embed=embed)
                logger.info(f"{ctx.author} synced {result['new_members_added']} new members")
            else:
                await ctx.send(f"❌ **Sync failed:** {result.get('error')}")

        except Exception as e:
            logger.exception("Error in sync_discord_members")
            await ctx.send(f"❌ **Error:** {str(e)}")

    @commands.command(name="fullsync")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def full_sync_to_sheets(self, ctx: commands.Context):
        """Perform a complete data sync to Google Sheets."""
        try:
            await ctx.send("🔄 **Starting full sync to Google Sheets...**")

            # Check if bot has sheets manager
            if hasattr(self.bot, "sheets") and self.bot.sheets:
                sheets_manager = self.bot.sheets
                print(f"DEBUG: Using bot's sheets manager")
            else:
                # Try to create new instance
                print(f"DEBUG: Bot doesn't have sheets manager, creating new instance")
                try:
                    from sheets import SheetsManager
                    sheets_manager = SheetsManager()
                    print(f"DEBUG: Created new SheetsManager instance")
                except Exception as import_error:
                    await ctx.send(f"❌ **Error importing sheets manager:** {import_error}")
                    return

            if not sheets_manager.is_connected():
                await ctx.send("❌ **Google Sheets not connected.** Check credentials in Secrets.")
                return

            print(f"DEBUG: Sheets manager is connected, proceeding with sync")

            event_manager = self.bot.get_cog("EventManager")
            all_data = {
                "events": self.data_manager.load_json(FILES["EVENTS"], {}),
                "results": self.data_manager.load_json(FILES["RESULTS"], {}),
                "player_stats": getattr(event_manager.data_manager, 'player_stats', {}) if event_manager else {},
                "notification_preferences": self.data_manager.load_json("data/notification_preferences.json", {})
            }

            # Perform full sync with comprehensive data collection
            if hasattr(self.bot.sheets, 'full_sync_and_create_templates'):
                sync_result = await self.bot.sheets.full_sync_and_create_templates(
                    self.bot, all_data, ctx.guild.id
                )
            else:
                # Fallback to create_all_templates if full sync method doesn't exist
                success = self.bot.sheets.create_all_templates(all_data)
                sync_result = {
                    "success": success,
                    "spreadsheet_url": self.bot.sheets.spreadsheet.url if self.bot.sheets.spreadsheet else None
                }

            if sync_result["success"]:
                member_sync = sync_result.get("member_sync", {}) # Use get for safety
                embed = discord.Embed(
                    title="✅ Full Setup Complete!",
                    description="Discord members synced and all templates created",
                    color=COLORS["SUCCESS"]
                )

                embed.add_field(
                    name="👥 Member Sync",
                    value=(
                        f"**New Members:** {member_sync.get('new_members_added', 'N/A')}\n"
                        f"**Updated:** {member_sync.get('existing_members_updated', 'N/A')}\n"
                        f"**Total:** {member_sync.get('total_discord_members', 'N/A')}"
                    )
                )

                embed.add_field(
                    name="📊 Templates Created",
                    value=(
                        "✅ Player Stats (all Discord members)\n"
                        "✅ Current Teams\n"
                        "✅ Results History\n"
                        "✅ Match Statistics\n"
                        "✅ Alliance Tracking\n"
                        "✅ Dashboard\n"
                        "✅ Notification Preferences\n"
                        "✅ Error Summary"
                    )
                )

                if sync_result.get("spreadsheet_url"):
                    embed.add_field(
                        name="🔗 Google Sheets",
                        value=f"[Open Spreadsheet]({sync_result['spreadsheet_url']})",
                        inline=False
                    )

                embed.add_field(
                    name="📝 Next Steps",
                    value=(
                        "1. Fill in power ratings in Player Stats sheet\n"
                        "2. Set specializations (Cavalry, Mages, etc.)\n"
                        "3. Add match data and alliance info manually"
                    ),
                    inline=False
                )

                await ctx.send(embed=embed)
                logger.info(f"{ctx.author} completed full sync")
            else:
                await ctx.send(f"❌ **Setup failed:** {sync_result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.exception("Error in full_sync_and_setup")
            await ctx.send(f"❌ **Error:** {str(e)}")


    @commands.command(name="sheetsinfo", help="Show Google Sheets status")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def sheets_info(self, ctx: commands.Context):
        """Show Google Sheets integration status."""
        try:
            if not hasattr(self.bot, "sheets") or self.bot.sheets is None:
                embed = discord.Embed(
                    title="⚠️ Google Sheets Not Configured",
                    description="Set environment variables and restart bot",
                    color=COLORS["WARNING"]
                )
                embed.add_field(
                    name="Required Variables",
                    value="• `GOOGLE_SHEETS_CREDENTIALS`\n• `GOOGLE_SHEETS_ID`"
                )
                return await ctx.send(embed=embed)

            sheets_manager = self.bot.sheets
            embed = discord.Embed(
                title="📊 Google Sheets Status",
                description="✅ Integration active",
                color=COLORS["SUCCESS"]
            )

            if sheets_manager.spreadsheet:
                try:
                    worksheets = [ws.title for ws in sheets_manager.spreadsheet.worksheets()]
                    embed.add_field(
                        name="📋 Spreadsheet",
                        value=f"**Worksheets:** {len(worksheets)}\n[Open Spreadsheet]({sheets_manager.spreadsheet.url})"
                    )
                    embed.add_field(
                        name="📄 Available Sheets",
                        value="\n".join([f"• {ws}" for ws in worksheets[:10]]),
                        inline=False
                    )
                except Exception as e:
                    embed.add_field(
                        name="⚠️ Access Error",
                        value=f"Cannot read worksheets: {str(e)}"
                    )

            embed.add_field(
                name="🛠️ Commands",
                value="`!syncmembers` • `!fullsync` • `!sheetsinfo`",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.exception("Error in sheets_info")
            await ctx.send(f"❌ **Error:** {str(e)}")


    # ============================================
    # JSON FILE MANAGEMENT COMMANDS
    # ============================================

    @commands.command(name="checkjson", help="Check the integrity of all JSON data files.")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def check_json_status(self, ctx: commands.Context):
        """Check the integrity of all JSON data files."""
        embed = discord.Embed(
            title="🔍 JSON File Status Report",
            description="Checking integrity of all bot data files...",
            color=COLORS["INFO"]
        )
        total_files = len(FILES)
        healthy = 0
        issues_found: List[str] = []

        for key, path in FILES.items():
            if key == "LOG":
                continue
            status_emoji = EMOJIS["SUCCESS"]
            status_text = "✅ Healthy"
            file_issues: List[str] = []

            if not os.path.exists(path):
                status_emoji = EMOJIS["WARNING"]
                status_text = "⚠️ Missing (will use defaults)"
                file_issues.append("File does not exist")
            else:
                try:
                    data = self.data_manager.load_json(path, {})
                    if data is None:
                        status_emoji = EMOJIS["ERROR"]
                        status_text = "❌ Corrupted"
                        file_issues.append("Failed to parse JSON")
                    else:
                        valid, struct_issues = self._validate_json_structure(key, data)
                        if not valid:
                            status_emoji = EMOJIS["WARNING"]
                            status_text = "⚠️ Structure Issues"
                            file_issues.extend(struct_issues)
                        else:
                            healthy += 1
                except Exception as e:
                    status_emoji = EMOJIS["ERROR"]
                    status_text = "❌ Read Error"
                    file_issues.append(f"Exception: {e}")

            size = f"{os.path.getsize(path)} bytes" if os.path.exists(path) else "N/A"
            field_value = f"{status_text}\n📁 `{os.path.basename(path)}`\n📏 {size}"
            if file_issues:
                issues_found.extend([f"**{key}**: {issue}" for issue in file_issues])
                field_value += f"\n🔧 {len(file_issues)} issue(s) found"
            embed.add_field(name=f"{status_emoji} {key}", value=field_value, inline=True)

        checked = total_files - (1 if "LOG" in FILES else 0)
        health_pct = (healthy / checked * 100) if checked else 0.0
        embed.color = COLORS["SUCCESS"] if health_pct >= 80 else COLORS["WARNING"] if health_pct >= 60 else COLORS["DANGER"]
        embed.add_field(name="📊 Summary", value=f"**{healthy}/{checked}** healthy ({health_pct:.1f}%)", inline=False)

        if issues_found:
            snippet = "\n".join(issues_found[:10])
            if len(issues_found) > 10:
                snippet += f"\n... and {len(issues_found) - 10} more issues"
            embed.add_field(name="🚨 Issues Found", value=snippet, inline=False)

        embed.set_footer(text=f"Report generated at {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")
        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} requested JSON status: {healthy}/{checked} healthy")

    @commands.command(name="fixjson", help="Attempt to fix corrupted or missing JSON files.")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def fix_json_files(self, ctx: commands.Context):
        """Attempt to fix corrupted or missing JSON files."""
        embed = discord.Embed(title="🔧 JSON File Repair Report",
                               description="Attempting to fix JSON file issues...",
                               color=COLORS["WARNING"])
        fixed, failed, skipped = [], [], []

        for key, path in FILES.items():
            if key == "LOG":
                continue
            needs_fix = False
            reason = ""
            data = {}

            try:
                if not os.path.exists(path):
                    needs_fix, reason = True, "File missing"
                else:
                    data = self.data_manager.load_json(path, None)
                    if data is None:
                        needs_fix, reason = True, "JSON corrupted"
                    else:
                        valid, struct_issues = self._validate_json_structure(key, data)
                        if not valid:
                            needs_fix, reason = True, f"{len(struct_issues)} structure issues"
            except Exception as e:
                needs_fix, reason = True, f"Exception: {e}"

            if needs_fix:
                if os.path.exists(path):
                    backup = f"{path}.backup.{datetime.utcnow():%Y%m%d_%H%M%S}"
                    try:
                        import shutil
                        shutil.copy2(path, backup)
                        logger.info(f"Backup created: {backup}")
                    except Exception as e:
                        logger.warning(f"Backup failed for {path}: {e}")

                default = self._get_expected_structure(key)

                # Try to preserve valid data when possible
                if isinstance(default, dict) and isinstance(data, dict):
                    if key == "EVENTS":
                        # Handle both user IDs and IGN strings
                        for team in ("main_team", "team_2", "team_3"):
                            if team in data and isinstance(data[team], list):
                                valid_members = []
                                for member in data[team]:
                                    if isinstance(member, int) and member > 0:
                                        valid_members.append(member)
                                    elif isinstance(member, str) and member.strip():
                                        valid_members.append(member.strip())
                                default[team] = valid_members

                    elif key == "BLOCKED":
                        for uid, info in data.items():
                            if (uid.isdigit() and isinstance(info, dict) and
                                all(field in info for field in ("blocked_by", "blocked_at", "ban_duration_days"))):
                                default[uid] = info

                    elif key == "IGN_MAP":
                        for uid, ign in data.items():
                            if uid.isdigit() and isinstance(ign, str) and ign.strip():
                                default[uid] = ign.strip()

                saved = self.data_manager.save_json(path, default)
                if saved:
                    fixed.append(f"**{key}**: {reason}")
                    logger.info(f"Fixed {key}: {reason}")
                else:
                    failed.append(f"**{key}**: failed to save")
                    logger.error(f"Failed fix {key}")
            else:
                skipped.append(key)

        if fixed:
            embed.add_field(name=f"✅ Fixed Files ({len(fixed)})", value="\n".join(fixed), inline=False)
        if failed:
            embed.add_field(name=f"❌ Failed Fixes ({len(failed)})", value="\n".join(failed), inline=False)
        if skipped:
            embed.add_field(name=f"⏭️ Skipped (Healthy) ({len(skipped)})", value=", ".join(skipped), inline=False)

        embed.color = COLORS["DANGER"] if failed else (COLORS["SUCCESS"] if fixed else COLORS["INFO"])
        embed.add_field(name="📋 Summary", value=f"Fixed: {len(fixed)} | Failed: {len(failed)} | Skipped: {len(skipped)}", inline=False)
        if fixed:
            embed.add_field(name="⚠️ Note", value="Valid data preserved where possible; check results.", inline=False)
        embed.set_footer(text=f"Repair completed at {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")
        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} ran fix: fixed {len(fixed)}, failed {len(failed)}")

    @commands.command(name="resetjson", help="Reset a specific JSON file to its default structure.")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def reset_json_file(self, ctx: commands.Context, file_key: str):
        """Reset a specific JSON file to its default structure."""
        key = file_key.upper()
        if key not in FILES or key == "LOG":
            available = [k for k in FILES if k != "LOG"]
            return await ctx.send(f"❌ Invalid key. Available: {', '.join(available)}")

        path = FILES[key]
        backuped = False

        if os.path.exists(path):
            backup = f"{path}.backup.{datetime.utcnow():%Y%m%d_%H%M%S}"
            try:
                import shutil
                shutil.copy2(path, backup)
                backuped = True
            except Exception as e:
                await ctx.send(f"⚠️ Backup failed: {e}")

        default = self._get_expected_structure(key)
        success = self.data_manager.save_json(path, default)

        if success:
            embed = discord.Embed(title="🔄 JSON Reset", description=f"Reset **{key}** to default structure.", color=COLORS["SUCCESS"])
            if backuped:
                embed.add_field(name="💾 Backup", value=f"`{os.path.basename(backup)}`", inline=False)
            embed.add_field(name="⚠️ Note", value="Previous data cleared.", inline=False)
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} reset {key}")
        else:
            await ctx.send(f"❌ Failed to reset {key}. Check logs.")
            logger.error(f"Failed to reset {key} for {ctx.author}")

    @commands.command(name="migratedata", help="Convert user IDs in events.json to IGN strings.")
    @commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
    async def migrate_user_ids_to_igns(self, ctx: commands.Context):
        """Convert user IDs in events.json to IGN strings."""
        events_data = self.data_manager.load_json(FILES["EVENTS"], {"main_team": [], "team_2": [], "team_3": []})
        profile_cog = self.bot.get_cog("Profile")

        if not profile_cog:
            return await ctx.send("❌ Profile cog not loaded. Cannot migrate data.")

        converted_count = 0
        failed_conversions = []

        for team_name, members in events_data.items():
            new_members = []
            for member in members:
                if isinstance(member, int):
                    # Convert user ID to IGN
                    user = self.bot.get_user(member)
                    if user:
                        ign = profile_cog.get_ign(user)
                        new_members.append(ign)
                        converted_count += 1
                    else:
                        failed_conversions.append(f"User ID {member} not found")
                        new_members.append(str(member))  # Keep as string
                elif isinstance(member, str):
                    # Already an IGN string
                    new_members.append(member)
                else:
                    failed_conversions.append(f"Unknown member type: {type(member)}")

            events_data[team_name] = new_members

        # Save the migrated data
        success = self.data_manager.save_json(FILES["EVENTS"], events_data)

        embed = discord.Embed(
            title="🔄 Data Migration Complete",
            color=COLORS["SUCCESS"] if success else COLORS["DANGER"]
        )

        if success:
            embed.add_field(name="✅ Converted", value=f"{converted_count} user IDs → IGNs", inline=True)
            if failed_conversions:
                failures = "\n".join(failed_conversions[:5])
                if len(failed_conversions) > 5:
                    failures += f"\n... and {len(failed_conversions) - 5} more"
                embed.add_field(name="⚠️ Failed", value=failures, inline=False)
        else:
            embed.description = "❌ Failed to save migrated data"

        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} migrated {converted_count} user IDs to IGNs")


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerActions(bot))
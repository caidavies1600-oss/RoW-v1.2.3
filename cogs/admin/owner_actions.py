import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

from config.constants import FILES, EMOJIS, COLORS
from config.settings import BOT_ADMIN_USER_ID
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger(“owner_actions”)

class OwnerActions(commands.Cog):
“”“Owner-only commands for bot maintenance and JSON file management.”””

```
def __init__(self, bot):
    self.bot = bot
    self.data_manager = DataManager()

def _is_owner(self, user_id: int) -> bool:
    """Check if user is the bot owner."""
    return user_id == BOT_ADMIN_USER_ID

def _get_expected_structure(self, file_key: str) -> Dict[str, Any]:
    """Get expected JSON structure for each file."""
    structures = {
        "EVENTS": {
            "main_team": [],
            "team_2": [],
            "team_3": []
        },
        "BLOCKED": {},
        "IGN_MAP": {},
        "RESULTS": {
            "total_wins": 0,
            "total_losses": 0,
            "history": []
        },
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
    issues = []
    expected = self._get_expected_structure(file_key)

    if file_key == "EVENTS":
        if not isinstance(data, dict):
            issues.append("Events data should be a dictionary")
            return False, issues

        required_teams = ["main_team", "team_2", "team_3"]
        for team in required_teams:
            if team not in data:
                issues.append(f"Missing team: {team}")
            elif not isinstance(data[team], list):
                issues.append(f"Team {team} should be a list, got {type(data[team])}")
            else:
                # Check for valid user IDs
                for i, user_id in enumerate(data[team]):
                    if not isinstance(user_id, int) or user_id <= 0:
                        issues.append(f"Invalid user ID in {team}[{i}]: {user_id}")

    elif file_key == "BLOCKED":
        if not isinstance(data, dict):
            issues.append("Blocked users data should be a dictionary")
            return False, issues

        for user_id, info in data.items():
            if not user_id.isdigit():
                issues.append(f"Invalid user ID key: {user_id}")
            if not isinstance(info, dict):
                issues.append(f"User {user_id} info should be a dictionary")
                continue

            required_fields = ["blocked_by", "blocked_at", "ban_duration_days"]
            for field in required_fields:
                if field not in info:
                    issues.append(f"User {user_id} missing field: {field}")

            # Validate timestamp format
            if "blocked_at" in info:
                try:
                    datetime.fromisoformat(info["blocked_at"])
                except ValueError:
                    issues.append(f"User {user_id} has invalid timestamp format")

    elif file_key == "RESULTS":
        if not isinstance(data, dict):
            issues.append("Results data should be a dictionary")
            return False, issues

        if "total_wins" not in data or not isinstance(data["total_wins"], int):
            issues.append("Missing or invalid total_wins")
        if "total_losses" not in data or not isinstance(data["total_losses"], int):
            issues.append("Missing or invalid total_losses")
        if "history" not in data or not isinstance(data["history"], list):
            issues.append("Missing or invalid history array")

    elif file_key == "HISTORY":
        if not isinstance(data, list):
            issues.append("History data should be a list")
            return False, issues

        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                issues.append(f"History entry {i} should be a dictionary")
                continue
            if "timestamp" not in entry:
                issues.append(f"History entry {i} missing timestamp")
            if "teams" not in entry or not isinstance(entry["teams"], dict):
                issues.append(f"History entry {i} missing or invalid teams data")

    elif file_key == "IGN_MAP":
        if not isinstance(data, dict):
            issues.append("IGN map should be a dictionary")
            return False, issues

        for user_id, ign in data.items():
            if not user_id.isdigit():
                issues.append(f"Invalid user ID key: {user_id}")
            if not isinstance(ign, str) or not ign.strip():
                issues.append(f"Invalid IGN for user {user_id}: {ign}")

    elif file_key == "TIMES":
        if not isinstance(data, dict):
            issues.append("Times data should be a dictionary")
            return False, issues

        required_teams = ["main_team", "team_2", "team_3"]
        for team in required_teams:
            if team not in data:
                issues.append(f"Missing time for team: {team}")
            elif not isinstance(data[team], str):
                issues.append(f"Time for {team} should be a string")

    elif file_key == "ABSENT":
        if not isinstance(data, dict):
            issues.append("Absent data should be a dictionary")
            return False, issues

    return len(issues) == 0, issues

@commands.command(name="checkjson")
@commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
async def check_json_status(self, ctx):
    """Check the status and integrity of all JSON data files."""
    embed = discord.Embed(
        title="🔍 JSON File Status Report",
        description="Checking integrity of all bot data files...",
        color=COLORS["INFO"]
    )

    total_files = len(FILES)
    healthy_files = 0
    issues_found = []

    for file_key, file_path in FILES.items():
        if file_key == "LOG":  # Skip log file
            continue

        status_emoji = EMOJIS["SUCCESS"]
        status_text = "✅ Healthy"
        file_issues = []

        # Check if file exists
        if not os.path.exists(file_path):
            status_emoji = EMOJIS["WARNING"]
            status_text = "⚠️ Missing (will use defaults)"
            file_issues.append("File does not exist")
        else:
            # Check if file is readable
            try:
                data = self.data_manager.load_json(file_path, {})
                if data is None:
                    status_emoji = EMOJIS["ERROR"]
                    status_text = "❌ Corrupted"
                    file_issues.append("Failed to parse JSON")
                else:
                    # Validate structure
                    is_valid, validation_issues = self._validate_json_structure(file_key, data)
                    if not is_valid:
                        status_emoji = EMOJIS["WARNING"]
                        status_text = "⚠️ Structure Issues"
                        file_issues.extend(validation_issues)
                    else:
                        healthy_files += 1

            except Exception as e:
                status_emoji = EMOJIS["ERROR"]
                status_text = "❌ Read Error"
                file_issues.append(f"Exception: {str(e)}")

        # Add to embed
        file_size = "N/A"
        if os.path.exists(file_path):
            try:
                file_size = f"{os.path.getsize(file_path)} bytes"
            except:
                file_size = "Unknown"

        field_value = f"{status_text}\n📁 `{os.path.basename(file_path)}`\n📏 {file_size}"

        if file_issues:
            issues_found.extend([f"**{file_key}**: {issue}" for issue in file_issues])
            field_value += f"\n🔧 {len(file_issues)} issue(s) found"

        embed.add_field(
            name=f"{status_emoji} {file_key}",
            value=field_value,
            inline=True
        )

    # Summary
    total_checked = total_files - 1  # Exclude LOG file
    health_percentage = (healthy_files / total_checked) * 100 if total_checked > 0 else 0

    summary_color = COLORS["SUCCESS"] if health_percentage >= 80 else COLORS["WARNING"] if health_percentage >= 60 else COLORS["DANGER"]
    embed.color = summary_color

    embed.add_field(
        name="📊 Summary",
        value=f"**{healthy_files}/{total_checked}** files healthy ({health_percentage:.1f}%)",
        inline=False
    )

    if issues_found:
        issues_text = "\n".join(issues_found[:10])  # Limit to first 10 issues
        if len(issues_found) > 10:
            issues_text += f"\n... and {len(issues_found) - 10} more issues"

        embed.add_field(
            name="🚨 Issues Found",
            value=issues_text,
            inline=False
        )

    embed.set_footer(text=f"Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    await ctx.send(embed=embed)
    logger.info(f"{ctx.author} requested JSON status check - {healthy_files}/{total_checked} files healthy")

@commands.command(name="fixjson")
@commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
async def fix_json_files(self, ctx):
    """Attempt to fix corrupted or missing JSON files by restoring default structures."""
    embed = discord.Embed(
        title="🔧 JSON File Repair Report",
        description="Attempting to fix JSON file issues...",
        color=COLORS["WARNING"]
    )

    fixed_files = []
    failed_fixes = []
    skipped_files = []

    for file_key, file_path in FILES.items():
        if file_key == "LOG":  # Skip log file
            continue

        try:
            # Check if file exists and is readable
            data = None
            needs_fix = False
            fix_reason = ""

            if not os.path.exists(file_path):
                needs_fix = True
                fix_reason = "File missing"
            else:
                try:
                    data = self.data_manager.load_json(file_path, None)
                    if data is None:
                        needs_fix = True
                        fix_reason = "JSON corrupted"
                    else:
                        # Check structure
                        is_valid, issues = self._validate_json_structure(file_key, data)
                        if not is_valid:
                            needs_fix = True
                            fix_reason = f"Structure issues: {len(issues)} found"
                except Exception as e:
                    needs_fix = True
                    fix_reason = f"Read error: {str(e)}"

            if needs_fix:
                # Create backup if file exists
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        import shutil
                        shutil.copy2(file_path, backup_path)
                        logger.info(f"Created backup: {backup_path}")
                    except Exception as e:
                        logger.warning(f"Failed to create backup for {file_path}: {e}")

                # Restore default structure
                default_structure = self._get_expected_structure(file_key)

                # Try to preserve valid data if possible
                if data and isinstance(data, (dict, list)):
                    if file_key == "EVENTS" and isinstance(data, dict):
                        # Preserve valid team data
                        for team in ["main_team", "team_2", "team_3"]:
                            if team in data and isinstance(data[team], list):
                                # Validate user IDs
                                valid_ids = [uid for uid in data[team] if isinstance(uid, int) and uid > 0]
                                default_structure[team] = valid_ids

                    elif file_key == "BLOCKED" and isinstance(data, dict):
                        # Preserve valid blocked user entries
                        for user_id, info in data.items():
                            if (user_id.isdigit() and isinstance(info, dict) and 
                                all(field in info for field in ["blocked_by", "blocked_at", "ban_duration_days"])):
                                default_structure[user_id] = info

                success = self.data_manager.save_json(file_path, default_structure)

                if success:
                    fixed_files.append(f"**{file_key}**: {fix_reason}")
                    logger.info(f"Fixed {file_key}: {fix_reason}")
                else:
                    failed_fixes.append(f"**{file_key}**: Failed to save fixed data")
                    logger.error(f"Failed to fix {file_key}")
            else:
                skipped_files.append(file_key)

        except Exception as e:
            failed_fixes.append(f"**{file_key}**: Exception during fix - {str(e)}")
            logger.exception(f"Error fixing {file_key}")

    # Build report
    if fixed_files:
        embed.add_field(
            name=f"✅ Fixed Files ({len(fixed_files)})",
            value="\n".join(fixed_files),
            inline=False
        )

    if failed_fixes:
        embed.add_field(
            name=f"❌ Failed Fixes ({len(failed_fixes)})",
            value="\n".join(failed_fixes),
            inline=False
        )

    if skipped_files:
        embed.add_field(
            name=f"⏭️ Skipped (Healthy) ({len(skipped_files)})",
            value=", ".join(skipped_files),
            inline=False
        )

    # Set final color based on results
    if failed_fixes:
        embed.color = COLORS["DANGER"]
    elif fixed_files:
        embed.color = COLORS["SUCCESS"]
    else:
        embed.color = COLORS["INFO"]

    embed.add_field(
        name="📋 Summary",
        value=f"Fixed: {len(fixed_files)} | Failed: {len(failed_fixes)} | Skipped: {len(skipped_files)}",
        inline=False
    )

    if fixed_files:
        embed.add_field(
            name="⚠️ Important",
            value="Fixed files have been reset to default structures. You may need to reconfigure some settings.",
            inline=False
        )

    embed.set_footer(text=f"Repair completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    await ctx.send(embed=embed)
    logger.info(f"{ctx.author} ran JSON repair - Fixed: {len(fixed_files)}, Failed: {len(failed_fixes)}")

@commands.command(name="resetjson")
@commands.check(lambda ctx: ctx.author.id == BOT_ADMIN_USER_ID)
async def reset_json_file(self, ctx, file_key: str):
    """Reset a specific JSON file to its default structure."""
    file_key = file_key.upper()

    if file_key not in FILES or file_key == "LOG":
        available_keys = [k for k in FILES.keys() if k != "LOG"]
        await ctx.send(f"❌ Invalid file key. Available: {', '.join(available_keys)}")
        return

    file_path = FILES[file_key]

    # Create backup if file exists
    backup_created = False
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            backup_created = True
        except Exception as e:
            await ctx.send(f"⚠️ Warning: Could not create backup - {e}")

    # Reset to default structure
    default_structure = self._get_expected_structure(file_key)
    success = self.data_manager.save_json(file_path, default_structure)

    if success:
        embed = discord.Embed(
            title="🔄 JSON File Reset",
            description=f"Successfully reset **{file_key}** to default structure.",
            color=COLORS["SUCCESS"]
        )

        if backup_created:
            embed.add_field(
                name="💾 Backup Created",
                value=f"`{os.path.basename(backup_path)}`",
                inline=False
            )

        embed.add_field(
            name="⚠️ Note",
            value="All previous data in this file has been cleared.",
            inline=False
        )

        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} reset {file_key} to defaults")
    else:
        await ctx.send(f"❌ Failed to reset {file_key}. Check logs for details.")
        logger.error(f"Failed to reset {file_key} for {ctx.author}")
```

async def setup(bot):
await bot.add_cog(OwnerActions(bot))
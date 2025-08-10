
import json
import discord
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from discord.ext import tasks, commands
import asyncio

from utils.logger import setup_logger
from utils.data_manager import DataManager
from config.constants import FILES, COLORS, EMOJIS, TEAM_DISPLAY, DEFAULT_TIMES

logger = setup_logger("smart_notifications")

async def setup(bot):
    """Setup function required for Discord.py cogs."""
    await bot.add_cog(SmartNotifications(bot))

class SmartNotifications:
    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()
        self.notification_prefs = self.load_notification_preferences()
        self.notification_queue = []

    def load_notification_preferences(self) -> Dict[str, Any]:
        """Load user notification preferences from Google Sheets first, then fallback to JSON."""
        default_prefs = {
            "users": {},
            "default_settings": {
                "method": "channel",  # "dm", "channel", "both"
                "event_reminders": True,
                "result_notifications": True,
                "team_updates": True,
                "reminder_times": [60, 15],  # Minutes before event
                "quiet_hours": {"start": 22, "end": 8},  # UTC hours
                "timezone_offset": 0
            }
        }

        # Try to load from Google Sheets first
        sheets_prefs = None
        if hasattr(self.bot, 'sheets') and self.bot.sheets:
            try:
                logger.debug("Attempting to load notification preferences from Google Sheets...")
                sheets_prefs = self.bot.sheets.load_notification_preferences_from_sheets()
                if sheets_prefs and isinstance(sheets_prefs, dict):
                    # Validate the structure
                    if "users" in sheets_prefs and "default_settings" in sheets_prefs:
                        logger.info(f"✅ Loaded notification preferences from Google Sheets ({len(sheets_prefs.get('users', {}))} users)")
                        return sheets_prefs
                    else:
                        logger.warning("⚠️ Invalid structure in sheets preferences, falling back to JSON")
                        sheets_prefs = None
                else:
                    logger.debug("No valid preferences found in Google Sheets, falling back to JSON")
            except Exception as e:
                logger.warning(f"Failed to load notification preferences from Sheets: {e}")
                import traceback
                logger.debug(f"Sheets loading traceback: {traceback.format_exc()}")

        # Fallback to JSON file
        try:
            json_prefs = self.data_manager.load_json("data/notification_preferences.json", default_prefs)
            if sheets_prefs is None:
                logger.info(f"📄 Loaded notification preferences from JSON file ({len(json_prefs.get('users', {}))} users)")
            else:
                logger.info("📄 Using JSON file as fallback due to sheets loading issues")
            return json_prefs
        except Exception as e:
            logger.error(f"Failed to load preferences from both Sheets and JSON: {e}")
            logger.warning("Using default preferences")
            return default_prefs

    def save_notification_preferences(self):
        """Save notification preferences to both JSON and Google Sheets."""
        # Save to JSON file
        json_success = self.data_manager.save_json("data/notification_preferences.json", self.notification_prefs, sync_to_sheets=False)

        # Sync to Google Sheets
        sheets_success = True
        if hasattr(self.bot, 'sheets') and self.bot.sheets:
            try:
                sheets_success = self.bot.sheets.sync_notification_preferences(self.notification_prefs)
                if sheets_success:
                    logger.info("✅ Synced notification preferences to Google Sheets")
                else:
                    logger.warning("⚠️ Failed to sync notification preferences to Sheets")
            except Exception as e:
                logger.error(f"Error syncing notification preferences to Sheets: {e}")
                sheets_success = False

        return json_success and sheets_success

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get notification preferences for a specific user."""
        user_id = str(user_id)
        user_prefs = self.notification_prefs["users"].get(user_id, {})
        default_prefs = self.notification_prefs["default_settings"]

        # Merge user preferences with defaults
        merged_prefs = default_prefs.copy()
        merged_prefs.update(user_prefs)
        return merged_prefs

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update notification preferences for a user."""
        try:
            user_id = str(user_id)
            
            # Create new user entry if it doesn't exist
            if user_id not in self.notification_prefs["users"]:
                self.notification_prefs["users"][user_id] = {}
            
            # Try to get the actual Discord username
            try:
                user = self.bot.get_user(int(user_id))
                if user:
                    display_name = user.display_name or user.name
                else:
                    # Fallback: try to fetch user
                    import asyncio
                    if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop():
                        # We're in an async context, but can't await here
                        display_name = f"User_{user_id}"
                    else:
                        display_name = f"User_{user_id}"
            except:
                display_name = f"User_{user_id}"
            
            # Always update the display name when preferences are updated
            preferences["display_name"] = display_name
            
            # Update the user's preferences
            self.notification_prefs["users"][user_id].update(preferences)
            
            logger.info(f"Updated preferences for {display_name} ({user_id})")
            return self.save_notification_preferences()
        except Exception as e:
            logger.error(f"Failed to update preferences for {user_id}: {e}")
            return False

    def is_quiet_hours(self, user_id: str) -> bool:
        """Check if it's currently quiet hours for a user."""
        try:
            prefs = self.get_user_preferences(user_id)
            quiet_hours = prefs.get("quiet_hours", {"start": 22, "end": 8})
            timezone_offset = prefs.get("timezone_offset", 0)
            
            from datetime import datetime, timedelta
            
            # Get current time in user's timezone
            utc_now = datetime.utcnow()
            user_time = utc_now + timedelta(hours=timezone_offset)
            current_hour = user_time.hour
            
            start_hour = quiet_hours["start"]
            end_hour = quiet_hours["end"]
            
            # Handle quiet hours that span midnight
            if start_hour > end_hour:
                return current_hour >= start_hour or current_hour < end_hour
            else:
                return start_hour <= current_hour < end_hour
                
        except Exception as e:
            logger.error(f"Error checking quiet hours for {user_id}: {e}")
            return False

    async def update_user_preferences_async(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Async version of update_user_preferences that can properly fetch usernames."""
        try:
            user_id = str(user_id)
            
            # Create new user entry if it doesn't exist
            if user_id not in self.notification_prefs["users"]:
                self.notification_prefs["users"][user_id] = {}
            
            # Try to get the actual Discord username
            try:
                user = self.bot.get_user(int(user_id))
                if not user:
                    user = await self.bot.fetch_user(int(user_id))
                
                if user:
                    display_name = user.display_name or user.name
                else:
                    display_name = f"User_{user_id}"
            except Exception as e:
                logger.warning(f"Could not fetch user {user_id}: {e}")
                display_name = f"User_{user_id}"
            
            # Always update the display name when preferences are updated
            preferences["display_name"] = display_name
            
            # Update the user's preferences
            self.notification_prefs["users"][user_id].update(preferences)
            
            logger.info(f"Updated preferences for {display_name} ({user_id})")
            return self.save_notification_preferences()
        except Exception as e:
            logger.error(f"Failed to update preferences for {user_id}: {e}")
            return False

    async def send_smart_notification(self, user_id: str, notification_type: str, content: Dict[str, Any]):
        """Send a smart notification based on user preferences."""
        try:
            user_id = str(user_id)
            prefs = self.get_user_preferences(user_id)

            # Check if user wants this type of notification
            if not prefs.get(notification_type, True):
                return

            # Check quiet hours
            if self.is_quiet_hours(user_id):
                # Queue for later delivery
                self.notification_queue.append({
                    "user_id": user_id,
                    "type": notification_type,
                    "content": content,
                    "queued_at": datetime.utcnow()
                })
                return

            # Get notification method
            method = prefs.get("method", "channel")

            # Create notification message
            embed = self._create_notification_embed(notification_type, content)

            try:
                user = await self.bot.fetch_user(int(user_id))
                dm_sent = False
                channel_sent = False

                if method == "dm" or method == "both":
                    try:
                        await user.send(embed=embed)
                        dm_sent = True
                        logger.info(f"✅ Sent DM notification to {user.display_name} ({user_id})")
                    except discord.Forbidden:
                        logger.warning(f"⚠️ Cannot send DM to {user.display_name} ({user_id}) - DMs disabled or blocked")
                        if method == "dm":
                            method = "channel"  # Fallback to channel if DM-only failed
                    except discord.HTTPException as e:
                        logger.error(f"❌ HTTP error sending DM to {user.display_name} ({user_id}): {e}")
                        if method == "dm":
                            method = "channel"  # Fallback to channel
                    except Exception as e:
                        logger.error(f"❌ Unexpected error sending DM to {user.display_name} ({user_id}): {e}")
                        if method == "dm":
                            method = "channel"  # Fallback to channel

                if method == "channel" or method == "both":
                    try:
                        # Send to main notification channel
                        from config.constants import ALERT_CHANNEL_ID
                        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
                        if channel:
                            await channel.send(f"<@{user_id}>", embed=embed)
                            channel_sent = True
                            logger.info(f"✅ Sent channel notification to {user.display_name} ({user_id})")
                        else:
                            logger.error(f"❌ Alert channel not found (ID: {ALERT_CHANNEL_ID})")
                    except Exception as e:
                        logger.error(f"❌ Failed to send channel notification to {user_id}: {e}")

                # Log final delivery status
                if not dm_sent and not channel_sent:
                    logger.error(f"❌ Failed to deliver notification to {user.display_name} ({user_id}) via any method")
                elif dm_sent and channel_sent:
                    logger.info(f"📨 Delivered notification to {user.display_name} ({user_id}) via both DM and channel")
                elif dm_sent:
                    logger.info(f"📱 Delivered notification to {user.display_name} ({user_id}) via DM only")
                elif channel_sent:
                    logger.info(f"💬 Delivered notification to {user.display_name} ({user_id}) via channel only")

            except Exception as e:
                logger.error(f"❌ Failed to send notification to {user_id}: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")

        except Exception as e:
            logger.error(f"Error in send_smart_notification: {e}")

    def _create_notification_embed(self, notification_type: str, content: Dict[str, Any]) -> discord.Embed:
        """Create an embed for the notification."""
        if notification_type == "event_reminders":
            embed = discord.Embed(
                title=f"{EMOJIS['CALENDAR']} Event Reminder",
                description=content.get("message", "Event starting soon!"),
                color=COLORS["WARNING"]
            )
            embed.add_field(
                name="Event Details",
                value=content.get("details", "Check event channel for details"),
                inline=False
            )

        elif notification_type == "result_notifications":
            embed = discord.Embed(
                title=f"{EMOJIS['TROPHY']} Match Result",
                description=content.get("message", "Match completed!"),
                color=COLORS["SUCCESS"] if content.get("won", False) else COLORS["DANGER"]
            )

        elif notification_type == "team_updates":
            embed = discord.Embed(
                title=f"{EMOJIS['INFO']} Team Update",
                description=content.get("message", "Team information updated"),
                color=COLORS["INFO"]
            )

        else:
            embed = discord.Embed(
                title="Notification",
                description=content.get("message", "You have a new notification"),
                color=COLORS["PRIMARY"]
            )

        embed.timestamp = datetime.utcnow()
        return embed

    async def process_notification_queue(self):
        """Process queued notifications for users who were in quiet hours."""
        try:
            processed = []

            for notification in self.notification_queue[:]:
                user_id = notification["user_id"]

                # Check if still in quiet hours
                if not self.is_quiet_hours(user_id):
                    await self.send_smart_notification(
                        user_id,
                        notification["type"],
                        notification["content"]
                    )
                    processed.append(notification)

                # Remove old queued notifications (24+ hours)
                elif (datetime.utcnow() - notification["queued_at"]).total_seconds() > 86400:
                    processed.append(notification)

            # Remove processed notifications
            for notification in processed:
                self.notification_queue.remove(notification)

        except Exception as e:
            logger.error(f"Error processing notification queue: {e}")

    async def send_event_reminders(self, team_key: str, minutes_before: List[int]):
        """Send event reminders to team members."""
        try:
            # Get current team members
            event_manager = self.bot.get_cog("EventManager")
            if not event_manager:
                return

            team_members = event_manager.events.get(team_key, [])

            for member_id in team_members:
                prefs = self.get_user_preferences(member_id)

                if prefs.get("event_reminders", True):
                    for minutes in minutes_before:
                        content = {
                            "message": f"Event starting in {minutes} minutes!",
                            "details": f"Team: {team_key.replace('_', ' ').title()}\nTime: {minutes} minutes from now"
                        }

                        await self.send_smart_notification(member_id, "event_reminders", content)

        except Exception as e:
            logger.error(f"Error sending event reminders: {e}")

    async def send_team_specific_reminders(self, team_key: str, custom_message: str = None, include_team_roster: bool = True):
        """Send targeted reminders to a specific team with team-specific information."""
        try:
            # Get current team members
            event_manager = self.bot.get_cog("EventManager")
            if not event_manager:
                logger.warning("EventManager not available for team reminders")
                return

            team_members = event_manager.events.get(team_key, [])
            if not team_members:
                logger.info(f"No members found for team {team_key}")
                return

            # Get team display name and scheduled time
            team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
            team_time = event_manager.event_times.get(team_key, DEFAULT_TIMES.get(team_key, "TBD"))

            # Create team roster if requested
            team_roster = ""
            if include_team_roster and len(team_members) > 1:
                # Try to get actual usernames
                roster_names = []
                for member_id in team_members:
                    try:
                        user = self.bot.get_user(int(member_id))
                        if user:
                            # Check if they have an IGN set
                            profile_cog = self.bot.get_cog("Profile")
                            if profile_cog and profile_cog.has_ign(user):
                                display_name = profile_cog.get_ign(user)
                            else:
                                display_name = user.display_name or user.name
                            roster_names.append(display_name)
                        else:
                            roster_names.append(f"User_{member_id}")
                    except:
                        roster_names.append(f"User_{member_id}")
                
                team_roster = f"\n**Team Roster:**\n" + "\n".join([f"• {name}" for name in roster_names])

            # Create the reminder content
            if custom_message:
                message = custom_message
            else:
                message = f"Reminder for {team_display}!"

            details = f"**Team:** {team_display}\n**Scheduled Time:** {team_time}{team_roster}"

            # Send reminder to each team member
            successful_sends = 0
            for member_id in team_members:
                try:
                    prefs = self.get_user_preferences(str(member_id))
                    
                    # Check if user wants team update notifications
                    if prefs.get("team_updates", True):
                        content = {
                            "message": message,
                            "details": details,
                            "team": team_key,
                            "team_display": team_display
                        }

                        await self.send_smart_notification(str(member_id), "team_updates", content)
                        successful_sends += 1
                    else:
                        logger.debug(f"User {member_id} has team updates disabled")
                        
                except Exception as e:
                    logger.error(f"Failed to send team reminder to {member_id}: {e}")

            logger.info(f"Sent team-specific reminders to {successful_sends}/{len(team_members)} members of {team_display}")
            return successful_sends

        except Exception as e:
            logger.error(f"Error sending team-specific reminders for {team_key}: {e}")
            return 0

    async def send_all_teams_reminders(self, custom_message: str = None, hours_before_event: int = 24):
        """Send reminders to all teams with members."""
        try:
            event_manager = self.bot.get_cog("EventManager")
            if not event_manager:
                return

            total_sent = 0
            reminder_summary = []

            for team_key in ["main_team", "team_2", "team_3"]:
                team_members = event_manager.events.get(team_key, [])
                if team_members:
                    team_message = custom_message or f"Don't forget about your upcoming event in {hours_before_event} hours!"
                    sent_count = await self.send_team_specific_reminders(
                        team_key, 
                        team_message, 
                        include_team_roster=True
                    )
                    total_sent += sent_count
                    
                    team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                    reminder_summary.append(f"{team_display}: {sent_count}/{len(team_members)} notified")

            logger.info(f"All teams reminder summary: {total_sent} total notifications sent")
            for summary_line in reminder_summary:
                logger.info(f"  {summary_line}")

            return total_sent, reminder_summary

        except Exception as e:
            logger.error(f"Error sending reminders to all teams: {e}")
            return 0, []

    async def notify_match_result(self, team_key: str, won: bool, players: List[str]):
        """Notify players about match results."""
        try:
            result_text = "Victory!" if won else "Defeat"
            emoji = EMOJIS["SUCCESS"] if won else EMOJIS["ERROR"]

            for player_id in players:
                content = {
                    "message": f"{emoji} {result_text}",
                    "won": won,
                    "details": f"Team: {team_key.replace('_', ' ').title()}"
                }

                await self.send_smart_notification(player_id, "result_notifications", content)

        except Exception as e:
            logger.error(f"Error notifying match result: {e}")

class NotificationSettingsView(discord.ui.View):
    def __init__(self, smart_notifications, user_id):
        super().__init__(timeout=300)
        self.smart_notifications = smart_notifications
        self.user_id = str(user_id)  # Ensure string consistency
        self._interaction_user_id = None  # Track who can interact

    async def update_embed(self, interaction):
        """Update the settings embed with current preferences."""
        prefs = self.smart_notifications.get_user_preferences(self.user_id)

        embed = discord.Embed(
            title="🔔 Notification Settings",
            description="Customize your notification preferences below:",
            color=COLORS["INFO"]
        )

        # Delivery method
        method_emoji = {"dm": "📱", "channel": "💬", "both": "📱💬"}
        embed.add_field(
            name="📤 Delivery Method",
            value=f"{method_emoji.get(prefs.get('method', 'channel'), '💬')} {prefs.get('method', 'channel').title()}",
            inline=True
        )

        # Timezone
        offset = prefs.get('timezone_offset', 0)
        embed.add_field(
            name="🌍 Timezone",
            value=f"UTC{offset:+d}",
            inline=True
        )

        # Quiet hours
        quiet_hours = prefs.get('quiet_hours', {'start': 22, 'end': 8})
        embed.add_field(
            name="🌙 Quiet Hours",
            value=f"{quiet_hours['start']:02d}:00 - {quiet_hours['end']:02d}:00",
            inline=True
        )

        # Notification types
        types_status = []
        types_status.append(f"📅 Event Reminders: {'✅' if prefs.get('event_reminders', True) else '❌'}")
        types_status.append(f"🏆 Match Results: {'✅' if prefs.get('result_notifications', True) else '❌'}")
        types_status.append(f"👥 Team Updates: {'✅' if prefs.get('team_updates', True) else '❌'}")

        embed.add_field(
            name="📋 Notification Types",
            value="\n".join(types_status),
            inline=False
        )

        embed.set_footer(text="Use the buttons below to modify your settings")

        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            # If interaction was already responded to, edit the original response
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error updating embed: {e}")
            # Fallback: try to send a new message if editing fails
            try:
                await interaction.followup.send(embed=embed, view=self, ephemeral=True)
            except:
                pass

    @discord.ui.select(
        placeholder="🚀 Choose delivery method...",
        options=[
            discord.SelectOption(label="Direct Messages", value="dm", emoji="📱", description="Send notifications via DM"),
            discord.SelectOption(label="Channel", value="channel", emoji="💬", description="Send in notification channel"),
            discord.SelectOption(label="Both", value="both", emoji="🔔", description="Send both DM and channel notifications")
        ]
    )
    async def delivery_method_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Ensure only the original user can interact
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your settings panel!", ephemeral=True)
            return
            
        method = select.values[0]
        await self.smart_notifications.update_user_preferences_async(self.user_id, {"method": method})
        await self.update_embed(interaction)

    @discord.ui.button(label="🌍 Set Timezone", style=discord.ButtonStyle.secondary)
    async def timezone_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your settings panel!", ephemeral=True)
            return
        await interaction.response.send_modal(TimezoneModal(self.smart_notifications, self.user_id, self))

    @discord.ui.button(label="🌙 Quiet Hours", style=discord.ButtonStyle.secondary)
    async def quiet_hours_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your settings panel!", ephemeral=True)
            return
        await interaction.response.send_modal(QuietHoursModal(self.smart_notifications, self.user_id, self))

    @discord.ui.button(label="📅 Toggle Events", style=discord.ButtonStyle.primary)
    async def toggle_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your settings panel!", ephemeral=True)
            return
        prefs = self.smart_notifications.get_user_preferences(self.user_id)
        new_value = not prefs.get('event_reminders', True)
        await self.smart_notifications.update_user_preferences_async(self.user_id, {"event_reminders": new_value})
        await self.update_embed(interaction)

    @discord.ui.button(label="🏆 Toggle Results", style=discord.ButtonStyle.primary)
    async def toggle_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your settings panel!", ephemeral=True)
            return
        prefs = self.smart_notifications.get_user_preferences(self.user_id)
        new_value = not prefs.get('result_notifications', True)
        await self.smart_notifications.update_user_preferences_async(self.user_id, {"result_notifications": new_value})
        await self.update_embed(interaction)

    @discord.ui.button(label="👥 Toggle Teams", style=discord.ButtonStyle.primary)
    async def toggle_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your settings panel!", ephemeral=True)
            return
        prefs = self.smart_notifications.get_user_preferences(self.user_id)
        new_value = not prefs.get('team_updates', True)
        await self.smart_notifications.update_user_preferences_async(self.user_id, {"team_updates": new_value})
        await self.update_embed(interaction)

class TimezoneModal(discord.ui.Modal):
    def __init__(self, smart_notifications, user_id, settings_view):
        super().__init__(title="🌍 Set Your Timezone")
        self.smart_notifications = smart_notifications
        self.user_id = user_id
        self.settings_view = settings_view

        self.timezone_input = discord.ui.TextInput(
            label="Timezone Offset (UTC)",
            placeholder="Enter offset from UTC (e.g., -5, +3, 0)",
            max_length=3,
            required=True
        )
        self.add_item(self.timezone_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            offset = int(self.timezone_input.value)
            if not (-12 <= offset <= 14):
                await interaction.response.send_message("❌ Timezone offset must be between -12 and +14", ephemeral=True)
                return

            await self.smart_notifications.update_user_preferences_async(self.user_id, {"timezone_offset": offset})
            await self.settings_view.update_embed(interaction)
        except ValueError:
            try:
                await interaction.response.send_message("❌ Please enter a valid number for timezone offset", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("❌ Please enter a valid number for timezone offset", ephemeral=True)

class QuietHoursModal(discord.ui.Modal):
    def __init__(self, smart_notifications, user_id, settings_view):
        super().__init__(title="🌙 Set Quiet Hours")
        self.smart_notifications = smart_notifications
        self.user_id = user_id
        self.settings_view = settings_view

        self.start_hour = discord.ui.TextInput(
            label="Start Hour (24h format)",
            placeholder="e.g., 22 for 10 PM",
            max_length=2,
            required=True
        )
        self.end_hour = discord.ui.TextInput(
            label="End Hour (24h format)", 
            placeholder="e.g., 8 for 8 AM",
            max_length=2,
            required=True
        )
        self.add_item(self.start_hour)
        self.add_item(self.end_hour)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start = int(self.start_hour.value)
            end = int(self.end_hour.value)

            if not (0 <= start <= 23) or not (0 <= end <= 23):
                await interaction.response.send_message("❌ Hours must be between 0-23", ephemeral=True)
                return

            await self.smart_notifications.update_user_preferences_async(
                self.user_id, 
                {"quiet_hours": {"start": start, "end": end}}
            )
            await self.settings_view.update_embed(interaction)
        except ValueError:
            try:
                await interaction.response.send_message("❌ Hours must be between 0-23", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("❌ Hours must be between 0-23", ephemeral=True)

class NotificationsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.smart_notifications = SmartNotifications(bot)
        self.process_queue.start()

    def cog_unload(self):
        self.process_queue.cancel()

    @tasks.loop(minutes=10)
    async def process_queue(self):
        """Process notification queue periodically."""
        await self.smart_notifications.process_notification_queue()

    @process_queue.before_loop
    async def before_process_queue(self):
        await self.bot.wait_until_ready()

    @commands.group(name="notifications", aliases=["notif"])
    async def notifications(self, ctx):
        """Notification preference commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @notifications.command(name="settings", aliases=["config", "setup"])
    async def show_settings(self, ctx):
        """Open the interactive notification settings panel."""
        view = NotificationSettingsView(self.smart_notifications, ctx.author.id)

        # Create the embed manually since update_embed expects an interaction
        prefs = self.smart_notifications.get_user_preferences(ctx.author.id)

        embed = discord.Embed(
            title="🔔 Notification Settings",
            description="Customize your notification preferences below:",
            color=COLORS["INFO"]
        )

        # Delivery method
        method_emoji = {"dm": "📱", "channel": "💬", "both": "📱💬"}
        embed.add_field(
            name="📤 Delivery Method",
            value=f"{method_emoji.get(prefs.get('method', 'channel'), '💬')} {prefs.get('method', 'channel').title()}",
            inline=True
        )

        # Timezone
        offset = prefs.get('timezone_offset', 0)
        embed.add_field(
            name="🌍 Timezone",
            value=f"UTC{offset:+d}",
            inline=True
        )

        # Quiet hours
        quiet_hours = prefs.get('quiet_hours', {'start': 22, 'end': 8})
        embed.add_field(
            name="🌙 Quiet Hours",
            value=f"{quiet_hours['start']:02d}:00 - {quiet_hours['end']:02d}:00",
            inline=True
        )

        # Notification types
        types_status = []
        types_status.append(f"📅 Event Reminders: {'✅' if prefs.get('event_reminders', True) else '❌'}")
        types_status.append(f"🏆 Match Results: {'✅' if prefs.get('result_notifications', True) else '❌'}")
        types_status.append(f"👥 Team Updates: {'✅' if prefs.get('team_updates', True) else '❌'}")

        embed.add_field(
            name="📋 Notification Types",
            value="\n".join(types_status),
            inline=False
        )

        embed.set_footer(text="Use the buttons below to modify your settings")

        # Send the message with the view - this is a regular command context
        await ctx.send(embed=embed, view=view)

    @notifications.command(name="test", aliases=["testdm"])
    async def test_notifications(self, ctx):
        """Test if the bot can send you a DM and show your notification preferences."""
        user_id = str(ctx.author.id)
        prefs = self.smart_notifications.get_user_preferences(user_id)
        
        # Create test embed
        embed = discord.Embed(
            title="🧪 Notification Test",
            description="This is a test notification to verify DM functionality.",
            color=COLORS["INFO"]
        )
        embed.add_field(
            name="Your Current Settings",
            value=f"**Method:** {prefs.get('method', 'channel')}\n**Event Reminders:** {'✅' if prefs.get('event_reminders', True) else '❌'}\n**Team Updates:** {'✅' if prefs.get('team_updates', True) else '❌'}",
            inline=False
        )
        
        # Try to send DM
        dm_success = False
        dm_error = None
        try:
            await ctx.author.send(embed=embed)
            dm_success = True
            await ctx.send("✅ **DM Test Successful!** Check your direct messages.")
        except discord.Forbidden:
            dm_error = "DMs are disabled or blocked"
            await ctx.send("❌ **DM Test Failed:** You have DMs disabled or have blocked the bot.")
        except discord.HTTPException as e:
            dm_error = f"HTTP error: {e}"
            await ctx.send(f"❌ **DM Test Failed:** HTTP error - {e}")
        except Exception as e:
            dm_error = f"Unknown error: {e}"
            await ctx.send(f"❌ **DM Test Failed:** {e}")
        
        # Log the test result
        logger.info(f"DM test for {ctx.author} ({user_id}): Success={dm_success}, Error={dm_error}")
        
        # Show current preferences in channel
        pref_embed = discord.Embed(
            title="📋 Your Notification Preferences",
            color=COLORS["INFO"]
        )
        pref_embed.add_field(
            name="Delivery Method",
            value=prefs.get('method', 'channel'),
            inline=True
        )
        pref_embed.add_field(
            name="Event Reminders",
            value="✅ Enabled" if prefs.get('event_reminders', True) else "❌ Disabled",
            inline=True
        )
        pref_embed.add_field(
            name="Team Updates",
            value="✅ Enabled" if prefs.get('team_updates', True) else "❌ Disabled",
            inline=True
        )
        pref_embed.set_footer(text="Use !notifications settings to modify these preferences")
        
        await ctx.send(embed=pref_embed)

    @notifications.command(name="remind", aliases=["teamreminder"])
    @commands.check(lambda ctx: any(role.id in [1395129965405540452, 1258214711124688967] for role in ctx.author.roles))
    async def send_team_reminder(self, ctx, team: str = None, *, message: str = None):
        """Send a targeted reminder to a specific team or all teams.
        
        Usage:
        !notifications remind main_team Don't forget about tonight's event!
        !notifications remind all Event starts in 2 hours - be ready!
        !notifications remind team_2
        """
        if team is None:
            embed = discord.Embed(
                title="📢 Team Reminder Command",
                description="Send targeted reminders to specific teams.",
                color=COLORS["INFO"]
            )
            embed.add_field(
                name="Usage",
                value="```\n!notifications remind <team> [message]\n!notifications remind all [message]\n```",
                inline=False
            )
            embed.add_field(
                name="Teams",
                value="• `main_team` - Main Team\n• `team_2` - Team 2\n• `team_3` - Team 3\n• `all` - All teams with members",
                inline=False
            )
            embed.add_field(
                name="Examples",
                value="```\n!notifications remind main_team Event in 1 hour!\n!notifications remind all Don't forget tonight's match\n!notifications remind team_2\n```",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        # Send to all teams
        if team.lower() == "all":
            total_sent, summary = await self.smart_notifications.send_all_teams_reminders(message)
            
            embed = discord.Embed(
                title="📢 Team Reminders Sent",
                description=f"Sent reminders to all teams with members.",
                color=COLORS["SUCCESS"]
            )
            embed.add_field(
                name="Summary",
                value="\n".join(summary) or "No teams have members currently.",
                inline=False
            )
            embed.add_field(
                name="Total Notifications",
                value=f"{total_sent} notifications sent",
                inline=True
            )
            if message:
                embed.add_field(
                    name="Custom Message",
                    value=f"```{message}```",
                    inline=False
                )
            await ctx.send(embed=embed)
            return

        # Validate team name
        valid_teams = ["main_team", "team_2", "team_3"]
        if team not in valid_teams:
            embed = discord.Embed(
                title="❌ Invalid Team",
                description=f"Team `{team}` not found.",
                color=COLORS["DANGER"]
            )
            embed.add_field(
                name="Valid Teams",
                value="\n".join([f"• `{t}`" for t in valid_teams]),
                inline=False
            )
            await ctx.send(embed=embed)
            return

        # Send to specific team
        sent_count = await self.smart_notifications.send_team_specific_reminders(
            team, 
            message, 
            include_team_roster=True
        )

        team_display = TEAM_DISPLAY.get(team, team.replace('_', ' ').title())
        
        # Get team member count
        event_manager = self.bot.get_cog("EventManager")
        team_members = event_manager.events.get(team, []) if event_manager else []

        embed = discord.Embed(
            title="📢 Team Reminder Sent",
            description=f"Sent reminder to {team_display}",
            color=COLORS["SUCCESS"] if sent_count > 0 else COLORS["WARNING"]
        )
        embed.add_field(
            name="Notifications Sent",
            value=f"{sent_count}/{len(team_members)} members notified",
            inline=True
        )
        if message:
            embed.add_field(
                name="Custom Message",
                value=f"```{message}```",
                inline=False
            )
        if sent_count == 0 and len(team_members) > 0:
            embed.add_field(
                name="Note",
                value="Some members may have team notifications disabled.",
                inline=False
            )
        elif len(team_members) == 0:
            embed.description = f"No members currently signed up for {team_display}"
            embed.color = COLORS["WARNING"]

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NotificationsCog(bot))

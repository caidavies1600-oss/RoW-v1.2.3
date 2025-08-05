import json
import discord
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from discord.ext import tasks, commands
import asyncio

from utils.logger import setup_logger
from utils.data_manager import DataManager
from config.constants import FILES, COLORS, EMOJIS

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
        if hasattr(self.data_manager, 'sheets_manager') and self.data_manager.sheets_manager:
            try:
                sheets_prefs = self.data_manager.sheets_manager.load_notification_preferences_from_sheets()
                if sheets_prefs:
                    logger.info("✅ Loaded notification preferences from Google Sheets")
                    return sheets_prefs
            except Exception as e:
                logger.warning(f"Failed to load notification preferences from Sheets: {e}")

        # Fallback to JSON file
        json_prefs = self.data_manager.load_json("data/notification_preferences.json", default_prefs)
        logger.info("📄 Loaded notification preferences from JSON file")
        return json_prefs

    def save_notification_preferences(self):
        """Save notification preferences to both JSON and Google Sheets."""
        # Save to JSON file
        json_success = self.data_manager.save_json("data/notification_preferences.json", self.notification_prefs, sync_to_sheets=False)

        # Sync to Google Sheets
        sheets_success = True
        if hasattr(self.data_manager, 'sheets_manager') and self.data_manager.sheets_manager:
            try:
                sheets_success = self.data_manager.sheets_manager.sync_notification_preferences(self.notification_prefs)
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
            if user_id not in self.notification_prefs["users"]:
                self.notification_prefs["users"][user_id] = {}

            self.notification_prefs["users"][user_id].update(preferences)
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

            # Adjust current time for user's timezone
            current_utc = datetime.utcnow()
            user_time = current_utc + timedelta(hours=timezone_offset)
            current_hour = user_time.hour

            start_hour = quiet_hours["start"]
            end_hour = quiet_hours["end"]

            if start_hour <= end_hour:
                return start_hour <= current_hour <= end_hour
            else:  # Quiet hours span midnight
                return current_hour >= start_hour or current_hour <= end_hour

        except Exception as e:
            logger.error(f"Error checking quiet hours for {user_id}: {e}")
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

                if method == "dm" or method == "both":
                    try:
                        await user.send(embed=embed)
                        logger.info(f"Sent DM notification to {user_id}")
                    except discord.Forbidden:
                        logger.warning(f"Cannot send DM to {user_id}, falling back to channel")
                        method = "channel"

                if method == "channel" or method == "both":
                    # Send to main notification channel
                    from config.constants import ALERT_CHANNEL_ID
                    channel = self.bot.get_channel(ALERT_CHANNEL_ID)
                    if channel:
                        await channel.send(f"<@{user_id}>", embed=embed)
                        logger.info(f"Sent channel notification to {user_id}")

            except Exception as e:
                logger.error(f"Failed to send notification to {user_id}: {e}")

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
        self.user_id = user_id

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

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="🚀 Choose delivery method...",
        options=[
            discord.SelectOption(label="Direct Messages", value="dm", emoji="📱", description="Send notifications via DM"),
            discord.SelectOption(label="Channel", value="channel", emoji="💬", description="Send in notification channel"),
            discord.SelectOption(label="Both", value="both", emoji="🔔", description="Send both DM and channel notifications")
        ]
    )
    async def delivery_method_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        method = select.values[0]
        self.smart_notifications.update_user_preferences(self.user_id, {"method": method})
        await self.update_embed(interaction)

    @discord.ui.button(label="🌍 Set Timezone", style=discord.ButtonStyle.secondary)
    async def timezone_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TimezoneModal(self.smart_notifications, self.user_id, self))

    @discord.ui.button(label="🌙 Quiet Hours", style=discord.ButtonStyle.secondary)
    async def quiet_hours_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuietHoursModal(self.smart_notifications, self.user_id, self))

    @discord.ui.button(label="📅 Toggle Events", style=discord.ButtonStyle.primary)
    async def toggle_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefs = self.smart_notifications.get_user_preferences(self.user_id)
        new_value = not prefs.get('event_reminders', True)
        self.smart_notifications.update_user_preferences(self.user_id, {"event_reminders": new_value})
        await self.update_embed(interaction)

    @discord.ui.button(label="🏆 Toggle Results", style=discord.ButtonStyle.primary)
    async def toggle_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefs = self.smart_notifications.get_user_preferences(self.user_id)
        new_value = not prefs.get('result_notifications', True)
        self.smart_notifications.update_user_preferences(self.user_id, {"result_notifications": new_value})
        await self.update_embed(interaction)

    @discord.ui.button(label="👥 Toggle Teams", style=discord.ButtonStyle.primary)
    async def toggle_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefs = self.smart_notifications.get_user_preferences(self.user_id)
        new_value = not prefs.get('team_updates', True)
        self.smart_notifications.update_user_preferences(self.user_id, {"team_updates": new_value})
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

            self.smart_notifications.update_user_preferences(self.user_id, {"timezone_offset": offset})
            await self.settings_view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for timezone offset", ephemeral=True)

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

            self.smart_notifications.update_user_preferences(
                self.user_id, 
                {"quiet_hours": {"start": start, "end": end}}
            )
            await self.settings_view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_modal(QuietHoursModal(self.smart_notifications, self.user_id, self))

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

async def setup(bot):
    await bot.add_cog(NotificationsCog(bot))
# services/notifications.py

import discord
from discord.ext import tasks, commands
import datetime
import json
import os
from utils.logger import setup_logger

logger = setup_logger("notifications")

async def setup(bot):
    """Setup function required for Discord.py cogs."""
    await bot.add_cog(NotificationService(bot))

class NotificationService(commands.Cog):
    def __init__(self, bot, event_file="data/events.json", alert_channel_id=None):
        self.bot = bot
        self.event_file = event_file
        self.alert_channel_id = alert_channel_id or 1257673327032664145  # Default fallback
        self.alerted = set()
        self.check_alerts.start()

    def load_events(self):
        if os.path.exists(self.event_file):
            with open(self.event_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {"main_team": [], "team_2": [], "team_3": []}
        return {"main_team": [], "team_2": [], "team_3": []}

    def stop(self):
        self.check_alerts.cancel()

    @tasks.loop(minutes=1)
    async def check_alerts(self):
        now = datetime.datetime.utcnow()

        # Define expected event times (UTC)
        upcoming = {
            "team_2": datetime.datetime.combine(now.date(), datetime.time(14, 0)) + datetime.timedelta(days=(6 - now.weekday()) % 7),  # Sunday 14 UTC
            "team_3": datetime.datetime.combine(now.date(), datetime.time(20, 0)) + datetime.timedelta(days=(6 - now.weekday()) % 7),  # Sunday 20 UTC
            "main_team": datetime.datetime.combine(now.date(), datetime.time(14, 0)) + datetime.timedelta(days=(5 - now.weekday()) % 7),  # Saturday 14 UTC
        }

        events = self.load_events()
        channel = self.bot.get_channel(self.alert_channel_id)
        if not channel:
            return

        for team, event_time in upcoming.items():
            delta = event_time - now
            if 3590 <= delta.total_seconds() <= 3660 and team not in self.alerted:
                mentions = " ".join(
                    f"<@{user.id}>"
                    for user in channel.guild.members
                    if user.display_name in events.get(team, [])
                )
                if mentions:
                    await channel.send(
                        f"⏰ **Reminder:** `{team.replace('_', ' ').title()}` starts in 1 hour!\n{mentions}"
                    )
                    self.alerted.add(team)

    @check_alerts.before_loop
    async def before_check_alerts(self):
        await self.bot.wait_until_ready()

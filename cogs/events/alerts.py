# cogs/events/alerts.py

import discord
from discord.ext import tasks, commands
import datetime
import json
import os

from config.constants import ALERT_CHANNEL_ID, FILES

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alerted = set()
        self.check_alerts.start()

    def cog_unload(self):
        self.check_alerts.cancel()

    def load_events(self):
        event_path = FILES["EVENTS"]
        if os.path.exists(event_path):
            with open(event_path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {"main_team": [], "team_2": [], "team_3": []}
        return {"main_team": [], "team_2": [], "team_3": []}

    @tasks.loop(minutes=1)
    async def check_alerts(self):
        now = datetime.datetime.utcnow()
        upcoming = {
            "team_2": datetime.datetime.combine(now.date(), datetime.time(14, 0)) + datetime.timedelta(days=(6 - now.weekday()) % 7),  # Sunday 14 UTC
            "team_3": datetime.datetime.combine(now.date(), datetime.time(20, 0)) + datetime.timedelta(days=(6 - now.weekday()) % 7),  # Sunday 20 UTC
            "main_team": datetime.datetime.combine(now.date(), datetime.time(14, 0)) + datetime.timedelta(days=(5 - now.weekday()) % 7),  # Saturday 14 UTC
        }

        events = self.load_events()
        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
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
                if not mentions:
                    continue

                await channel.send(
                    f"⏰ **Reminder:** `{team.replace('_', ' ').title()}` starts in **1 hour!**\n{mentions}"
                )
                self.alerted.add(team)

        # Reset alerted set after the event starts
        for team, event_time in upcoming.items():
            if (now - event_time).total_seconds() > 3600:
                self.alerted.discard(team)

    @check_alerts.before_loop
    async def before_alerts(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Alerts(bot))

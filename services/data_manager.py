import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import logging

from config.constants import FILES, BOT_ADMIN_ID, ALERT_CHANNEL_ID
from utils.data_manager import DataManager
from utils.logger import setup_logger
from utils.helpers import Helpers

logger = setup_logger("event_manager")


class EventManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = DataManager.load_json(FILES["EVENTS"])
        self.blocked_users = DataManager.load_json(FILES["BLOCKED"])
        self.unblock_expired_loop.start()

    def cog_unload(self):
        self.unblock_expired_loop.cancel()

    @tasks.loop(minutes=60)
    async def unblock_expired_loop(self):
        now = datetime.utcnow()
        expired = []

        for user_id, info in self.blocked_users.items():
            try:
                blocked_at = datetime.fromisoformat(info.get("blocked_at"))
                duration = info.get("ban_duration_days", 0)
                expires_at = blocked_at + timedelta(days=duration)
                if now >= expires_at:
                    expired.append(user_id)
            except Exception as e:
                logger.warning(f"Skipping invalid blocked entry for {user_id}: {e}")

        if expired:
            for user_id in expired:
                user_obj = await self.get_user_object(user_id)
                blocked_by = self.blocked_users[user_id].get("blocked_by", "Unknown")
                await self.notify_unblock(user_obj, blocked_by, auto=True)
                self.blocked_users.pop(user_id, None)

            DataManager.save_json(FILES["BLOCKED"], self.blocked_users)
            logger.info(f"✅ Auto-unblocked users: {expired}")

    @unblock_expired_loop.before_loop
    async def before_unblock_loop(self):
        await self.bot.wait_until_ready()

    async def manual_unblock(self, user_id: str, unblocked_by: str):
        """Call this from an admin command to manually unblock a user."""
        user_obj = await self.get_user_object(user_id)
        if user_id in self.blocked_users:
            self.blocked_users.pop(user_id)
            DataManager.save_json(FILES["BLOCKED"], self.blocked_users)
            await self.notify_unblock(user_obj, unblocked_by, auto=False)
            logger.info(f"✅ Manually unblocked {user_id} by {unblocked_by}")
            return True
        return False

    async def notify_unblock(self, user: discord.User, unblocked_by: str, auto: bool = False):
        admin = self.bot.get_user(BOT_ADMIN_ID)
        alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        tag = user.mention if user else f"<@{user.id}>"
        reason = "⏰ auto-expired" if auto else f"🛠 manually by `{unblocked_by}`"

        # DM admin
        if admin:
            try:
                await admin.send(f"✅ `{user}` ({tag}) has been unblocked ({reason}).")
            except Exception as e:
                logger.warning(f"Could not DM admin about unblock: {e}")

        # Announce in alert channel
        if alert_channel:
            try:
                await alert_channel.send(f"🔓 {tag} has been unblocked ({reason}).")
            except Exception as e:
                logger.warning(f"Could not announce unblock: {e}")

    async def get_user_object(self, user_id):
        user_id = int(user_id)
        user = self.bot.get_user(user_id)
        if not user:
            try:
                user = await self.bot.fetch_user(user_id)
            except Exception as e:
                logger.warning(f"Failed to fetch user {user_id}: {e}")
                return None
        return user

    # Add other methods (signup, event posting, etc.) here...


async def setup(bot):
    await bot.add_cog(EventManager(bot))

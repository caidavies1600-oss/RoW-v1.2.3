
"""Common helper functions."""

import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.constants import TEAM_DISPLAY, EMOJIS, ALERT_CHANNEL_ID
import logging

def days_until_expiry(expiry_timestamp: str, duration_days: int = 0) -> int:
    """Calculate how many days remain until the expiry timestamp (ISO format)."""
    try:
        blocked_at = datetime.fromisoformat(expiry_timestamp)
        expiry = blocked_at + timedelta(days=duration_days)
        now = datetime.utcnow()
        delta = expiry - now
        return max(delta.days, 0)
    except Exception:
        return 0  # Default to 0 if invalid format

class Helpers:
    """Collection of helper functions."""

    @staticmethod
    def format_team_name(team_key: str) -> str:
        """Format team key into display name."""
        return TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())

    @staticmethod
    def calculate_win_rate(wins: int, losses: int) -> float:
        """Returns win rate percentage rounded to 1 decimal."""
        total = wins + losses
        if total == 0:
            return 0.0
        return round((wins / total) * 100, 1)

    @staticmethod
    def create_embed(
        title: str,
        description: str = None,
        color: int = discord.Color.blue(),
        fields: list = None
    ) -> discord.Embed:
        """Create a standardized embed."""
        embed = discord.Embed(title=title, description=description, color=color)

        if fields:
            for field in fields:
                embed.add_field(**field)

        return embed

    @staticmethod
    def format_user_list(users: list, max_length: int = 1000) -> str:
        """Format a list of users for display."""
        if not users:
            return "No members yet."

        formatted = "\n".join([f"{i+1}. {user}" for i, user in enumerate(users)])

        if len(formatted) > max_length:
            formatted = formatted[:max_length-10] + "\n... (truncated)"

        return formatted

    @staticmethod
    def calculate_expiry(days: int) -> str:
        """Calculate expiry datetime as ISO string."""
        return (datetime.utcnow() + timedelta(days=days)).isoformat()

    @staticmethod
    def is_expired(expiry_str: str) -> bool:
        """Check if an ISO datetime string is expired."""
        try:
            expiry = datetime.fromisoformat(expiry_str)
            return datetime.utcnow() > expiry
        except:
            return True  # Assume expired if can't parse

    @staticmethod
    def format_time_remaining(expiry_str: str) -> str:
        """Format time remaining until expiry."""
        try:
            expiry = datetime.fromisoformat(expiry_str)
            remaining = expiry - datetime.utcnow()

            if remaining.total_seconds() <= 0:
                return "Expired"

            days = remaining.days
            hours = remaining.seconds // 3600

            if days > 0:
                return f"{days}d {hours}h"
            else:
                return f"{hours}h"
        except:
            return "Invalid"

    @staticmethod
    def days_until_expiry(expiry_timestamp: str, duration_days: int) -> int:
        """Calculate how many days remain until expiry."""
        return days_until_expiry(expiry_timestamp, duration_days)

    @staticmethod
    async def create_fake_context(bot):
        """Creates a fake context object to simulate a command being run by the bot itself."""
        from discord.ext import commands

        logging.info("🔍 DEBUG: Starting create_fake_context")
        logging.info(f"🔧 ALERT_CHANNEL_ID from config: {ALERT_CHANNEL_ID} (type: {type(ALERT_CHANNEL_ID)})")

        for guild in bot.guilds:
            logging.info(f"📡 Connected Guild: {guild.name} (ID: {guild.id})")
            for channel in guild.text_channels:
                logging.info(f" - Found Text Channel: {channel.name} (ID: {channel.id})")
                if channel.id == ALERT_CHANNEL_ID:
                    fake_message = await channel.send("📢 Starting event...")
                    ctx = await bot.get_context(fake_message, cls=commands.Context)
                    return ctx

        raise ValueError("⚠️ ALERT_CHANNEL_ID does not match any channel in this guild.")

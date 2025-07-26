"""Common helper functions."""

import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.constants import TEAM_DISPLAY, EMOJIS, ALERT_CHANNEL_IDS
import logging

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
    def format_user_list(users: list, max_length: int = 1000, bot=None, guild=None) -> str:
        """Format a list of users for display."""
        if not users:
            return "No members yet."

        formatted_users = []
        for i, user in enumerate(users):
            try:
                if isinstance(user, (int, str)) and str(user).isdigit():
                    # It's a user ID, try to get display name
                    user_id = int(user)
                    
                    if bot and guild:
                        # Try to get user object for display name
                        user_obj = guild.get_member(user_id) or bot.get_user(user_id)
                        if user_obj:
                            # Check for IGN
                            profile_cog = bot.get_cog("Profile")
                            if profile_cog and profile_cog.has_ign(user_obj):
                                display_name = profile_cog.get_ign(user_obj)
                            else:
                                display_name = user_obj.display_name
                            formatted_users.append(f"{i+1}. {display_name}")
                        else:
                            # Fallback to mention
                            formatted_users.append(f"{i+1}. <@{user_id}>")
                    else:
                        # No bot/guild context, use mention
                        formatted_users.append(f"{i+1}. <@{user_id}>")
                else:
                    # It's already a display name/IGN
                    formatted_users.append(f"{i+1}. {user}")
            except Exception as e:
                # Fallback for any errors
                formatted_users.append(f"{i+1}. Unknown User")

        formatted = "\n".join(formatted_users)

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
    def days_until_expiry(blocked_at_str: str, duration_days: int) -> int:
        """Calculate how many days remain until expiry."""
        try:
            blocked_at = datetime.fromisoformat(blocked_at_str)
            expiry = blocked_at + timedelta(days=duration_days)
            remaining = expiry - datetime.utcnow()
            return max(remaining.days, 0)
        except Exception:
            return 0  # Default to 0 if invalid format

    @staticmethod
    async def create_fake_context(bot):
        """Creates a fake context object to simulate a command being run by the bot itself."""
        from discord.ext import commands

        logging.info("🔍 DEBUG: Starting create_fake_context")
        logging.info(f"🔧 ALERT_CHANNEL_IDS from config: {ALERT_CHANNEL_IDS}")

        # Try to find any of the configured alert channels
        for channel_id in ALERT_CHANNEL_IDS:
            for guild in bot.guilds:
                logging.info(f"📡 Checking Guild: {guild.name} (ID: {guild.id})")
                channel = guild.get_channel(channel_id)
                if channel:
                    logging.info(f"✅ Found channel: {channel.name} in {guild.name}")
                    # Create a temporary message to build context from
                    fake_message = await channel.send("📢 Starting automated task...")
                    ctx = await bot.get_context(fake_message, cls=commands.Context)
                    # Delete the temporary message
                    try:
                        await fake_message.delete()
                    except:
                        pass  # Don't fail if we can't delete
                    return ctx

        # If we get here, none of the channels were found
        available_channels = []
        for guild in bot.guilds:
            for channel in guild.text_channels:
                available_channels.append(f"{guild.name}#{channel.name} (ID: {channel.id})")

        error_msg = f"⚠️ None of the configured ALERT_CHANNEL_IDS {ALERT_CHANNEL_IDS} were found.\n"
        error_msg += f"Available channels:\n" + "\n".join(available_channels[:10])
        
        logging.error(error_msg)
        raise ValueError(error_msg)

    @staticmethod
    def sanitize_user_input(text: str, max_length: int = 100) -> str:
        """Sanitize user input for safe storage and display."""
        if not isinstance(text, str):
            return ""
        
        # Strip whitespace and limit length
        sanitized = text.strip()[:max_length]
        
        # Remove any potential harmful characters (basic sanitization)
        forbidden_chars = ['@everyone', '@here', '```']
        for char in forbidden_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized

    @staticmethod
    def safe_mention(user_id: int, fallback: str = "Unknown User") -> str:
        """Create a safe user mention that won't break if user doesn't exist."""
        try:
            return f"<@{int(user_id)}>"
        except (ValueError, TypeError):
            return fallback

    @staticmethod
    def validate_json_data(data: Any, expected_type: type, default: Any = None) -> Any:
        """Validate JSON data matches expected type, return default if invalid."""
        if isinstance(data, expected_type):
            return data
        
        logging.warning(f"JSON data validation failed. Expected {expected_type}, got {type(data)}. Using default.")
        return default if default is not None else expected_type()

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format seconds into human readable duration."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"

    @staticmethod
    def chunk_list(lst: list, chunk_size: int) -> list:
        """Split a list into chunks of specified size."""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to max length with optional suffix."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    async def safe_send_message(channel, content: str = None, embed: discord.Embed = None, 
                              view: discord.ui.View = None) -> Optional[discord.Message]:
        """Safely send a message with error handling."""
        try:
            return await channel.send(content=content, embed=embed, view=view)
        except discord.Forbidden:
            logging.warning(f"No permission to send message to {channel}")
            return None
        except discord.HTTPException as e:
            logging.warning(f"HTTP error sending message to {channel}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error sending message to {channel}: {e}")
            return None

    @staticmethod
    def get_team_emoji(team_key: str) -> str:
        """Get emoji for team based on team key."""
        team_emojis = {
            "main_team": "🏆",
            "team_2": "🔸", 
            "team_3": "🔹"
        }
        return team_emojis.get(team_key, "⚫")

    @staticmethod
    def format_signup_count(current: int, maximum: int) -> str:
        """Format signup count with appropriate emoji based on capacity."""
        percentage = (current / maximum) * 100 if maximum > 0 else 0
        
        if percentage >= 100:
            emoji = "🔴"  # Full
        elif percentage >= 80:
            emoji = "🟡"  # Nearly full
        else:
            emoji = "🟢"  # Available
            
        return f"{emoji} {current}/{maximum}"
"""Rate limiting system to prevent spam and abuse."""

import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from discord.ext import commands
from utils.logger import setup_logger

logger = setup_logger("rate_limiter")

class RateLimiter:
    """Rate limiter with configurable limits per user/command."""

    def __init__(self):
        # Store user activity: user_id -> deque of timestamps
        self.user_activity = defaultdict(lambda: deque())
        # Store command cooldowns: (user_id, command) -> last_used_time
        self.command_cooldowns = {}
        # Store button activity: user_id -> deque of timestamps
        self.button_activity = defaultdict(lambda: deque())

        # Rate limiting configuration
        self.limits = {
            "commands_per_minute": 10,
            "commands_per_hour": 100,
            "buttons_per_minute": 5,
            "button_spam_window": 2,  # seconds
            "button_spam_limit": 3,   # max clicks in window
            "cooldown_commands": {
                "startevent": 300,     # 5 minutes
                "win": 60,             # 1 minute  
                "loss": 60,            # 1 minute
                "block": 30,           # 30 seconds
                "unblock": 30,         # 30 seconds
            }
        }

    def check_command_rate_limit(self, user_id: int, command_name: str) -> Tuple[bool, Optional[str]]:
        """Check if user can execute a command."""
        current_time = time.time()

        # Check global command rate limits
        user_commands = self.user_activity[user_id]

        # Remove old entries (older than 1 hour)
        while user_commands and current_time - user_commands[0] > 3600:
            user_commands.popleft()

        # Check per-minute limit
        recent_commands = sum(1 for t in user_commands if current_time - t <= 60)
        if recent_commands >= self.limits["commands_per_minute"]:
            return False, f"Rate limit: max {self.limits['commands_per_minute']} commands per minute"

        # Check per-hour limit
        if len(user_commands) >= self.limits["commands_per_hour"]:
            return False, f"Rate limit: max {self.limits['commands_per_hour']} commands per hour"

        # Check command-specific cooldowns
        if command_name in self.limits["cooldown_commands"]:
            cooldown_key = (user_id, command_name)
            if cooldown_key in self.command_cooldowns:
                last_used = self.command_cooldowns[cooldown_key]
                cooldown_time = self.limits["cooldown_commands"][command_name]
                time_left = cooldown_time - (current_time - last_used)

                if time_left > 0:
                    return False, f"Command cooldown: {int(time_left)}s remaining"

        # All checks passed - record the command
        user_commands.append(current_time)
        if command_name in self.limits["cooldown_commands"]:
            self.command_cooldowns[(user_id, command_name)] = current_time

        return True, None

    def check_button_rate_limit(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Check if user can click buttons."""
        current_time = time.time()

        user_buttons = self.button_activity[user_id]

        # Remove old entries (older than 1 minute)
        while user_buttons and current_time - user_buttons[0] > 60:
            user_buttons.popleft()

        # Check per-minute limit
        if len(user_buttons) >= self.limits["buttons_per_minute"]:
            return False, f"Button rate limit: max {self.limits['buttons_per_minute']} clicks per minute"

        # Check spam detection (rapid clicking)
        spam_window = self.limits["button_spam_window"]
        recent_clicks = sum(1 for t in user_buttons if current_time - t <= spam_window)

        if recent_clicks >= self.limits["button_spam_limit"]:
            return False, f"Button spam detected: slow down!"

        # Record the button click
        user_buttons.append(current_time)
        return True, None

    def is_user_rate_limited(self, user_id: int) -> bool:
        """Check if user is currently rate limited."""
        current_time = time.time()

        # Check if they've hit any limits recently
        user_commands = self.user_activity[user_id]
        recent_commands = sum(1 for t in user_commands if current_time - t <= 60)

        return recent_commands >= self.limits["commands_per_minute"]

    def get_user_stats(self, user_id: int) -> Dict:
        """Get rate limiting stats for a user."""
        current_time = time.time()

        user_commands = self.user_activity[user_id]
        user_buttons = self.button_activity[user_id]

        # Count recent activity
        commands_last_minute = sum(1 for t in user_commands if current_time - t <= 60)
        commands_last_hour = sum(1 for t in user_commands if current_time - t <= 3600)
        buttons_last_minute = sum(1 for t in user_buttons if current_time - t <= 60)

        # Check active cooldowns
        active_cooldowns = {}
        for (uid, cmd), last_used in self.command_cooldowns.items():
            if uid == user_id:
                cooldown_time = self.limits["cooldown_commands"].get(cmd, 0)
                time_left = cooldown_time - (current_time - last_used)
                if time_left > 0:
                    active_cooldowns[cmd] = int(time_left)

        return {
            "commands_last_minute": commands_last_minute,
            "commands_last_hour": commands_last_hour,
            "buttons_last_minute": buttons_last_minute,
            "active_cooldowns": active_cooldowns,
            "is_rate_limited": self.is_user_rate_limited(user_id)
        }

    def reset_user_limits(self, user_id: int):
        """Reset rate limits for a user (admin function)."""
        if user_id in self.user_activity:
            del self.user_activity[user_id]
        if user_id in self.button_activity:
            del self.button_activity[user_id]

        # Remove command cooldowns for this user
        to_remove = [key for key in self.command_cooldowns.keys() if key[0] == user_id]
        for key in to_remove:
            del self.command_cooldowns[key]

        logger.info(f"🔄 Reset rate limits for user {user_id}")

    def get_global_stats(self) -> Dict:
        """Get global rate limiting statistics."""
        current_time = time.time()

        active_users = len([uid for uid, activity in self.user_activity.items() 
                           if any(current_time - t <= 3600 for t in activity)])

        rate_limited_users = len([uid for uid in self.user_activity.keys() 
                                 if self.is_user_rate_limited(uid)])

        total_commands_hour = sum(sum(1 for t in activity if current_time - t <= 3600) 
                                 for activity in self.user_activity.values())

        active_cooldowns = len([cd for cd in self.command_cooldowns.values() 
                               if current_time - cd <= max(self.limits["cooldown_commands"].values())])

        return {
            "active_users_last_hour": active_users,
            "rate_limited_users": rate_limited_users,
            "total_commands_last_hour": total_commands_hour,
            "active_cooldowns": active_cooldowns
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

def create_rate_limit_check():
    """Create a command check for rate limiting."""
    async def rate_limit_check(ctx):
        allowed, message = rate_limiter.check_command_rate_limit(ctx.author.id, ctx.command.name)
        if not allowed:
            await ctx.send(f"⏰ {message}")
            logger.warning(f"Rate limited user {ctx.author.id} for command {ctx.command.name}")
            return False
        return True

    return commands.check(rate_limit_check)

def check_button_rate_limit(user_id: int) -> Tuple[bool, Optional[str]]:
    """Check button rate limit for interactions."""
    return rate_limiter.check_button_rate_limit(user_id)

def reset_user_rate_limits(user_id: int):
    """Reset rate limits for a user."""
    rate_limiter.reset_user_limits(user_id)

def get_user_rate_stats(user_id: int) -> Dict:
    """Get rate limiting stats for a user."""
    return rate_limiter.get_user_stats(user_id)
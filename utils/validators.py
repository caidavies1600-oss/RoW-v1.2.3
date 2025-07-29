"""Input validation utilities."""

import re
from typing import Optional
import discord
from config.settings import ADMIN_ROLE_IDS, MAIN_TEAM_ROLE_ID

class Validators:
    """Collection of validation functions."""

    @staticmethod
    def is_admin(user: discord.Member) -> bool:
        """Check if user has admin permissions."""
        return any(role.id in ADMIN_ROLE_IDS for role in user.roles)

    @staticmethod
    def can_join_main_team(user: discord.Member) -> bool:
        """Check if user can join main team."""
        return any(role.id == MAIN_TEAM_ROLE_ID for role in user.roles)

    @staticmethod
    def validate_ign(ign: str) -> tuple[bool, Optional[str]]:
        """Validate an in-game name."""
        if not ign or not ign.strip():
            return False, "IGN cannot be empty"

        ign = ign.strip()

        if len(ign) < 2:
            return False, "IGN must be at least 2 characters"

        if len(ign) > 20:
            return False, "IGN must be 20 characters or less"

        # Allow alphanumeric, spaces, underscores, hyphens
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', ign):
            return False, "IGN contains invalid characters"

        return True, None

    @staticmethod
    def validate_team_name(team: str) -> Optional[str]:
        """Validate and normalize team name."""
        team_mapping = {
            "main": "main_team",
            "main_team": "main_team",
            "team1": "main_team",
            "team_1": "main_team",
            "1": "main_team",

            "team2": "team_2",
            "team_2": "team_2", 
            "2": "team_2",

            "team3": "team_3",
            "team_3": "team_3",
            "3": "team_3"
        }
        return team_mapping.get(team.lower().strip())

    @staticmethod
    def validate_days(days: int) -> tuple[bool, Optional[str]]:
        """Validate day count for blocking users."""
        if days < 1:
            return False, "Days must be at least 1"
        if days > 365:
            return False, "Days cannot exceed 365"
        return True, None
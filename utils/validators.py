"""
Input validation utilities for the RoW Discord bot.

This module provides:
- User permission validation
- In-game name validation
- Team name normalization
- Time period validation
- Role-based access control

Features:
- Admin permission checking
- Main team role validation
- IGN format verification
- Team name standardization
- Duration validation
"""

import re
from typing import Optional

import discord

from config.constants import MAX_BAN_DAYS, MAX_TEAM_SIZE
from config.settings import ADMIN_ROLE_IDS, MAIN_TEAM_ROLE_ID


class Validators:
    """
    Collection of validation functions for bot input.

    Features:
    - Permission validation
    - Role checking
    - Name format validation
    - Team name normalization
    - Duration validation
    """

    @staticmethod
    def is_admin(user: discord.Member) -> bool:
        """
        Check if user has admin permissions.

        Args:
            user: Discord member to check

        Returns:
            bool: True if user has admin role

        Checks:
            - Admin role presence
            - Role ID validation
        """
        return any(role.id in ADMIN_ROLE_IDS for role in user.roles)

    @staticmethod
    def can_join_main_team(user: discord.Member) -> bool:
        """
        Check if user can join main team.

        Args:
            user: Discord member to check

        Returns:
            bool: True if user has main team role

        Validates:
            - Main team role presence
            - Role ID match
        """
        return any(role.id == MAIN_TEAM_ROLE_ID for role in user.roles)

    @staticmethod
    def validate_ign(ign: str) -> tuple[bool, Optional[str]]:
        """
        Validate an in-game name.

        Args:
            ign: In-game name to validate

        Returns:
            tuple: (valid: bool, error_message: Optional[str])

        Validates:
        - Non-empty string
        - Length (2-20 chars)
        - Character set (alphanumeric + space + _-)
        """
        if not ign or not ign.strip():
            return False, "IGN cannot be empty"

        ign = ign.strip()

        if len(ign) < 2:
            return False, "IGN must be at least 2 characters"

        if len(ign) > 20:
            return False, "IGN must be 20 characters or less"

        # Allow alphanumeric, spaces, underscores, hyphens
        if not re.match(r"^[a-zA-Z0-9\s_-]+$", ign):
            return False, "IGN contains invalid characters"

        return True, None

    @staticmethod
    def validate_team_name(team: str) -> Optional[str]:
        """
        Validate and normalize team name.

        Args:
            team: Team name/identifier to validate

        Returns:
            Optional[str]: Normalized team name or None if invalid

        Features:
        - Case insensitive matching
        - Alias support (team1 -> main_team)
        - Numeric shortcuts (1 -> main_team)
        """
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
            "3": "team_3",
        }
        return team_mapping.get(team.lower().strip())

    @staticmethod
    def validate_days(days: int) -> tuple[bool, str]:
        """
        Validate the number of days for blocking a user.
        
        Args:
            days: Number of days to validate
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            days = int(days)
            if days < 1:
                return False, "Duration must be at least 1 day."
            if days > MAX_BAN_DAYS:
                return False, f"Duration cannot exceed {MAX_BAN_DAYS} days."
            return True, ""
        except ValueError:
            return False, "Duration must be a whole number."

    @staticmethod
    def validate_team_size(team: list) -> tuple[bool, str]:
        """Validate the number of members in a team."""
        if len(team) > MAX_TEAM_SIZE:
            return False, f"Team cannot exceed {MAX_TEAM_SIZE} members"
        return True, ""

    @staticmethod
    def validate_user_id(user_id: str) -> tuple[bool, str]:
        """Validate Discord user ID format."""
        if not isinstance(user_id, str):
            user_id = str(user_id)
        if not user_id.isdigit():
            return False, "User ID must contain only numbers"
        if len(user_id) < 17 or len(user_id) > 20:
            return False, "Invalid user ID length"
        return True, ""

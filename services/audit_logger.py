"""
Audit logging system for tracking important bot actions.

This module provides comprehensive audit logging functionality:
- Team signup tracking
- Admin action logging
- Event management logging
- Result recording
- Action history searching

The audit log is stored as JSON and maintains the last 1000 entries
to prevent excessive file growth.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from utils.logger import setup_logger
from utils.data_manager import DataManager

logger = setup_logger("audit_logger")

class AuditLogger:
    """
    Handles audit logging for important bot actions.
    
    Features:
    - Automatic log rotation (1000 entries)
    - JSON-based persistent storage
    - Action filtering and searching
    - User history tracking
    - Guild-specific logging
    """

    def __init__(self):
        self.audit_file = "data/audit_log.json"
        self.data_manager = DataManager()
        self._ensure_audit_file()

    def _ensure_audit_file(self):
        """Ensure audit log file exists."""
        if not os.path.exists(self.audit_file):
            try:
                os.makedirs(os.path.dirname(self.audit_file), exist_ok=True)
                with open(self.audit_file, 'w') as f:
                    json.dump([], f)
                logger.info(f"✅ Created audit log file: {self.audit_file}")
            except Exception as e:
                logger.error(f"❌ Failed to create audit log file: {e}")

    def log_action(self, action_type: str, user_id: int, details: Dict[str, Any], 
                   target_user_id: Optional[int] = None, guild_id: Optional[int] = None):
        """
        Log an audit action with full details.

        Args:
            action_type: Type of action being logged
            user_id: ID of user performing action
            details: Additional action details
            target_user_id: Optional ID of user being acted upon
            guild_id: Optional Discord server ID

        The log entry includes:
        - Timestamp in ISO format
        - Action type and user IDs
        - Guild context if provided
        - Additional details dictionary
        """
        try:
            # Load existing audit log
            audit_log = self.data_manager.load_json(self.audit_file, [])

            # Create audit entry
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action_type": action_type,
                "user_id": str(user_id),
                "target_user_id": str(target_user_id) if target_user_id else None,
                "guild_id": str(guild_id) if guild_id else None,
                "details": details
            }

            # Add to log
            audit_log.append(entry)

            # Keep only last 1000 entries to prevent file bloat
            if len(audit_log) > 1000:
                audit_log = audit_log[-1000:]

            # Save audit log
            if self.data_manager.save_json(self.audit_file, audit_log):
                logger.debug(f"📝 Audit logged: {action_type} by {user_id}")
            else:
                logger.error(f"❌ Failed to save audit log entry")

        except Exception as e:
            logger.error(f"❌ Error logging audit action: {e}")

    def log_signup(self, user_id: int, team: str, action: str = "join", guild_id: Optional[int] = None):
        """Log team signup/leave actions."""
        self.log_action(
            action_type=f"team_{action}",
            user_id=user_id,
            details={"team": team, "action": action},
            guild_id=guild_id
        )

    def log_admin_action(self, admin_id: int, action: str, target_user_id: Optional[int] = None, 
                        details: Optional[Dict] = None, guild_id: Optional[int] = None):
        """Log admin actions like blocking, unblocking, etc."""
        self.log_action(
            action_type=f"admin_{action}",
            user_id=admin_id,
            target_user_id=target_user_id,
            details=details or {},
            guild_id=guild_id
        )

    def log_result(self, admin_id: int, team: str, result: str, guild_id: Optional[int] = None):
        """Log win/loss recording."""
        self.log_action(
            action_type="record_result",
            user_id=admin_id,
            details={"team": team, "result": result},
            guild_id=guild_id
        )

    def log_event_action(self, admin_id: int, action: str, details: Optional[Dict] = None, 
                        guild_id: Optional[int] = None):
        """Log event management actions."""
        self.log_action(
            action_type=f"event_{action}",
            user_id=admin_id,
            details=details or {},
            guild_id=guild_id
        )

    def get_user_actions(self, user_id: int, limit: int = 50) -> list:
        """
        Get recent actions by a specific user.

        Args:
            user_id: Discord user ID to search for
            limit: Maximum number of actions to return

        Returns:
            list: Most recent actions by the user, newest first
        """
        try:
            audit_log = self.data_manager.load_json(self.audit_file, [])
            user_actions = []

            for entry in reversed(audit_log):
                if entry.get("user_id") == str(user_id):
                    user_actions.append(entry)
                    if len(user_actions) >= limit:
                        break

            return user_actions
        except Exception as e:
            logger.error(f"❌ Error getting user actions: {e}")
            return []

    def get_recent_actions(self, limit: int = 100) -> list:
        """
        Get recent actions across all users.

        Args:
            limit: Maximum number of actions to return

        Returns:
            list: Most recent audit log entries, newest first
        """
        try:
            audit_log = self.data_manager.load_json(self.audit_file, [])
            return audit_log[-limit:]
        except Exception as e:
            logger.error(f"❌ Error getting recent actions: {e}")
            return []

    def search_actions(self, action_type: Optional[str] = None, user_id: Optional[int] = None,
                      days_back: int = 7) -> list:
        """
        Search audit log with filters.

        Args:
            action_type: Optional action type to filter by
            user_id: Optional user ID to filter by
            days_back: Number of days to search back

        Returns:
            list: Matching audit log entries within time period
        """
        try:
            audit_log = self.data_manager.load_json(self.audit_file, [])
            results = []

            cutoff_date = datetime.utcnow().timestamp() - (days_back * 86400)

            for entry in audit_log:
                try:
                    entry_date = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if entry_date < cutoff_date:
                        continue
                except:
                    continue

                # Apply filters
                if action_type and not entry.get("action_type", "").startswith(action_type):
                    continue

                if user_id and entry.get("user_id") != str(user_id):
                    continue

                results.append(entry)

            return results
        except Exception as e:
            logger.error(f"❌ Error searching audit log: {e}")
            return []

# Global audit logger instance
audit_logger = AuditLogger()

# Convenience functions for easy access
def log_signup(user_id: int, team: str, action: str = "join", guild_id: Optional[int] = None):
    """
    Log team signup action.

    Args:
        user_id: User performing signup
        team: Team being joined/left
        action: "join" or "leave"
        guild_id: Optional Discord server ID
    """
    audit_logger.log_signup(user_id, team, action, guild_id)

def log_admin_action(admin_id: int, action: str, target_user_id: Optional[int] = None, 
                    details: Optional[Dict] = None, guild_id: Optional[int] = None):
    """
    Log administrative action.

    Args:
        admin_id: Admin performing action
        action: Type of admin action
        target_user_id: User being acted upon
        details: Additional action details
        guild_id: Optional Discord server ID
    """
    audit_logger.log_admin_action(admin_id, action, target_user_id, details, guild_id)

def log_result(admin_id: int, team: str, result: str, guild_id: Optional[int] = None):
    """Log result recording."""
    audit_logger.log_result(admin_id, team, result, guild_id)

def log_event_action(admin_id: int, action: str, details: Optional[Dict] = None, 
                    guild_id: Optional[int] = None):
    """Log event action."""
    audit_logger.log_event_action(admin_id, action, details, guild_id)
"""
Configuration management for Google Sheets integration.

This module centralizes all configuration settings and provides
validation for Google Sheets connection parameters.
"""

import os
import json
from typing import Dict, Any, Optional
from utils.logger import setup_logger

logger = setup_logger("sheets_config")


class SheetsConfig:
    """Configuration manager for Google Sheets integration."""

    def __init__(self):
        self.credentials_path = "credentials.json"
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self.rate_limits = {
            "requests_per_100_seconds": 100,
            "writes_per_100_seconds": 100,
            "min_request_interval": 0.1,
            "max_retries": 5,
            "backoff_factor": 2,
            "max_backoff": 64
        }

    def get_credentials_dict(self) -> Optional[Dict[str, Any]]:
        """Get credentials from environment or file."""
        try:
            # Try environment variable first
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            if creds_json:
                return json.loads(creds_json)

            # Fall back to file
            if os.path.exists(self.credentials_path):
                with open(self.credentials_path, 'r') as f:
                    return json.load(f)

            return None

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def get_spreadsheet_id(self) -> Optional[str]:
        """Get spreadsheet ID from environment."""
        return os.getenv("GOOGLE_SHEETS_ID")

    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration settings."""
        validation = {
            "credentials_available": self.get_credentials_dict() is not None,
            "spreadsheet_id_set": self.get_spreadsheet_id() is not None,
            "scopes_defined": len(self.scopes) > 0,
            "rate_limits_configured": bool(self.rate_limits)
        }

        all_valid = all(validation.values())
        logger.info(f"Configuration validation: {'✅ Passed' if all_valid else '❌ Failed'}")

        return validation


# Global config instance
config = SheetsConfig()
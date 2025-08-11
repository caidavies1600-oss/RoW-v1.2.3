"""
Google Sheets integration for Discord RoW Bot.

This module provides a clean interface for syncing bot data with Google Sheets.
Falls back gracefully if sheets integration is not available.
"""

from .manager import SheetsManager

__all__ = ['SheetsManager']

# Version info
__version__ = "1.0.0"
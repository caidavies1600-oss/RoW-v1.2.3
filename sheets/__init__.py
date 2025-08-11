"""Google Sheets integration for Discord RoW Bot - Clean Architecture."""

from .manager import SheetsManager

# Clean export - only expose the main manager
__all__ = ['SheetsManager']
"""Google Sheets integration for Discord RoW Bot."""

from .data_sync import DataSync

# Main export - this replaces the old SheetsManager
SheetsManager = DataSync

__all__ = ['SheetsManager']
# Google Sheets Integration

Clean, working Google Sheets integration for the Discord RoW Bot.

## Features

- **Fallback-safe**: Bot works even if sheets integration fails
- **Rate-limited**: Respects Google API quotas
- **Error handling**: Comprehensive logging and graceful failure
- **Template creation**: Sets up sheets for manual data entry
- **Data syncing**: Keeps bot data in sync with Google Sheets

## Setup

1. Set environment variables:
   ```
   GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}
   GOOGLE_SHEETS_ID=your_spreadsheet_id_here
   ```

2. Import and use:
   ```python
   from sheets import SheetsManager

   sheets = SheetsManager()
   if sheets.is_connected():
       print("✅ Sheets ready!")
   ```

## Usage Examples

### Basic Connection Test
```python
# Test connection
info = sheets.get_connection_info()
print(f"Connected: {info['connected']}")
print(f"URL: {info['spreadsheet_url']}")
```

### Sync All Bot Data
```python
# Sync everything to sheets
bot_data = {
    "events": {"main_team": ["player1", "player2"], "team_2": [], "team_3": []},
    "player_stats": {"123456": {"name": "Player1", "power_rating": 50000000}},
    "results": {"total_wins": 5, "total_losses": 3, "history": []}
}

success = sheets.sync_all_data(bot_data)
if success:
    print("✅ All data synced!")
```

### Quick Team Sync
```python
# Just sync current teams
events_data = {
    "main_team": ["PlayerA", "PlayerB"],
    "team_2": ["PlayerC"],
    "team_3": []
}
sheets.quick_sync_teams(events_data)
```

### Add Match Result
```python
# Record a match result
sheets.add_match_result("main_team", "win", "AdminUser")
```

### Create Templates
```python
# Set up sheets for manual data entry
sheets.setup_templates(bot_data)
```

### Load Data from Sheets
```python
# Use sheets as primary data source
data = sheets.load_bot_data()
if data:
    print("✅ Loaded from sheets")
else:
    print("⚠️ Falling back to JSON files")
```

## File Structure

```
sheets/
├── __init__.py          # Clean import interface
├── config.py            # Sheet configurations and settings
├── client.py            # Authentication and basic operations
├── operations.py        # Data sync and template operations  
├── manager.py           # Main API interface
└── README.md           # This file
```

## Error Handling

The module is designed to fail gracefully:

- No credentials? Bot works with JSON files only
- API errors? Operations return False, bot continues
- Network issues? Rate limiting and retries handle it
- Invalid data? Validation and logging prevent crashes

## Worksheets Created

- **Current Teams**: Active team signups
- **Player Stats**: Manual power rating entry and win/loss tracking
- **Match Results**: Battle outcomes and enemy alliance data
- **Alliance Tracking**: Enemy alliance performance tracking
- **Dashboard**: Overview and summary data

## Backwards Compatibility

The new structure maintains compatibility with existing bot code:

```python
# Old usage still works
from sheets import SheetsManager
sheets = SheetsManager()

# All existing method calls work
if sheets.is_connected():
    success = sheets.sync_current_teams(events_data)
```
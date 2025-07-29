# Discord Row Bot

A modular, scalable Discord bot built for managing in-game events, tracking participation, and syncing IGN (in-game names) with Discord users.

## 🧱 Project Structure

```
discord_row_bot/
│
├── main.py                        # Entry point for the bot
├── requirements.txt              # Python package dependencies
│
├── config/                       # Bot configuration
│   ├── __init__.py
│   ├── settings.py               # Token, prefixes, environment configs
│   └── constants.py              # Static variables and enums
│
├── bot/                          # Bot client setup and error handling
│   ├── __init__.py
│   ├── client.py
│   └── error_handler.py
│
├── cogs/                         # Core bot functionality (modularized)
│   ├── __init__.py
│   └── admin/
│       ├── __init__.py
│       ├── actions.py           # Admin moderation commands
│       ├── attendance.py        # Logs/checks absences
│       └── exporter.py          # Admin data export tools
│
├── events/                       # Event system
│   ├── __init__.py
│   ├── manager.py               # Main event logic
│   ├── alerts.py                # Event reminders
│   └── results.py               # Match results and win/loss tracking
│
├── services/                     # Background & utility services
│   ├── __init__.py
│   ├── scheduler.py             # Periodic task execution
│   └── notifications.py         # Notification sending service
│
├── user/                         # User-related commands and profile
│   ├── __init__.py
│   ├── profile.py               # IGN linking and management
│   └── commands.py              # User commands like !myign, !setign
│
├── interactions/                # UI interaction handlers
│   ├── __init__.py
│   ├── buttons.py               # Handles button clicks
│   └── dropdowns.py             # Team selection dropdowns
│
├── utils/                        # Shared utility code
│   ├── __init__.py
│   ├── logger.py                # Logger setup
│   ├── data_manager.py          # JSON data read/write
│   ├── validators.py            # Validation utilities
│   └── helpers.py               # Shared functions
│
├── data/                         # Persistent data storage
│   ├── events.json              # Signed up users per event
│   ├── blocked_users.json       # Blacklist
│   ├── ign_map.json             # IGN → Discord mapping
│   ├── event_results.json       # Match outcomes
│   ├── events_history.json      # History of events
│   ├── row_times.json           # Scheduled event times
│   └── logs/
│       └── bot.log              # Runtime logs
```

## 📦 Setup

1. Clone the repo.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Add your bot token and configuration in `settings.py`.
4. Run the bot:
   ```
   python main.py
   ```

## 🧩 Features

- 🔔 Event reminders
- 📊 Match tracking
- 🛠️ Admin tools for reporting/exporting
- ⌛ Background scheduling
- 🎛️ UI components (dropdowns, buttons)
- ✅ Validation & error handling

---

Developed with modularity and scalability in mind.

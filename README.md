
# Discord Row Bot

A comprehensive Discord bot built for managing in-game events, tracking participation, syncing IGN (in-game names) with Discord users, and integrating with Google Sheets for data management and analytics.

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
│   ├── client.py                 # Main bot client class
│   └── error_handler.py          # Global error handling
│
├── cogs/                         # Core bot functionality (modularized)
│   ├── __init__.py
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── actions.py           # Admin moderation commands
│   │   ├── attendance.py        # Logs/checks absences
│   │   ├── exporter.py          # Admin data export tools
│   │   ├── owner_actions.py     # Bot owner-only commands
│   │   ├── sheets_test.py       # Google Sheets testing commands
│   │   └── sheet_formatter.py   # Advanced sheet formatting
│   ├── events/
│   │   ├── __init__.py
│   │   ├── manager.py           # Main event logic
│   │   ├── alerts.py            # Event reminders
│   │   ├── results.py           # Match results and win/loss tracking
│   │   └── signup_view.py       # Event signup UI components
│   ├── interactions/
│   │   ├── __init__.py
│   │   ├── buttons.py           # Handles button clicks
│   │   ├── dropdowns.py         # Team selection dropdowns
│   │   └── mention_handler.py   # Custom mention processing
│   └── user/
│       ├── __init__.py
│       ├── profile.py           # IGN linking and management
│       └── commands.py          # User commands like !myign, !setign
│
├── events/                       # Legacy event system (deprecated)
│   ├── __init__.py
│   ├── manager.py
│   ├── alerts.py
│   └── results.py
│
├── services/                     # Background & utility services
│   ├── __init__.py
│   ├── scheduler.py             # Periodic task execution
│   ├── notifications.py         # Basic notification service
│   ├── smart_notifications.py   # Advanced notification system
│   ├── sheets_manager.py        # Google Sheets integration
│   ├── audit_logger.py          # Audit trail logging
│   ├── error_logger.py          # Centralized error logging
│   └── prediction_engine.py     # Match prediction system
│
├── sheets/                       # Google Sheets management
│   ├── __init__.py
│   ├── base_manager.py          # Base sheets functionality
│   ├── data_sync.py             # Data synchronization
│   ├── error_handler.py         # Sheets-specific error handling
│   ├── enhanced_sheets_manager.py # Advanced sheets features
│   ├── template_creator.py      # Sheet template generation
│   ├── worksheet_handlers.py    # Individual worksheet management
│   └── config.py                # Sheets configuration
│
├── utils/                        # Shared utility code
│   ├── __init__.py
│   ├── logger.py                # Logger setup
│   ├── data_manager.py          # JSON data read/write
│   ├── validators.py            # Validation utilities
│   ├── helpers.py               # Shared functions
│   ├── health_monitor.py        # System health monitoring
│   ├── backup_manager.py        # Data backup system
│   ├── rate_limiter.py          # API rate limiting
│   ├── admin_notifier.py        # Admin notification system
│   ├── automatic_monitor.py     # Automated monitoring
│   ├── integrated_data_manager.py # Advanced data management
│   ├── startup_data_fixer.py    # Data integrity fixes on startup
│   └── file_ops.py              # File operation utilities
│
├── dashboard/                    # Web dashboard
│   ├── templates/
│   │   ├── base.html            # Base template
│   │   ├── dashboard.html       # Main dashboard
│   │   ├── events.html          # Events overview
│   │   ├── players.html         # Player statistics
│   │   ├── sheets.html          # Sheets management
│   │   └── error.html           # Error pages
│   ├── app.py                   # Flask web application
│   └── run_dashboard.py         # Dashboard runner
│
├── data/                         # Persistent data storage
│   ├── backups/                 # Automated backups
│   ├── logs/                    # Application logs
│   ├── events.json              # Current event signups
│   ├── blocked_users.json       # User blacklist
│   ├── ign_map.json             # IGN → Discord mapping
│   ├── event_results.json       # Match outcomes
│   ├── events_history.json      # Historical events
│   ├── player_stats.json        # Player statistics
│   ├── row_times.json           # Scheduled event times
│   ├── absent_users.json        # Attendance tracking
│   ├── notification_preferences.json # User notification settings
│   └── signup_lock.json         # Signup state management
│
└── scripts/                     # Utility scripts
    └── check_sheets_config.py   # Google Sheets configuration checker
```

## 🚀 Features

### Core Event Management
- 📅 **Event Scheduling**: Automated event creation and management
- 👥 **Team Signups**: Multi-team signup system with UI components
- 📊 **Results Tracking**: Win/loss tracking with detailed statistics
- 🏆 **Player Statistics**: Individual and team performance analytics
- 📈 **Historical Data**: Complete event and match history

### Google Sheets Integration
- 📋 **Real-time Sync**: Automatic data synchronization with Google Sheets
- 📊 **Advanced Analytics**: Enhanced player statistics and performance metrics
- 🎨 **Auto-formatting**: Intelligent sheet formatting with color coding
- 📈 **Dashboard Views**: Multiple sheet views for different data types
- 🔄 **Batch Operations**: Efficient bulk data operations with rate limiting

### Smart Notifications
- 🔔 **Event Reminders**: Automated event notifications
- 🎯 **Targeted Messaging**: Team-specific and role-based notifications
- ⚙️ **User Preferences**: Customizable notification settings
- 📱 **Multi-channel**: Support for DMs and channel notifications

### Administrative Tools
- 🛠️ **Moderation Commands**: User management and blacklist functionality
- 📊 **Data Export**: Comprehensive data export capabilities
- 🔍 **Health Monitoring**: System health checks and diagnostics
- 📋 **Audit Logging**: Complete action audit trails
- 🔧 **Configuration Management**: Dynamic bot configuration

### Web Dashboard
- 🌐 **Real-time Dashboard**: Web-based monitoring and management
- 📊 **Statistics View**: Visual data representation
- 👥 **Player Management**: User and IGN management interface
- 📋 **Event Overview**: Current and historical event data

### Advanced Features
- 🤖 **Prediction Engine**: Match outcome predictions
- 🔄 **Automatic Backups**: Scheduled data backups
- ⚡ **Rate Limiting**: API rate limiting and optimization
- 🚨 **Error Recovery**: Comprehensive error handling and recovery
- 📱 **Interactive UI**: Buttons, dropdowns, and rich interactions

## 📦 Setup

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Google Sheets API credentials (optional, for sheets integration)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd discord_row_bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file or set environment variables:
   ```
   BOT_TOKEN=your_discord_bot_token
   GOOGLE_SHEETS_CREDENTIALS=your_google_credentials_json
   GOOGLE_SHEETS_ID=your_spreadsheet_id
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

### Optional: Web Dashboard
To run the web dashboard:
```bash
python dashboard/run_dashboard.py
```

## 🎮 Usage

### Basic Commands
- `!signup` - Join an event
- `!leave` - Leave an event
- `!events` - View current signups
- `!results` - View match results and statistics
- `!myign` - View your linked IGN
- `!setign <ign>` - Link your in-game name

### Admin Commands
- `!addresult <team> <result>` - Record match results
- `!export` - Export data to various formats
- `!health` - Check bot system health
- `!sheets sync` - Force Google Sheets synchronization

## 🔧 Configuration

The bot uses multiple configuration files:
- `config/settings.py` - Main bot settings and tokens
- `config/constants.py` - Static values and enums
- `sheets/config.py` - Google Sheets configuration
- Data files in `/data/` for persistent storage

## 📊 Google Sheets Integration

The bot automatically syncs with Google Sheets to provide:
- Current team signups
- Player statistics and analytics
- Match results and history
- Enhanced performance metrics
- Automated formatting and visualization

## 🚨 Monitoring & Health

- **Health Monitoring**: Real-time system health checks
- **Audit Logging**: Complete action logging for accountability
- **Error Recovery**: Automatic error handling and recovery
- **Performance Metrics**: Operation timing and success rates
- **Backup System**: Automated data backups

## 🛡️ Error Handling

Comprehensive error handling includes:
- Global Discord error handling
- Google Sheets API error recovery
- Data validation and sanitization
- Graceful degradation on service failures
- Detailed logging for troubleshooting

---

**Built with modularity, scalability, and reliability in mind.**

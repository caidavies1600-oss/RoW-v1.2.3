# Railway Deployment Setup

## Required Environment Variables

Set these in your Railway dashboard:

1. **BOT_TOKEN** - Your Discord bot token
2. **GOOGLE_SHEETS_CREDENTIALS** - Your Google service account JSON (optional)
3. **GOOGLE_SHEETS_ID** - Your Google Sheets ID (optional)

## Setup Steps

1. Connect this GitHub repo to Railway
2. Set the environment variables above
3. Deploy automatically starts with `python main.py`

## Server-Specific Configuration

Update `config/settings.py` with your Discord server's:
- Role IDs
- Channel IDs  
- Admin user IDs

The bot will work with default settings but customize for your server.

## Data Storage

- Bot uses JSON files in `data/` directory
- Google Sheets integration is optional
- All data persists between deployments

## Support

Check logs in Railway dashboard for any deployment issues.

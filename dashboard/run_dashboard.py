
#!/usr/bin/env python3
"""
Dashboard Runner for RoW Discord Bot.

This script can be used to run the dashboard independently
or integrated with the main bot.
"""

import sys
import os
import asyncio
import threading
from pathlib import Path

# Add the parent directory to the path so we can import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.app import create_dashboard_app
from utils.logger import setup_logger

logger = setup_logger("dashboard_runner")

def run_dashboard_standalone(host='0.0.0.0', port=5000):
    """
    Run the dashboard as a standalone application.
    
    Args:
        host: Host to bind to
        port: Port to run on
    """
    logger.info("🚀 Starting RoW Bot Dashboard (Standalone Mode)")
    
    try:
        # Create dashboard app without bot instance
        app = create_dashboard_app(bot=None)
        
        logger.info(f"📊 Dashboard starting on http://{host}:{port}")
        logger.info("📝 Available endpoints:")
        logger.info("   - / (Dashboard Overview)")
        logger.info("   - /events (Events Management)")
        logger.info("   - /players (Player Statistics)")
        logger.info("   - /sheets (Google Sheets Status)")
        logger.info("   - /api/stats (Statistics API)")
        logger.info("   - /api/health (Health Check API)")
        
        # Run the dashboard
        app.run(host=host, port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Failed to start dashboard: {e}")
        raise

def run_dashboard_with_bot(bot, host='0.0.0.0', port=5000):
    """
    Run the dashboard integrated with the bot.
    
    Args:
        bot: Discord bot instance
        host: Host to bind to
        port: Port to run on
    """
    def dashboard_thread():
        logger.info("🚀 Starting RoW Bot Dashboard (Integrated Mode)")
        
        try:
            # Create dashboard app with bot instance
            app = create_dashboard_app(bot=bot)
            
            logger.info(f"📊 Dashboard running on http://{host}:{port}")
            
            # Run the dashboard
            app.run(host=host, port=port, debug=False, threaded=True)
            
        except Exception as e:
            logger.error(f"❌ Dashboard error: {e}")
    
    # Start dashboard in a separate thread
    dashboard_thread_instance = threading.Thread(
        target=dashboard_thread,
        name="DashboardThread",
        daemon=True
    )
    dashboard_thread_instance.start()
    
    logger.info("✅ Dashboard thread started")
    return dashboard_thread_instance

if __name__ == "__main__":
    """Run dashboard standalone for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RoW Bot Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    
    args = parser.parse_args()
    
    run_dashboard_standalone(host=args.host, port=args.port)

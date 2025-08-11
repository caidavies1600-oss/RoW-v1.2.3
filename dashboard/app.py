
from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime, timedelta
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time

from utils.logger import setup_logger
from utils.data_manager import DataManager
from config.constants import TEAM_DISPLAY, COLORS

logger = setup_logger("dashboard")

class DashboardApp:
    """
    Main dashboard application for the RoW Discord Bot.
    
    Features:
    - Real-time bot statistics
    - Event management overview
    - Player performance analytics
    - Google Sheets integration status
    - Health monitoring
    - Interactive data visualization
    """
    
    def __init__(self, bot=None):
        self.bot = bot
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.data_manager = DataManager()
        self.setup_routes()
        
    def setup_routes(self):
        """Set up all dashboard routes."""
        
        @self.app.route('/')
        def dashboard_home():
            """Main dashboard overview page."""
            try:
                # Get basic statistics
                stats = self.get_dashboard_stats()
                return render_template('dashboard.html', stats=stats)
            except Exception as e:
                logger.error(f"Error loading dashboard: {e}")
                return render_template('error.html', error=str(e))
        
        @self.app.route('/events')
        def events_page():
            """Events management and history page."""
            try:
                events_data = self.get_events_data()
                return render_template('events.html', data=events_data)
            except Exception as e:
                logger.error(f"Error loading events page: {e}")
                return render_template('error.html', error=str(e))
        
        @self.app.route('/players')
        def players_page():
            """Player statistics and performance page."""
            try:
                player_data = self.get_player_data()
                return render_template('players.html', data=player_data)
            except Exception as e:
                logger.error(f"Error loading players page: {e}")
                return render_template('error.html', error=str(e))
        
        @self.app.route('/sheets')
        def sheets_page():
            """Google Sheets integration status page."""
            try:
                sheets_data = self.get_sheets_data()
                return render_template('sheets.html', data=sheets_data)
            except Exception as e:
                logger.error(f"Error loading sheets page: {e}")
                return render_template('error.html', error=str(e))
        
        @self.app.route('/api/stats')
        def api_stats():
            """API endpoint for real-time statistics."""
            try:
                return jsonify(self.get_dashboard_stats())
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/health')
        def api_health():
            """API endpoint for bot health status."""
            try:
                return jsonify(self.get_health_status())
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/events/current')
        def api_current_events():
            """API endpoint for current event signups."""
            try:
                return jsonify(self.get_current_events())
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    def get_dashboard_stats(self):
        """Get comprehensive dashboard statistics."""
        try:
            # Load all data
            all_data = self.data_manager.load_all_data_from_sheets()
            
            # Basic bot stats
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "bot_status": "Online" if self.bot and self.bot.is_ready() else "Offline",
                "uptime": self.calculate_uptime(),
                "guild_count": len(self.bot.guilds) if self.bot else 0,
                "member_count": sum(len(guild.members) for guild in self.bot.guilds) if self.bot else 0,
            }
            
            # Event statistics
            events = all_data.get("events", {})
            stats["current_events"] = {
                "main_team_count": len(events.get("main_team", [])),
                "team_2_count": len(events.get("team_2", [])),
                "team_3_count": len(events.get("team_3", [])),
                "total_signups": sum(len(team) for team in events.values())
            }
            
            # Player statistics
            player_stats = all_data.get("player_stats", {})
            stats["player_summary"] = {
                "total_players": len(player_stats),
                "active_players": len([p for p in player_stats.values() if p.get("wins", 0) + p.get("losses", 0) > 0]),
                "total_matches": sum(p.get("wins", 0) + p.get("losses", 0) for p in player_stats.values()),
                "average_win_rate": self.calculate_average_win_rate(player_stats)
            }
            
            # Recent activity
            events_history = all_data.get("events_history", [])
            stats["recent_activity"] = events_history[-5:] if events_history else []
            
            # System health
            stats["system_health"] = self.get_system_health()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def get_events_data(self):
        """Get comprehensive events data."""
        try:
            all_data = self.data_manager.load_all_data_from_sheets()
            
            # Current signups
            current_events = all_data.get("events", {})
            
            # Events history
            events_history = all_data.get("events_history", [])
            
            # Format team data with better display
            formatted_teams = {}
            for team_key, members in current_events.items():
                formatted_teams[team_key] = {
                    "display_name": TEAM_DISPLAY.get(team_key, team_key.replace("_", " ").title()),
                    "members": members,
                    "count": len(members),
                    "capacity": 40,  # Assuming max capacity
                    "fill_percentage": round((len(members) / 40) * 100, 1)
                }
            
            return {
                "current_teams": formatted_teams,
                "history": events_history[-20:],  # Last 20 events
                "statistics": {
                    "total_events": len(events_history),
                    "this_month": len([e for e in events_history if self.is_this_month(e.get("timestamp"))]),
                    "average_participation": self.calculate_average_participation(events_history)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting events data: {e}")
            return {"error": str(e)}
    
    def get_player_data(self):
        """Get comprehensive player data."""
        try:
            all_data = self.data_manager.load_all_data_from_sheets()
            player_stats = all_data.get("player_stats", {})
            
            # Process player data
            players = []
            for username, stats in player_stats.items():
                wins = stats.get("wins", 0)
                losses = stats.get("losses", 0)
                total_games = wins + losses
                win_rate = (wins / total_games * 100) if total_games > 0 else 0
                
                players.append({
                    "username": username,
                    "wins": wins,
                    "losses": losses,
                    "total_games": total_games,
                    "win_rate": round(win_rate, 1),
                    "rank": self.calculate_player_rank(stats),
                    "last_active": stats.get("last_seen", "Unknown")
                })
            
            # Sort by performance
            players.sort(key=lambda x: (x["win_rate"], x["total_games"]), reverse=True)
            
            # Add rankings
            for i, player in enumerate(players, 1):
                player["position"] = i
            
            # Statistics
            total_players = len(players)
            active_players = len([p for p in players if p["total_games"] > 0])
            
            return {
                "players": players,
                "leaderboard": players[:10],  # Top 10
                "statistics": {
                    "total_players": total_players,
                    "active_players": active_players,
                    "average_games": round(sum(p["total_games"] for p in players) / total_players, 1) if total_players > 0 else 0,
                    "average_win_rate": round(sum(p["win_rate"] for p in players) / total_players, 1) if total_players > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting player data: {e}")
            return {"error": str(e)}
    
    def get_sheets_data(self):
        """Get Google Sheets integration status."""
        try:
            sheets_status = {
                "connected": False,
                "last_sync": "Never",
                "worksheets": [],
                "error": None
            }
            
            if hasattr(self.bot, 'sheets') and self.bot.sheets:
                try:
                    sheets_status["connected"] = self.bot.sheets.is_connected()
                    
                    if sheets_status["connected"]:
                        # Get comprehensive stats
                        stats = self.bot.sheets.get_comprehensive_stats()
                        sheets_status.update({
                            "spreadsheet_url": stats.get("spreadsheet_url"),
                            "worksheets": stats.get("worksheets", []),
                            "performance_metrics": stats.get("performance_metrics", {}),
                            "system_health": stats.get("system_health", "Unknown"),
                            "last_sync": stats.get("last_updated", "Unknown")
                        })
                    
                except Exception as e:
                    sheets_status["error"] = str(e)
            
            return sheets_status
            
        except Exception as e:
            logger.error(f"Error getting sheets data: {e}")
            return {"error": str(e)}
    
    def get_health_status(self):
        """Get bot health status."""
        try:
            health = {
                "status": "healthy",
                "checks": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Bot connection check
            health["checks"]["bot_connection"] = {
                "status": "pass" if self.bot and self.bot.is_ready() else "fail",
                "message": "Bot is connected to Discord" if self.bot and self.bot.is_ready() else "Bot is offline"
            }
            
            # Data files check
            data_files = ["events.json", "player_stats.json", "events_history.json"]
            health["checks"]["data_files"] = {
                "status": "pass" if all(os.path.exists(f"data/{file}") for file in data_files) else "fail",
                "message": "All data files present" if all(os.path.exists(f"data/{file}") for file in data_files) else "Some data files missing"
            }
            
            # Sheets connection check
            if hasattr(self.bot, 'sheets') and self.bot.sheets:
                sheets_connected = self.bot.sheets.is_connected()
                health["checks"]["sheets_connection"] = {
                    "status": "pass" if sheets_connected else "fail",
                    "message": "Google Sheets connected" if sheets_connected else "Google Sheets disconnected"
                }
            
            # Overall status
            failed_checks = [check for check in health["checks"].values() if check["status"] == "fail"]
            if failed_checks:
                health["status"] = "degraded" if len(failed_checks) < len(health["checks"]) else "critical"
            
            return health
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_current_events(self):
        """Get current event signups for API."""
        try:
            all_data = self.data_manager.load_all_data_from_sheets()
            events = all_data.get("events", {})
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "teams": events,
                "total_signups": sum(len(team) for team in events.values())
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # Helper methods
    def calculate_uptime(self):
        """Calculate bot uptime."""
        if hasattr(self.bot, 'start_time'):
            uptime = datetime.utcnow() - self.bot.start_time
            return str(uptime).split('.')[0]  # Remove microseconds
        return "Unknown"
    
    def calculate_average_win_rate(self, player_stats):
        """Calculate average win rate across all players."""
        if not player_stats:
            return 0
        
        total_rate = 0
        active_players = 0
        
        for stats in player_stats.values():
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            total_games = wins + losses
            
            if total_games > 0:
                win_rate = (wins / total_games) * 100
                total_rate += win_rate
                active_players += 1
        
        return round(total_rate / active_players, 1) if active_players > 0 else 0
    
    def calculate_player_rank(self, stats):
        """Calculate player rank based on performance."""
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total_games = wins + losses
        
        if total_games == 0:
            return "Unranked"
        
        win_rate = (wins / total_games) * 100
        
        if win_rate >= 80 and total_games >= 10:
            return "Elite"
        elif win_rate >= 70 and total_games >= 5:
            return "Expert"
        elif win_rate >= 60:
            return "Advanced"
        elif win_rate >= 50:
            return "Intermediate"
        else:
            return "Beginner"
    
    def is_this_month(self, timestamp_str):
        """Check if timestamp is from this month."""
        if not timestamp_str:
            return False
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.utcnow()
            return timestamp.year == now.year and timestamp.month == now.month
        except:
            return False
    
    def calculate_average_participation(self, events_history):
        """Calculate average participation from events history."""
        if not events_history:
            return 0
        
        total_participants = sum(event.get("total_participants", 0) for event in events_history)
        return round(total_participants / len(events_history), 1)
    
    def get_system_health(self):
        """Get overall system health status."""
        try:
            checks = []
            
            # Check if bot is running
            if self.bot and self.bot.is_ready():
                checks.append("bot_online")
            
            # Check data files
            if os.path.exists("data/events.json"):
                checks.append("data_files")
            
            # Check sheets connection
            if hasattr(self.bot, 'sheets') and self.bot.sheets and self.bot.sheets.is_connected():
                checks.append("sheets_connected")
            
            # Determine health status
            if len(checks) >= 3:
                return {"status": "excellent", "score": 100}
            elif len(checks) >= 2:
                return {"status": "good", "score": 75}
            elif len(checks) >= 1:
                return {"status": "degraded", "score": 50}
            else:
                return {"status": "critical", "score": 25}
                
        except Exception as e:
            return {"status": "error", "score": 0, "error": str(e)}

    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the dashboard web application."""
        logger.info(f"🚀 Starting dashboard on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)

# Create global app instance
dashboard_app = None

def create_dashboard_app(bot=None):
    """Create and return dashboard application instance."""
    global dashboard_app
    dashboard_app = DashboardApp(bot)
    return dashboard_app

def get_dashboard_app():
    """Get existing dashboard application instance."""
    return dashboard_app

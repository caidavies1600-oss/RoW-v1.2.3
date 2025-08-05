
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import statistics
from utils.logger import setup_logger
from utils.data_manager import DataManager

logger = setup_logger("analytics_engine")

class AnalyticsEngine:
    def __init__(self):
        self.data_manager = DataManager()
    
    def get_team_performance_trends(self, team_key: str, days: int = 30) -> Dict[str, Any]:
        """Analyze team performance trends over time."""
        try:
            results = self.data_manager.load_json("data/event_results.json", {"history": []})
            history = results.get("history", [])
            
            # Filter results for the team within the time period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            team_results = []
            
            for entry in history:
                if entry.get("team") == team_key:
                    try:
                        entry_date = datetime.fromisoformat(entry.get("timestamp", ""))
                        if entry_date >= cutoff_date:
                            team_results.append(entry)
                    except:
                        continue
            
            # Calculate trends
            weekly_performance = defaultdict(lambda: {"wins": 0, "losses": 0})
            player_participation = defaultdict(int)
            
            for entry in team_results:
                # Weekly grouping
                entry_date = datetime.fromisoformat(entry.get("timestamp", ""))
                week_key = entry_date.strftime("%Y-W%U")
                
                if entry.get("result") == "win":
                    weekly_performance[week_key]["wins"] += 1
                else:
                    weekly_performance[week_key]["losses"] += 1
                
                # Player participation
                for player_id in entry.get("players", []):
                    player_participation[player_id] += 1
            
            # Calculate win rate trend
            win_rates = []
            for week_data in weekly_performance.values():
                total = week_data["wins"] + week_data["losses"]
                if total > 0:
                    win_rates.append(week_data["wins"] / total * 100)
            
            trend_direction = "stable"
            if len(win_rates) >= 2:
                if win_rates[-1] > win_rates[0]:
                    trend_direction = "improving"
                elif win_rates[-1] < win_rates[0]:
                    trend_direction = "declining"
            
            return {
                "team": team_key,
                "period_days": days,
                "total_games": len(team_results),
                "weekly_performance": dict(weekly_performance),
                "average_win_rate": statistics.mean(win_rates) if win_rates else 0,
                "trend_direction": trend_direction,
                "most_active_players": dict(Counter(player_participation).most_common(10))
            }
            
        except Exception as e:
            logger.error(f"Error calculating team performance trends: {e}")
            return {}
    
    def analyze_player_synergy(self, min_games_together: int = 3) -> Dict[str, Any]:
        """Analyze which players work well together."""
        try:
            results = self.data_manager.load_json("data/event_results.json", {"history": []})
            history = results.get("history", [])
            ign_map = self.data_manager.load_json("data/ign_map.json", {})
            
            # Track player combinations and their results
            pair_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})
            
            for entry in history:
                players = entry.get("players", [])
                result = entry.get("result")
                
                if len(players) >= 2 and result in ["win", "loss"]:
                    # Generate all player pairs in this game
                    for i in range(len(players)):
                        for j in range(i + 1, len(players)):
                            pair = tuple(sorted([str(players[i]), str(players[j])]))
                            pair_stats[pair]["games"] += 1
                            
                            if result == "win":
                                pair_stats[pair]["wins"] += 1
                            else:
                                pair_stats[pair]["losses"] += 1
            
            # Calculate synergy scores
            synergy_results = []
            for pair, stats in pair_stats.items():
                if stats["games"] >= min_games_together:
                    win_rate = (stats["wins"] / stats["games"]) * 100
                    player1_name = ign_map.get(pair[0], f"User_{pair[0]}")
                    player2_name = ign_map.get(pair[1], f"User_{pair[1]}")
                    
                    synergy_results.append({
                        "player1": player1_name,
                        "player2": player2_name,
                        "player1_id": pair[0],
                        "player2_id": pair[1],
                        "games_together": stats["games"],
                        "wins": stats["wins"],
                        "losses": stats["losses"],
                        "win_rate": round(win_rate, 1),
                        "synergy_score": round(win_rate, 1)  # Can be enhanced with more complex scoring
                    })
            
            # Sort by synergy score
            synergy_results.sort(key=lambda x: x["synergy_score"], reverse=True)
            
            return {
                "min_games_threshold": min_games_together,
                "total_pairs_analyzed": len(synergy_results),
                "top_synergies": synergy_results[:15],
                "average_pair_win_rate": statistics.mean([s["win_rate"] for s in synergy_results]) if synergy_results else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing player synergy: {e}")
            return {}
    
    def analyze_win_loss_patterns(self) -> Dict[str, Any]:
        """Analyze win/loss patterns by day, time, and team composition."""
        try:
            results = self.data_manager.load_json("data/event_results.json", {"history": []})
            history = results.get("history", [])
            
            day_patterns = defaultdict(lambda: {"wins": 0, "losses": 0})
            hour_patterns = defaultdict(lambda: {"wins": 0, "losses": 0})
            team_size_patterns = defaultdict(lambda: {"wins": 0, "losses": 0})
            
            for entry in history:
                try:
                    timestamp = entry.get("timestamp", "")
                    if not timestamp:
                        continue
                        
                    entry_date = datetime.fromisoformat(timestamp)
                    day_of_week = entry_date.strftime("%A")
                    hour = entry_date.hour
                    team_size = len(entry.get("players", []))
                    result = entry.get("result")
                    
                    if result in ["win", "loss"]:
                        # Day patterns
                        day_patterns[day_of_week][result + "s"] += 1
                        
                        # Hour patterns
                        hour_patterns[hour][result + "s"] += 1
                        
                        # Team size patterns
                        team_size_patterns[team_size][result + "s"] += 1
                        
                except Exception as e:
                    logger.warning(f"Skipping invalid entry: {e}")
                    continue
            
            # Calculate win rates for each pattern
            def calculate_win_rates(pattern_dict):
                result = {}
                for key, stats in pattern_dict.items():
                    total = stats["wins"] + stats["losses"]
                    if total > 0:
                        result[key] = {
                            "wins": stats["wins"],
                            "losses": stats["losses"],
                            "total": total,
                            "win_rate": round((stats["wins"] / total) * 100, 1)
                        }
                return result
            
            return {
                "day_of_week_patterns": calculate_win_rates(day_patterns),
                "hour_patterns": calculate_win_rates(hour_patterns),
                "team_size_patterns": calculate_win_rates(team_size_patterns),
                "best_day": max(calculate_win_rates(day_patterns).items(), key=lambda x: x[1]["win_rate"], default=(None, {"win_rate": 0}))[0],
                "best_hour": max(calculate_win_rates(hour_patterns).items(), key=lambda x: x[1]["win_rate"], default=(None, {"win_rate": 0}))[0],
                "optimal_team_size": max(calculate_win_rates(team_size_patterns).items(), key=lambda x: x[1]["win_rate"], default=(None, {"win_rate": 0}))[0]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing win/loss patterns: {e}")
            return {}

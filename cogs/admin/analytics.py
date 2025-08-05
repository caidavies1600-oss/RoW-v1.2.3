import discord
from discord.ext import commands
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64

from config.constants import ADMIN_ROLE_IDS, COLORS, TEAM_DISPLAY
from services.analytics_engine import AnalyticsEngine
from utils.logger import setup_logger

# Simple PredictionEngine placeholder until it's implemented
class PredictionEngine:
    def __init__(self):
        from utils.data_manager import DataManager
        self.data_manager = DataManager()
    
    def predict_team_strength(self, players, team_key):
        return {
            "strength": 0.5,
            "confidence": 0.5,
            "breakdown": {},
            "player_strengths": {}
        }
    
    def predict_match_outcome(self, team_players, enemy_team_power):
        return {
            "win_probability": 0.5,
            "team_matchmaking_power": 0,
            "alliance_factor": 1.0,
            "key_factors": ["Insufficient data for prediction"],
            "team_composition": {}
        }

logger = setup_logger("analytics")

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.analytics_engine = AnalyticsEngine()
        self.prediction_engine = PredictionEngine()

    @commands.command(name="teamtrends")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def team_performance_trends(self, ctx, team_key: str = "main_team", days: int = 30):
        """Show team performance trends over time."""
        try:
            if team_key not in TEAM_DISPLAY:
                await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
                return

            trends = self.analytics_engine.get_team_performance_trends(team_key, days)

            if not trends:
                await ctx.send("❌ No trend data available for this team.")
                return

            embed = discord.Embed(
                title=f"📈 {TEAM_DISPLAY[team_key]} Performance Trends",
                description=f"Analysis for the last {days} days",
                color=COLORS["INFO"]
            )

            embed.add_field(
                name="📊 Overview",
                value=(
                    f"**Total Games:** {trends['total_games']}\n"
                    f"**Average Win Rate:** {trends['average_win_rate']:.1f}%\n"
                    f"**Trend Direction:** {trends['trend_direction'].title()}"
                ),
                inline=False
            )

            # Weekly performance breakdown
            weekly_data = trends.get('weekly_performance', {})
            if weekly_data:
                weekly_summary = []
                for week, stats in list(weekly_data.items())[-4:]:  # Last 4 weeks
                    total = stats['wins'] + stats['losses']
                    wr = (stats['wins'] / total * 100) if total > 0 else 0
                    weekly_summary.append(f"Week {week}: {stats['wins']}W-{stats['losses']}L ({wr:.1f}%)")

                embed.add_field(
                    name="📅 Recent Weekly Performance",
                    value="\n".join(weekly_summary) or "No recent data",
                    inline=False
                )

            # Most active players
            active_players = trends.get('most_active_players', {})
            if active_players:
                top_players = []
                for player_id, games in list(active_players.items())[:5]:
                    top_players.append(f"<@{player_id}>: {games} games")

                embed.add_field(
                    name="🏃 Most Active Players",
                    value="\n".join(top_players),
                    inline=True
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in team_performance_trends: {e}")
            await ctx.send("❌ Failed to analyze team trends. Please try again.")

    @commands.command(name="synergy")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def player_synergy_analysis(self, ctx, min_games: int = 3):
        """Analyze player synergy and combinations."""
        try:
            synergy_data = self.analytics_engine.analyze_player_synergy(min_games)

            if not synergy_data or not synergy_data.get("top_synergies"):
                await ctx.send("❌ Not enough data for synergy analysis.")
                return

            embed = discord.Embed(
                title="🤝 Player Synergy Analysis",
                description=f"Best player combinations (min {min_games} games together)",
                color=COLORS["SUCCESS"]
            )

            embed.add_field(
                name="📊 Analysis Summary",
                value=(
                    f"**Pairs Analyzed:** {synergy_data['total_pairs_analyzed']}\n"
                    f"**Average Pair Win Rate:** {synergy_data['average_pair_win_rate']:.1f}%\n"
                    f"**Minimum Games:** {min_games}"
                ),
                inline=False
            )

            # Top synergistic pairs
            top_pairs = []
            for i, pair in enumerate(synergy_data["top_synergies"][:8], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
                top_pairs.append(
                    f"{emoji} **{pair['player1']}** + **{pair['player2']}**\n"
                    f"   {pair['wins']}W-{pair['losses']}L ({pair['win_rate']}%) in {pair['games_together']} games"
                )

            if top_pairs:
                embed.add_field(
                    name="🏆 Top Player Combinations",
                    value="\n\n".join(top_pairs),
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in player_synergy_analysis: {e}")
            await ctx.send("❌ Failed to analyze player synergy. Please try again.")

    @commands.command(name="patterns")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def win_loss_patterns(self, ctx):
        """Analyze win/loss patterns by day, time, and team composition."""
        try:
            patterns = self.analytics_engine.analyze_win_loss_patterns()

            if not patterns:
                await ctx.send("❌ No pattern data available.")
                return

            embed = discord.Embed(
                title="📋 Win/Loss Pattern Analysis",
                description="Performance patterns across different factors",
                color=COLORS["INFO"]
            )

            # Day of week patterns
            day_patterns = patterns.get("day_of_week_patterns", {})
            if day_patterns:
                day_summary = []
                for day, stats in day_patterns.items():
                    day_summary.append(f"**{day}:** {stats['wins']}W-{stats['losses']}L ({stats['win_rate']}%)")

                embed.add_field(
                    name="📅 Day of Week Performance",
                    value="\n".join(day_summary),
                    inline=False
                )

            # Best performance factors
            best_day = patterns.get("best_day")
            best_hour = patterns.get("best_hour")
            optimal_size = patterns.get("optimal_team_size")

            insights = []
            if best_day:
                insights.append(f"📅 **Best Day:** {best_day}")
            if best_hour is not None:
                insights.append(f"🕐 **Best Hour:** {best_hour}:00 UTC")
            if optimal_size:
                insights.append(f"👥 **Optimal Team Size:** {optimal_size} players")

            if insights:
                embed.add_field(
                    name="🎯 Key Insights",
                    value="\n".join(insights),
                    inline=False
                )

            # Team size patterns
            size_patterns = patterns.get("team_size_patterns", {})
            if size_patterns:
                size_summary = []
                for size, stats in sorted(size_patterns.items()):
                    size_summary.append(f"**{size} players:** {stats['wins']}W-{stats['losses']}L ({stats['win_rate']}%)")

                embed.add_field(
                    name="👥 Team Size Performance",
                    value="\n".join(size_summary),
                    inline=True
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in win_loss_patterns: {e}")
            await ctx.send("❌ Failed to analyze patterns. Please try again.")

    @commands.command(name="predict")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def predict_team_performance(self, ctx, team_key: str = "main_team"):
        """Predict current team's performance based on signed up players."""
        try:
            if team_key not in TEAM_DISPLAY:
                await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
                return

            # Get current team players
            event_manager = self.bot.get_cog("EventManager")
            if not event_manager:
                await ctx.send("❌ Event manager not available.")
                return

            current_players = event_manager.events.get(team_key, [])

            if not current_players:
                await ctx.send(f"❌ No players currently signed up for {TEAM_DISPLAY[team_key]}.")
                return

            prediction = self.prediction_engine.predict_team_strength(current_players, team_key)

            embed = discord.Embed(
                title=f"🔮 {TEAM_DISPLAY[team_key]} Performance Prediction",
                color=COLORS["PRIMARY"]
            )

            # Overall prediction
            strength_pct = prediction["strength"] * 100
            confidence_pct = prediction["confidence"] * 100

            strength_emoji = "🔥" if strength_pct >= 70 else "💪" if strength_pct >= 50 else "⚡"

            embed.add_field(
                name="📊 Overall Prediction",
                value=(
                    f"{strength_emoji} **Team Strength:** {strength_pct:.1f}%\n"
                    f"🎯 **Confidence:** {confidence_pct:.1f}%\n"
                    f"👥 **Players Analyzed:** {len(current_players)}"
                ),
                inline=False
            )

            # Breakdown
            breakdown = prediction.get("breakdown", {})
            if breakdown:
                embed.add_field(
                    name="🔍 Strength Breakdown",
                    value=(
                        f"**Individual Average:** {breakdown.get('individual_average', 0) * 100:.1f}%\n"
                        f"**Synergy Bonus:** {breakdown.get('synergy_bonus', 0) * 100:+.1f}%\n"
                        f"**Size Factor:** {breakdown.get('size_factor', 0) * 100:.1f}%\n"
                        f"**Historical Factor:** {breakdown.get('historical_factor', 0) * 100:.1f}%"
                    ),
                    inline=True
                )

            # Top players with power ratings
            player_strengths = prediction.get("player_strengths", {})
            if player_strengths:
                top_players = sorted(player_strengths.items(), key=lambda x: x[1], reverse=True)[:5]
                player_list = []
                for player_id, strength in top_players:
                    strength_pct = strength * 100
                    player_stats = self.prediction_engine.data_manager.player_stats.get(str(player_id), {})
                    power_rating = player_stats.get("power_rating", 0)
                    power_text = f" ({power_rating:,})" if power_rating > 0 else ""
                    player_list.append(f"<@{player_id}>: {strength_pct:.1f}%{power_text}")

                embed.add_field(
                    name="⭐ Top Performers",
                    value="\n".join(player_list),
                    inline=True
                )

            # Prediction interpretation
            if strength_pct >= 70:
                interpretation = "🚀 Excellent team composition! High win probability expected."
            elif strength_pct >= 60:
                interpretation = "💪 Strong team setup with good win chances."
            elif strength_pct >= 50:
                interpretation = "⚖️ Balanced team with moderate win probability."
            else:
                interpretation = "⚠️ Consider team adjustments for better performance."

            embed.add_field(
                name="💡 Interpretation",
                value=interpretation,
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in predict_team_performance: {e}")
            await ctx.send("❌ Failed to generate prediction. Please try again.")

    @commands.command(name="predict")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def predict_match_outcome(self, ctx, team: str = "main_team"):
        """Predict match outcome based on team composition and historical data."""
        try:
            if team not in ["main_team", "team_2", "team_3"]:
                await ctx.send("❌ Invalid team. Use: main_team, team_2, or team_3")
                return

            events = self.data_manager.load_json(FILES["EVENTS"], {})
            current_team = events.get(team, [])

            if not current_team:
                await ctx.send(f"❌ No players signed up for {team.replace('_', ' ').title()}")
                return

            # Get prediction (enemy power will be read from sheets)
            prediction = self.prediction_engine.predict_match_outcome(
                team_players=current_team,
                enemy_team_power=0  # Will be determined from sheets data
            )

            if not prediction:
                await ctx.send("❌ Unable to generate prediction. Make sure player data is filled in Google Sheets.")
                return

            # Create prediction embed
            embed = discord.Embed(
                title=f"🔮 Match Prediction: {team.replace('_', ' ').title()}",
                description="*Based on Google Sheets data and historical performance*",
                color=discord.Color.gold()
            )

            # Win probability
            win_prob = prediction.get('win_probability', 0)
            prob_color = "🟢" if win_prob >= 0.7 else "🟡" if win_prob >= 0.4 else "🔴"
            embed.add_field(
                name=f"{prob_color} Win Probability",
                value=f"{win_prob:.1%}",
                inline=True
            )

            # Team matchmaking power
            team_power = prediction.get('team_matchmaking_power', 0)
            embed.add_field(
                name="⚔️ Team Matchmaking Power",
                value=f"{team_power:,}" if team_power > 0 else "Not calculated",
                inline=True
            )

            # Alliance factor
            alliance_factor = prediction.get('alliance_factor', 1.0)
            if alliance_factor != 1.0:
                embed.add_field(
                    name="🏰 Alliance Factor",
                    value=f"{alliance_factor:.2f}x",
                    inline=True
                )

            # Key factors
            factors = prediction.get('key_factors', [])
            if factors:
                embed.add_field(
                    name="🎯 Key Factors",
                    value="\n".join(f"• {factor}" for factor in factors[:5]),
                    inline=False
                )

            # Team composition
            composition = prediction.get('team_composition', {})
            if composition:
                comp_text = []
                for spec, count in composition.items():
                    if count > 0:
                        comp_text.append(f"{spec.title()}: {count}")

                if comp_text:
                    embed.add_field(
                        name="👥 Team Specializations",
                        value=" | ".join(comp_text),
                        inline=False
                    )

            # Current team players
            player_names = []
            for player_id in current_team:
                stats = self.data_manager.player_stats.get(str(player_id), {})
                name = stats.get('name', f'Player {player_id}')
                power = stats.get('power_rating', 0)
                if power > 0:
                    player_names.append(f"{name} ({power:,})")
                else:
                    player_names.append(name)

            embed.add_field(
                name="🎮 Current Team",
                value=", ".join(player_names[:8]) + ("..." if len(player_names) > 8 else ""),
                inline=False
            )

            embed.set_footer(text="Enemy data and alliance history read from Google Sheets • Use !createsheets to set up templates")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.exception("Failed to predict match outcome")
            await ctx.send("❌ Failed to generate prediction. Make sure Google Sheets templates are created with !createsheets")

async def setup(bot):
    await bot.add_cog(Analytics(bot))
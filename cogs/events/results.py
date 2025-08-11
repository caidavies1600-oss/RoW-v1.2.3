import logging
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands

from config.constants import COLORS, FILES, TEAM_DISPLAY
from config.settings import ADMIN_ROLE_IDS
from utils.integrated_data_manager import data_manager

logger = logging.getLogger("results")


class Results(commands.Cog):
    """
    Manages RoW event results and player statistics.

    Features:
    - Win/loss recording and tracking
    - Player statistics management
    - Results history display
    - Google Sheets template creation
    - Player performance tracking
    """

    def __init__(self, bot):
        """
        Initialize the Results cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.data_manager = data_manager
        self.results = {"wins": 0, "losses": 0, "history": []}
        self.player_stats = {}  # Initialize player stats locally

    def calculate_win_rate(self, wins: int, losses: int) -> float:
        """Calculate win rate percentage from wins and losses."""
        total = wins + losses
        return (wins / total * 100) if total > 0 else 0

    async def load_results(self):
        """Load results with integrated manager."""
        self.results = await self.data_manager.load_data(
            FILES["RESULTS"],
            default={"wins": 0, "losses": 0, "history": []},
        )

    async def save_results(self) -> bool:
        """Save results with atomic operations."""
        return await self.data_manager.save_data(
            FILES["RESULTS"], self.results, sync_to_sheets=True
        )

    async def get_current_team_players(self, team_key: str):
        """
        Get current players signed up for a team.

        Args:
            team_key: Key identifying the team (main_team, team_2, team_3)

        Returns:
            list: List of player IDs currently signed up
        """
        try:
            # Get the current events from EventManager
            event_manager = self.bot.get_cog("EventManager")
            if event_manager:
                return event_manager.events.get(team_key, [])
            else:
                # Fallback to loading from file
                events = await self.data_manager.load_data(FILES["EVENTS"], {})
                return events.get(team_key, [])
        except Exception as e:
            logger.error(f"Failed to get current team players: {e}")
            return []

    async def update_player_stats_for_result(self, team_key: str, result: str, players: list):
        """
        Update individual player statistics after a match.

        Args:
            team_key: Key identifying the team
            result: Match result ('win' or 'loss')
            players: List of player IDs to update

        Updates:
            - Individual win/loss records
            - Team-specific statistics
            - Player history
        """
        try:
            # Get IGN map for player names
            ign_map = await self.data_manager.load_data(FILES["IGN_MAP"], {})

            for player_id in players:
                player_name = ign_map.get(str(player_id), f"User_{player_id}")
                await self.data_manager.update_player_stats(
                    player_id, team_key, result, player_name
                )

            # Save updated player stats
            player_stats = await self.data_manager.load_data(FILES["PLAYER_STATS"], {})
            await self.data_manager.save_data(FILES["PLAYER_STATS"], player_stats)
            logger.info(
                f"Updated player stats for {len(players)} players: {team_key} {result}"
            )

        except Exception as e:
            logger.error(f"Failed to update player stats: {e}")

    @commands.command(name="win")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_win(self, ctx, team_key: str):
        """
        Record a win for a team with current player list.

        Args:
            ctx: Command context
            team_key: Team identifier (main_team, team_2, team_3)

        Effects:
            - Updates team win count
            - Records player participation
            - Sends notifications
            - Updates player statistics
        """
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
            return

        # Get current players for this team
        current_players = await self.get_current_team_players(team_key)

        await self.load_results()
        self.results["total_wins"] = self.results.get("total_wins", 0) + 1
        self.results["history"] = self.results.get("history", [])

        result_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "result": "win",
            "team": team_key,
            "players": current_players.copy(),  # Store player list at time of result
            "recorded_by": str(ctx.author),
            "by": str(ctx.author),
        }

        self.results["history"].append(result_entry)

        # Update individual player stats
        await self.update_player_stats_for_result(team_key, "win", current_players)

        if await self.save_results():
            # Send smart notifications to players
            notifications_cog = self.bot.get_cog("NotificationsCog")
            if notifications_cog:
                await notifications_cog.smart_notifications.notify_match_result(
                    team_key, True, current_players
                )
            team_display = TEAM_DISPLAY.get(team_key, team_key)
            player_count = len(current_players)

            embed = discord.Embed(
                title="✅ Win Recorded!",
                description=f"**{team_display}** victory recorded with **{player_count} players**",
                color=COLORS["SUCCESS"],
            )
            embed.add_field(
                name="Players",
                value=", ".join([f"<@{p}>" for p in current_players[:10]]) or "None",
                inline=False,
            )
            embed.set_footer(text=f"Recorded by {ctx.author}")

            await ctx.send(embed=embed)
            logger.info(
                f"{ctx.author} recorded win for {team_key} with {player_count} players"
            )
        else:
            await ctx.send("❌ Failed to save win record. Please try again.")

    @commands.command(name="loss")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_loss(self, ctx, team_key: str):
        """
        Record a loss for a team with current player list.

        Args:
            ctx: Command context
            team_key: Team identifier (main_team, team_2, team_3)

        Effects:
            - Updates team loss count
            - Records player participation
            - Sends notifications
            - Updates player statistics
        """
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
            return

        # Get current players for this team
        current_players = await self.get_current_team_players(team_key)

        self.results["total_losses"] = self.results.get("total_losses", 0) + 1
        self.results["history"] = self.results.get("history", [])

        result_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "result": "loss",
            "team": team_key,
            "players": current_players.copy(),  # Store player list at time of result
            "recorded_by": str(ctx.author),
            "by": str(ctx.author),
        }

        self.results["history"].append(result_entry)

        # Update individual player stats
        await self.update_player_stats_for_result(team_key, "loss", current_players)

        if await self.save_results():
            # Send smart notifications to players
            notifications_cog = self.bot.get_cog("NotificationsCog")
            if notifications_cog:
                await notifications_cog.smart_notifications.notify_match_result(
                    team_key, False, current_players
                )
            team_display = TEAM_DISPLAY.get(team_key, team_key)
            player_count = len(current_players)

            embed = discord.Embed(
                title="❌ Loss Recorded",
                description=f"**{team_display}** loss recorded with **{player_count} players**",
                color=COLORS["ERROR"],
            )
            embed.add_field(
                name="Players",
                value=", ".join([f"<@{p}>" for p in current_players[:10]]) or "None",
                inline=False,
            )
            embed.set_footer(text=f"Recorded by {ctx.author}")

            await ctx.send(embed=embed)
            logger.info(
                f"{ctx.author} recorded loss for {team_key} with {player_count} players"
            )
        else:
            await ctx.send("❌ Failed to save loss record. Please try again.")

    @commands.command(name="results")
    async def show_results(self, ctx):
        """
        Show overall and recent results summary.

        Displays:
            - Total wins and losses
            - Win rate percentage
            - Last 10 match results
            - Results by team
        """
        await self.load_results()
        embed = discord.Embed(title="🏆 RoW Results Summary", color=COLORS["PRIMARY"])

        total_wins = self.results.get("total_wins", 0)
        total_losses = self.results.get("total_losses", 0)
        win_rate = self.calculate_win_rate(total_wins, total_losses)

        embed.description = (
            f"**Total Wins:** {total_wins}\n"
            f"**Total Losses:** {total_losses}\n"
            f"**Win Rate:** {win_rate:.1f}%"
        )

        recent_results = []
        for entry in self.results.get("history", [])[-10:]:
            try:
                date = datetime.fromisoformat(entry["timestamp"]).strftime("%b %d")
                team = TEAM_DISPLAY.get(entry.get("team", "unknown"), "Unknown Team")
                result = entry.get("result", "unknown")
                player_count = len(entry.get("players", []))
                emoji = "✅" if result == "win" else "❌"
                recent_results.append(
                    f"{emoji} {team} ({player_count} players) — {date}"
                )
            except Exception as e:
                logger.warning(f"Skipping invalid result entry: {e}")

        if recent_results:
            embed.add_field(
                name="📅 Recent Results (Last 10)",
                value="\n".join(recent_results),
                inline=False,
            )
        else:
            embed.add_field(
                name="📅 Recent Results", value="No results recorded yet.", inline=False
            )

        await ctx.send(embed=embed)

    async def show_player_stats(self, ctx, user: Optional[discord.User] = None):
        """
        Show detailed player statistics.

        Args:
            ctx: Command context
            user: Optional user to show stats for (defaults to command author)

        Displays:
            - Overall win/loss record
            - Team-specific performance
            - Attendance record
            - Block status
        """
        if user is None:
            user = ctx.author

        if user is None:
            await ctx.send("❌ Could not resolve user")
            return

        user_id = str(user.id)

        # Get player stats
        player_stats = await self.data_manager.load_data(FILES["PLAYER_STATS"], {})
        if user_id not in player_stats:
            await ctx.send(f"❌ No statistics found for {user.display_name}")
            return

        stats = player_stats[user_id]
        team_results = stats.get("team_results", {})

        embed = discord.Embed(
            title=f"📊 Player Statistics: {stats.get('name', user.display_name)}",
            color=COLORS["INFO"],
        )

        # Calculate totals
        total_wins = sum(team.get("wins", 0) for team in team_results.values())
        total_losses = sum(team.get("losses", 0) for team in team_results.values())
        total_games = total_wins + total_losses
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

        embed.description = (
            f"**Total Games:** {total_games}\n"
            f"**Total Wins:** {total_wins}\n"
            f"**Total Losses:** {total_losses}\n"
            f"**Win Rate:** {win_rate:.1f}%"
        )

        # Team-specific stats
        for team_key, team_name in TEAM_DISPLAY.items():
            team_stats = team_results.get(team_key, {"wins": 0, "losses": 0})
            team_wins = team_stats["wins"]
            team_losses = team_stats["losses"]
            team_total = team_wins + team_losses
            team_wr = (team_wins / team_total * 100) if team_total > 0 else 0

            embed.add_field(
                name=f"{team_name}",
                value=f"W: {team_wins} | L: {team_losses}\nWR: {team_wr:.1f}%",
                inline=True,
            )

        # Additional info
        embed.add_field(
            name="Other",
            value=f"Absents: {stats.get('absents', 0)}\nBlocked: {'Yes' if stats.get('blocked', False) else 'No'}",
            inline=True,
        )

        await ctx.send(embed=embed)

    @commands.command(name="createtemplates", aliases=["templates"])
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def create_sheets_templates(self, ctx):
        """Create Google Sheets templates with current player data for manual entry."""
        if not hasattr(self.data_manager, 'sheets_manager') or not self.data_manager.sheets_manager:
            await ctx.send("❌ Google Sheets not configured. Set environment variables and restart bot.")
            return

        try:
            # Send initial message
            status_msg = await ctx.send("🔄 Creating Google Sheets templates... This may take a few minutes due to rate limiting.")

            # Gather current player data for template creation
            all_data = {
                "events": await self.data_manager.load_data(FILES["EVENTS"], {}),
                "blocked": await self.data_manager.load_data(FILES["BLOCKED"], {}),
                "results": self.results,
                "player_stats": await self.data_manager.load_data("data/player_stats.json", {}),
                "ign_map": await self.data_manager.load_data(FILES["IGN_MAP"], {}),
                "absent": await self.data_manager.load_data(FILES["ABSENT"], {}),
                "notification_preferences": await self.data_manager.load_data("data/notification_preferences.json", {})
            }

            # Create templates with detailed results
            if hasattr(self.data_manager.sheets_manager, 'setup_templates'):
                results = self.data_manager.sheets_manager.setup_templates(all_data)
            elif hasattr(self.data_manager.sheets_manager, 'create_all_templates'):
                template_results = self.data_manager.sheets_manager.create_all_templates(all_data)
                # Convert to expected format
                results = {
                    "connected": template_results.get("connected", False),
                    "summary": {
                        "success_count": sum(1 for v in template_results.values() if v is True),
                        "total_count": len([k for k in template_results.keys() if k != "connected"])
                    }
                }
                # Copy individual template results
                results.update(template_results)
            else:
                results = {"connected": False, "summary": {"success_count": 0, "total_count": 0}}

            if not results.get("connected", False):
                await status_msg.edit(content="❌ Could not connect to Google Sheets. Check credentials.")
                return

            # Build detailed results message
            embed = discord.Embed(
                title="📊 Google Sheets Template Creation Results",
                color=discord.Color.green() if results.get("summary", {}).get("success_count", 0) >= 3 else discord.Color.orange()
            )

            # Add summary
            summary = results.get("summary", {})
            success_count = summary.get("success_count", 0)
            total_count = summary.get("total_count", 0)

            embed.add_field(
                name="📈 Summary",
                value=f"**{success_count}/{total_count}** templates created successfully",
                inline=False
            )

            # Add individual results
            template_status = []
            template_names = {
                "player_stats": "📊 Player Stats",
                "alliance_tracking": "🏰 Alliance Tracking",
                "dashboard": "📋 Dashboard",
                "current_teams": "👥 Current Teams"
            }

            for key, name in template_names.items():
                status = "✅" if results.get(key, False) else "❌"
                template_status.append(f"{status} {name}")

            embed.add_field(
                name="📝 Template Status",
                value="\n".join(template_status),
                inline=False
            )

            # Add spreadsheet link if available
            if hasattr(self.data_manager.sheets_manager, 'spreadsheet') and self.data_manager.sheets_manager.spreadsheet:
                sheets_url = self.data_manager.sheets_manager.spreadsheet.url
                embed.add_field(
                    name="🔗 Spreadsheet",
                    value=f"[📊 Open Google Sheets]({sheets_url})",
                    inline=False
                )
            elif hasattr(self.data_manager.sheets_manager, 'get_spreadsheet_url'):
                sheets_url = self.data_manager.sheets_manager.get_spreadsheet_url()
                if sheets_url:
                    embed.add_field(
                        name="🔗 Spreadsheet",
                        value=f"[📊 Open Google Sheets]({sheets_url})",
                        inline=False
                    )

            # Add instructions
            if success_count > 0:
                embed.add_field(
                    name="📝 Next Steps",
                    value="• Fill in player power ratings in Player Stats sheet\n• Add match data manually\n• Update alliance information\n• All changes sync automatically",
                    inline=False
                )

            # Add footer with timing info
            embed.set_footer(text="Templates created with rate limiting to prevent API errors")

            await status_msg.edit(content="", embed=embed)

        except Exception as e:
            logger.exception("Failed to create sheets templates")
            await ctx.send(f"❌ Failed to create templates: {str(e)[:100]}...")


async def setup(bot):
    """
    Set up the Results cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(Results(bot))
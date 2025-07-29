import discord
from discord.ext import commands
from datetime import datetime
import logging

from config.constants import FILES, TEAM_DISPLAY, EMOJIS, COLORS
from config.settings import ADMIN_ROLE_IDS
from utils.helpers import Helpers
from utils.data_manager import DataManager

logger = logging.getLogger("results")

class Results(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()
        self.results = self.load_results()

    def load_results(self):
        """Load result data using DataManager."""
        default_results = {
            "total_wins": 0,
            "total_losses": 0,
            "history": []
        }
        return self.data_manager.load_json(FILES["RESULTS"], default_results)

    def save_results(self):
        """Save result data using DataManager."""
        success = self.data_manager.save_json(FILES["RESULTS"], self.results)
        if not success:
            logger.error("❌ Failed to save results data")
        return success

    @commands.command(name="win")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_win(self, ctx, team_key: str):
        """Record a win for a team."""
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
            return

        self.results["total_wins"] = self.results.get("total_wins", 0) + 1
        self.results["history"] = self.results.get("history", [])
        self.results["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": "win",
            "team": team_key,
            "recorded_by": str(ctx.author)
        })
        
        if self.save_results():
            team_display = TEAM_DISPLAY.get(team_key, team_key)
            await ctx.send(f"✅ Win recorded for **{team_display}**.")
            logger.info(f"{ctx.author} recorded win for {team_key}")
        else:
            await ctx.send("❌ Failed to save win record. Please try again.")

    @commands.command(name="loss")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_loss(self, ctx, team_key: str):
        """Record a loss for a team."""
        team_key = team_key.lower()
        if team_key not in TEAM_DISPLAY:
            await ctx.send("❌ Invalid team key. Use: main_team, team_2, or team_3")
            return

        self.results["total_losses"] = self.results.get("total_losses", 0) + 1
        self.results["history"] = self.results.get("history", [])
        self.results["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": "loss",
            "team": team_key,
            "recorded_by": str(ctx.author)
        })
        
        if self.save_results():
            team_display = TEAM_DISPLAY.get(team_key, team_key)
            await ctx.send(f"❌ Loss recorded for **{team_display}**.")
            logger.info(f"{ctx.author} recorded loss for {team_key}")
        else:
            await ctx.send("❌ Failed to save loss record. Please try again.")

    @commands.command(name="results")
    async def show_results(self, ctx):
        """Show overall and recent results summary."""
        self.results = self.load_results()
        
        embed = discord.Embed(
            title="🏆 RoW Results Summary",
            color=COLORS["PRIMARY"]
        )

        total_wins = self.results.get("total_wins", 0)
        total_losses = self.results.get("total_losses", 0)
        win_rate = Helpers.calculate_win_rate(total_wins, total_losses)

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
                emoji = "✅" if result == "win" else "❌"
                recent_results.append(f"{emoji} {team} — {date}")
            except Exception as e:
                logger.warning(f"Skipping invalid result entry: {e}")

        if recent_results:
            embed.add_field(
                name="📅 Recent Results (Last 10)",
                value="\n".join(recent_results),
                inline=False
            )
        else:
            embed.add_field(
                name="📅 Recent Results",
                value="No results recorded yet.",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Results(bot))
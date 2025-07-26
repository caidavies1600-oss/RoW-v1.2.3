import discord
from discord.ext import commands
from datetime import datetime
import logging

from config.constants import RESULTS_FILE, TEAM_DISPLAY, EMOJIS, ADMIN_ROLE_IDS
from utils.helpers import Helpers
import json
import os

logger = logging.getLogger("results")

def load_results():
    """Load result data from file."""
    if not os.path.exists(RESULTS_FILE):
        return {team: {"wins": 0, "losses": 0, "recent": []} for team in TEAM_DISPLAY}

    try:
        with open(RESULTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Failed to load results file: {e}")
        return {team: {"wins": 0, "losses": 0, "recent": []} for team in TEAM_DISPLAY}

def save_results(data):
    """Save result data to file."""
    try:
        os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
        with open(RESULTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Failed to save results file: {e}")

class Results(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.results = load_results()

    @commands.command(name="win")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_win(self, ctx, team_key: str):
        """Record a win for a team."""
        team_key = team_key.lower()
        if team_key not in self.results:
            await ctx.send("❌ Invalid team key.")
            return

        self.results[team_key]["wins"] += 1
        self.results[team_key]["recent"].append({
            "date": datetime.utcnow().isoformat(),
            "result": "win",
            "by": str(ctx.author)
        })
        save_results(self.results)
        await ctx.send(f"✅ Win recorded for **{TEAM_DISPLAY[team_key]}**.")

    @commands.command(name="loss")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def record_loss(self, ctx, team_key: str):
        """Record a loss for a team."""
        team_key = team_key.lower()
        if team_key not in self.results:
            await ctx.send("❌ Invalid team key.")
            return

        self.results[team_key]["losses"] += 1
        self.results[team_key]["recent"].append({
            "date": datetime.utcnow().isoformat(),
            "result": "loss",
            "by": str(ctx.author)
        })
        save_results(self.results)
        await ctx.send(f"❌ Loss recorded for **{TEAM_DISPLAY[team_key]}**.")

    @commands.command(name="results")
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def show_results(self, ctx):
        """Show overall and recent results summary."""
        embed = Helpers.create_embed(
            title="🏆 RoW Results Summary",
            color=discord.Color.gold()
        )

        # Total + team stats
        total_wins = sum(t["wins"] for t in self.results.values())
        total_losses = sum(t["losses"] for t in self.results.values())
        win_rate = Helpers.calculate_win_rate(total_wins, total_losses)

        embed.description = (
            f"**Total Wins:** {total_wins}\n"
            f"**Total Losses:** {total_losses}\n"
            f"**Win Rate:** {win_rate:.1f}%"
        )

        for team_key, data in self.results.items():
            wins = data["wins"]
            losses = data["losses"]
            team_name = TEAM_DISPLAY.get(team_key, team_key.title())
            embed.add_field(
                name=f"{EMOJIS['DOT']} {team_name}",
                value=f"✅ {wins} | ❌ {losses}",
                inline=True
            )

        # Last 5 results
        all_recent = []
        for team_key, data in self.results.items():
            for r in data["recent"][-5:]:
                all_recent.append({
                    **r,
                    "team": TEAM_DISPLAY.get(team_key, team_key.title())
                })

        all_recent.sort(key=lambda r: r["date"], reverse=True)
        if all_recent:
            recent_text = ""
            for r in all_recent[:5]:
                date = datetime.fromisoformat(r["date"]).strftime("%b %d, %Y")
                emoji = "✅" if r["result"] == "win" else "❌"
                recent_text += f"{emoji} {r['team']} — {date} (by {r['by']})\n"
            embed.add_field(name="📅 Recent Results", value=recent_text, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Results(bot))

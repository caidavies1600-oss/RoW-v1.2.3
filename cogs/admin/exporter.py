import discord
from discord.ext import commands
import tempfile
import os
from datetime import datetime

from config.constants import FILES
from config.settings import ADMIN_ROLE_IDS
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("exporter")


class Exporter(commands.Cog):
    """
    Handles data export functionality for RoW bot.
    
    Provides commands to export:
    - Current team signups
    - Event participation history
    
    Exports are provided as formatted text files.
    """

    def __init__(self, bot):
        """
        Initialize the Exporter cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.data_manager = DataManager()

    @commands.command()
    @commands.check(lambda ctx: any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles))
    async def exportteams(self, ctx):
        """
        Export current team signups to a text file.

        Args:
            ctx: The command context

        Requires:
            Admin role permissions

        Exports:
            - Current timestamp
            - Team rosters with player counts
            - Total player count
            - Formatted as a text file attachment
        """
        try:
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await ctx.send("❌ Event system not available.")
                return

            data = event_cog.events
            lines = []

            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"RoW Team Export - {timestamp}\n")
            lines.append("=" * 50)
            lines.append("")

            total_players = 0
            for team, members in data.items():
                team_name = team.replace('_', ' ').title()
                lines.append(f"# {team_name} ({len(members)} players)")
                lines.append("-" * 30)

                if members:
                    for i, user in enumerate(members, 1):
                        lines.append(f"{i:2d}. {user}")
                    total_players += len(members)
                else:
                    lines.append("No members signed up")

                lines.append("")

            lines.append(f"Total players across all teams: {total_players}")

            text = "\n".join(lines)

            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as temp:
                temp.write(text)
                temp_path = temp.name

            await ctx.send(
                content=f"📋 **Team Export Complete** - {total_players} total players signed up",
                file=discord.File(temp_path, filename="team_export.txt")
            )
            logger.info(f"{ctx.author} exported team list ({total_players} players).")

            os.remove(temp_path)

        except Exception:
            logger.exception("Error in exportteams command:")
            await ctx.send("❌ Failed to export team data.")

    @commands.command()
    @commands.check(lambda ctx: any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles))
    async def exporthistory(self, ctx):
        """
        Export event history to a text file.

        Args:
            ctx: The command context

        Requires:
            Admin role permissions

        Exports:
            - Event timestamps
            - Team compositions per event
            - Player counts per team
            - Total event count
            - Formatted as a text file attachment
        """
        try:
            history = self.data_manager.load_json(FILES["HISTORY"], [])

            if not history:
                await ctx.send("❌ No event history found.")
                return

            lines = []
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"RoW Event History Export - {timestamp}\n")
            lines.append("=" * 60)
            lines.append("")

            for i, entry in enumerate(history, 1):
                event_date = entry.get("timestamp", "Unknown")
                lines.append(f"Event #{i} - {event_date}")
                lines.append("-" * 40)

                teams = entry.get("teams", {})
                for team, members in teams.items():
                    team_name = team.replace('_', ' ').title()
                    lines.append(f"{team_name}: {len(members)} players")
                    if members:
                        member_list = ", ".join(members[:10])
                        if len(members) > 10:
                            member_list += f" ... (+{len(members) - 10} more)"
                        lines.append(f"  {member_list}")

                lines.append("")

            lines.append(f"Total events recorded: {len(history)}")

            text = "\n".join(lines)

            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as temp:
                temp.write(text)
                temp_path = temp.name

            await ctx.send(
                content=f"📚 **Event History Export Complete** - {len(history)} events recorded",
                file=discord.File(temp_path, filename="event_history.txt")
            )
            logger.info(f"{ctx.author} exported event history ({len(history)} events).")

            os.remove(temp_path)

        except Exception:
            logger.exception("Error in exporthistory command:")
            await ctx.send("❌ Failed to export history data.")


async def setup(bot):
    """
    Set up the Exporter cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(Exporter(bot))

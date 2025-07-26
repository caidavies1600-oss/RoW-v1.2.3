# cogs/user/commands.py

import discord
from discord.ext import commands
import json
import os
from config.constants import ADMIN_ROLE_IDS


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ign_map = {}
        self.ign_file = "data/ign_map.json"
        self.load_ign_map()

    def load_ign_map(self):
        if os.path.exists(self.ign_file):
            with open(self.ign_file, "r") as f:
                self.ign_map = json.load(f)
        else:
            self.ign_map = {}

    def save_ign_map(self):
        with open(self.ign_file, "w") as f:
            json.dump(self.ign_map, f, indent=4)

    def get_ign(self, user):
        return self.ign_map.get(str(user.id))

    def has_ign(self, user):
        return str(user.id) in self.ign_map

    async def warn_if_no_ign(self, interaction: discord.Interaction):
        if not self.has_ign(interaction.user):
            await interaction.response.send_message(
                "⚠️ You haven't set your IGN yet. Use `!setign YourName`.",
                ephemeral=True
            )

    @commands.command(name="commands", help="Show available commands.")
    async def list_commands(self, ctx):
        """List all available commands dynamically, split by user/admin."""
        is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

        user_cmds = []
        admin_cmds = []

        # Known admin-only command names
        admin_command_names = {
            "startevent", "flagabsent", "clearabsent", "win", "loss",
            "exportteams", "exporthistory", "absencerecord", "rowstats"
        }

        for command in self.bot.commands:
            if command.hidden or command.name == "commands":
                continue

            if command.name != command.qualified_name:
                continue  # Skip aliases

            name = f"`!{command.name}`"
            desc = command.help or "No description"
            line = f"{name} — {desc}"

            is_admin_cmd = command.name in admin_command_names

            if not is_admin_cmd:
                for check in command.checks:
                    if hasattr(check, "__closure__"):
                        for cell in check.__closure__ or []:
                            if isinstance(cell.cell_contents, (list, tuple)):
                                if any(role_id in cell.cell_contents for role_id in ADMIN_ROLE_IDS):
                                    is_admin_cmd = True
                                    break

            if is_admin_cmd:
                admin_cmds.append(line)
            else:
                user_cmds.append(line)

        embed = discord.Embed(
            title="📜 Available Bot Commands",
            color=discord.Color.blurple()
        )
        embed.add_field(name="👤 User Commands", value="\n".join(user_cmds) or "None", inline=False)

        if is_admin:
            embed.add_field(name="🛡️ Admin Commands", value="\n".join(admin_cmds) or "None", inline=False)
        else:
            embed.set_footer(text="Admin commands are only visible if you have the required roles.")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UserCommands(bot))

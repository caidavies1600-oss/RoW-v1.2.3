import discord
from discord.ui import View, Button
from config.constants import EMOJIS, TEAM_DISPLAY, FILES
from config.settings import MAX_TEAM_SIZE
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("signup_view")

class EventSignupView(View):
    def __init__(self, manager):
        super().__init__(timeout=None)
        self.manager = manager

        self.add_item(JoinButton("main_team", "Join Main Team"))
        self.add_item(JoinButton("team_2", "Join Team 2"))
        self.add_item(JoinButton("team_3", "Join Team 3"))
        self.add_item(LeaveButton())

class JoinButton(Button):
    def __init__(self, team_key: str, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.team_key = team_key

    async def callback(self, interaction: discord.Interaction):
        manager = self.view.manager
        user_id = str(interaction.user.id)  # Store as string for consistency

        if manager.is_user_blocked(interaction.user.id):
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} You are currently blocked from signing up.",
                ephemeral=True
            )
            return

        # Get user's IGN
        profile_cog = manager.bot.get_cog("Profile")
        if profile_cog and profile_cog.has_ign(interaction.user):
            user_display = profile_cog.get_ign(interaction.user)
        else:
            user_display = interaction.user.display_name

        # Check if already in this team
        if user_id in manager.events.get(self.team_key, []):
            await interaction.response.send_message(
                f"{EMOJIS['SUCCESS']} You're already in {TEAM_DISPLAY[self.team_key]}!",
                ephemeral=True
            )
            return

        # Check capacity
        if len(manager.events.get(self.team_key, [])) >= MAX_TEAM_SIZE:
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} {TEAM_DISPLAY[self.team_key]} is full ({MAX_TEAM_SIZE}/{MAX_TEAM_SIZE})!",
                ephemeral=True
            )
            return

        # Remove user from all other teams first
        for team in manager.events:
            if user_id in manager.events[team] and team != self.team_key:
                manager.events[team].remove(user_id)

        # Add to selected team
        if self.team_key not in manager.events:
            manager.events[self.team_key] = []
        manager.events[self.team_key].append(user_id)

        # Save using DataManager
        if manager.data_manager.save_json(FILES["EVENTS"], manager.events):
            logger.info(f"{interaction.user} ({user_display}) joined {self.team_key}")
            await interaction.response.send_message(
                f"{EMOJIS['SUCCESS']} {user_display} joined {TEAM_DISPLAY[self.team_key]}!",
                ephemeral=True
            )
        else:
            # Rollback on save failure
            manager.events[self.team_key].remove(user_id)
            logger.error(f"Failed to save signup for {interaction.user}")
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} Failed to save your signup. Please try again.",
                ephemeral=True
            )

class LeaveButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Leave Team")

    async def callback(self, interaction: discord.Interaction):
        manager = self.view.manager
        user_id = str(interaction.user.id)  # Store as string for consistency

        # Get user's display name
        profile_cog = manager.bot.get_cog("Profile")
        if profile_cog and profile_cog.has_ign(interaction.user):
            user_display = profile_cog.get_ign(interaction.user)
        else:
            user_display = interaction.user.display_name

        # Track what was removed for rollback
        removed_from = None
        removed_teams = []

        # Remove from all teams
        for team, members in manager.events.items():
            if user_id in members:
                members.remove(user_id)
                removed_teams.append((team, user_id))
                removed_from = team

        if removed_teams:
            # Save using DataManager
            if manager.data_manager.save_json(FILES["EVENTS"], manager.events):
                logger.info(f"{interaction.user} ({user_display}) left their team")
                team_display = TEAM_DISPLAY.get(removed_from, removed_from.replace('_', ' ').title())
                await interaction.response.send_message(
                    f"{EMOJIS['SUCCESS']} {user_display} has left **{team_display}**.",
                    ephemeral=True
                )
            else:
                # Rollback on save failure
                for team, uid in removed_teams:
                    manager.events[team].append(uid)
                logger.error(f"Failed to save leave action for {interaction.user}")
                await interaction.response.send_message(
                    f"{EMOJIS['ERROR']} Failed to save changes. Please try again.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"{EMOJIS['INFO']} You're not signed up for any team.",
                ephemeral=True
            )
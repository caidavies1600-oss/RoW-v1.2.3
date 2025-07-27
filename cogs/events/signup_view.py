
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
        self.data_manager = DataManager()

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
        data_manager = self.view.data_manager
        user_id = interaction.user.id

        if manager.is_user_blocked(user_id):
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} You are currently blocked from signing up.",
                ephemeral=True
            )
            return

        # Get user's IGN
        profile_cog = interaction.client.get_cog("Profile")
        if profile_cog and profile_cog.has_ign(interaction.user):
            user_ign = profile_cog.get_ign(interaction.user)
        else:
            user_ign = interaction.user.display_name

        # Remove user from all teams (check both ID and IGN for compatibility)
        for team in manager.events:
            # Remove by ID
            if user_id in manager.events[team]:
                manager.events[team].remove(user_id)
            # Remove by IGN  
            if user_ign in manager.events[team]:
                manager.events[team].remove(user_ign)

        # Check capacity
        if len(manager.events[self.team_key]) >= MAX_TEAM_SIZE:
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} {TEAM_DISPLAY[self.team_key]} is full!",
                ephemeral=True
            )
            return

        # Add user by IGN (consistent with display)
        manager.events[self.team_key].append(user_ign)
        manager.save_events()

        logger.info(f"{interaction.user} ({user_ign}) joined {self.team_key}")

        await interaction.response.send_message(
            f"{EMOJIS['SUCCESS']} You joined {TEAM_DISPLAY[self.team_key]}!",
            ephemeral=True
        )

class LeaveButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Leave Team")

    async def callback(self, interaction: discord.Interaction):
        manager = self.view.manager
        data_manager = self.view.data_manager
        user_id = interaction.user.id

        # Get user's IGN
        profile_cog = interaction.client.get_cog("Profile")
        if profile_cog and profile_cog.has_ign(interaction.user):
            user_ign = profile_cog.get_ign(interaction.user)
        else:
            user_ign = interaction.user.display_name

        removed = False
        for team in manager.events:
            # Remove by ID
            if user_id in manager.events[team]:
                manager.events[team].remove(user_id)
                removed = True
            # Remove by IGN
            if user_ign in manager.events[team]:
                manager.events[team].remove(user_ign)
                removed = True

        if removed:
            manager.save_events()
            logger.info(f"{interaction.user} ({user_ign}) left their team")

            await interaction.response.send_message(
                f"{EMOJIS['WARNING']} You have been removed from your team.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{EMOJIS['INFO']} You were not signed up for any team.",
                ephemeral=True
            )

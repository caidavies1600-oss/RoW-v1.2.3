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

        # Remove user from all teams
        for team in manager.events:
            if user_id in manager.events[team]:
                manager.events[team].remove(user_id)

        # Check capacity
        if len(manager.events[self.team_key]) >= MAX_TEAM_SIZE:
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} {TEAM_DISPLAY[self.team_key]} is full!",
                ephemeral=True
            )
            return

        manager.events[self.team_key].append(user_id)

        # Save updated team data
        success = data_manager.save_json(FILES["EVENTS"], manager.events)
        if success:
            logger.info(f"{interaction.user} joined {self.team_key}")
        else:
            logger.warning(f"Failed to save signup for {interaction.user}")

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

        removed = False
        for team in manager.events:
            if user_id in manager.events[team]:
                manager.events[team].remove(user_id)
                removed = True

        if removed:
            success = data_manager.save_json(FILES["EVENTS"], manager.events)
            if success:
                logger.info(f"{interaction.user} left their team")
            else:
                logger.warning(f"Failed to save leave action for {interaction.user}")

            await interaction.response.send_message(
                f"{EMOJIS['WARNING']} You have been removed from your team.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{EMOJIS['INFO']} You were not signed up to any team.",
                ephemeral=True
            )

import discord
from discord.ui import Button, View

from config.constants import EMOJIS, TEAM_DISPLAY
from config.settings import MAIN_TEAM_ROLE_ID, MAX_TEAM_SIZE
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("signup_view")


class EventSignupView(View):
    """
    View containing buttons for RoW event team signups.

    Features:
    - Team joining buttons (Main Team, Team 2, Team 3)
    - Team leaving functionality
    - Role-based access control
    - Player IGN validation
    """

    def __init__(self, manager):
        """
        Initialize the signup view with team buttons.

        Args:
            manager: EventManager instance for handling team data
        """
        super().__init__(timeout=None)
        self.manager = manager
        self.data_manager = DataManager()

        self.add_item(JoinButton("main_team", "Join Main Team", requires_role=True))
        self.add_item(JoinButton("team_2", "Join Team 2"))
        self.add_item(JoinButton("team_3", "Join Team 3"))
        self.add_item(LeaveButton())


class JoinButton(Button):
    """
    Button for joining a specific RoW team.

    Features:
    - Team capacity checking
    - Role requirement validation
    - Block status checking
    - IGN validation
    - Automatic team switching
    """

    def __init__(self, team_key: str, label: str, requires_role: bool = False):
        """
        Initialize a team join button.

        Args:
            team_key: Identifier for the team (main_team, team_2, team_3)
            label: Display text for the button
            requires_role: Whether the button requires a specific role
        """
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.team_key = team_key
        self.requires_role = requires_role

    async def callback(self, interaction: discord.Interaction):
        """
        Handle button click for team joining.

        Args:
            interaction: Discord interaction event

        Checks:
        - Signup lock status
        - User block status
        - Role requirements
        - IGN setup
        - Team capacity

        Effects:
        - Removes user from other teams
        - Adds user to selected team
        - Saves changes
        - Sends confirmation
        """
        manager = self.view.manager
        data_manager = self.view.data_manager

        # Check if signups are locked
        if manager.is_signup_locked():
            await interaction.response.send_message(
                f"🔒 {EMOJIS['ERROR']} Signups are currently locked! Teams have been finalized for this week.",
                ephemeral=True,
            )
            return

        # Check if user is blocked
        if manager.is_user_blocked(interaction.user.id):
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} You are currently blocked from signing up.",
                ephemeral=True,
            )
            return

        # Check role requirement for main team
        if self.requires_role:
            if not any(role.id == MAIN_TEAM_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message(
                    "❌ You don't have permission to join the Main Team.",
                    ephemeral=True,
                )
                return

        # Get user's IGN
        profile_cog = manager.bot.get_cog("Profile")
        if profile_cog:
            user_ign = profile_cog.get_ign(interaction.user)
            if not user_ign:
                await interaction.response.send_message(
                    f"{EMOJIS['WARNING']} You haven't set your IGN yet. Use `!setign YourName` first.",
                    ephemeral=True,
                )
                return
        else:
            user_ign = interaction.user.display_name

        # Check if already in this team
        if user_ign in manager.events[self.team_key]:
            await interaction.response.send_message(
                f"{EMOJIS['SUCCESS']} You're already in {TEAM_DISPLAY[self.team_key]}!",
                ephemeral=True,
            )
            return

        # Check capacity
        if len(manager.events[self.team_key]) >= MAX_TEAM_SIZE:
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} {TEAM_DISPLAY[self.team_key]} is full!",
                ephemeral=True,
            )
            return

        # Remove user from all teams (using IGN)
        for team in manager.events:
            if user_ign in manager.events[team]:
                manager.events[team].remove(user_ign)

        # Add to new team
        manager.events[self.team_key].append(user_ign)

        # Save updated team data
        if await manager.save_events():
            logger.info(f"{interaction.user} ({user_ign}) joined {self.team_key}")
            await interaction.response.send_message(
                f"{EMOJIS['SUCCESS']} {user_ign} joined {TEAM_DISPLAY[self.team_key]}!",
                ephemeral=True,
            )
        else:
            logger.error(f"Failed to save signup for {interaction.user}")
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} Failed to save your signup. Please try again.",
                ephemeral=True,
            )


class LeaveButton(Button):
    """
    Button for leaving current RoW team.

    Features:
    - Removes player from any team
    - Handles locked signup states
    - Validates IGN status
    """

    def __init__(self):
        """Initialize the leave team button."""
        super().__init__(style=discord.ButtonStyle.danger, label="Leave Team")

    async def callback(self, interaction: discord.Interaction):
        """
        Handle button click for team leaving.

        Args:
            interaction: Discord interaction event

        Checks:
        - Signup lock status
        - IGN status
        - Current team membership

        Effects:
        - Removes user from current team
        - Saves changes
        - Sends confirmation
        """
        manager = self.view.manager

        # Check if signups are locked
        if manager.is_signup_locked():
            await interaction.response.send_message(
                f"🔒 {EMOJIS['ERROR']} Signups are locked! You cannot leave your team at this time.",
                ephemeral=True,
            )
            return

        # Get user's IGN
        profile_cog = manager.bot.get_cog("Profile")
        if profile_cog:
            user_ign = profile_cog.get_ign(interaction.user)
            if not user_ign:
                await interaction.response.send_message(
                    f"{EMOJIS['INFO']} You haven't set an IGN, so you're not in any team.",
                    ephemeral=True,
                )
                return
        else:
            user_ign = interaction.user.display_name

        # Remove from all teams
        removed = False
        removed_from = None
        for team in manager.events:
            if user_ign in manager.events[team]:
                manager.events[team].remove(user_ign)
                removed = True
                removed_from = team
                break

        if removed:
            if await manager.save_events():
                logger.info(f"{interaction.user} ({user_ign}) left {removed_from}")
                await interaction.response.send_message(
                    f"{EMOJIS['WARNING']} {user_ign} has been removed from {TEAM_DISPLAY[removed_from]}.",
                    ephemeral=True,
                )
            else:
                logger.error(f"Failed to save leave action for {interaction.user}")
                await interaction.response.send_message(
                    f"{EMOJIS['ERROR']} Failed to save your action. Please try again.",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                f"{EMOJIS['INFO']} You were not signed up to any team.", ephemeral=True
            )

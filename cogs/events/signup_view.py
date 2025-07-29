import discord
from discord.ui import View, Button
from config.constants import EMOJIS, TEAM_DISPLAY, FILES, MAIN_TEAM_ROLE_ID
from config.settings import MAX_TEAM_SIZE
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger(“signup_view”)

class EventSignupView(View):
def **init**(self, manager):
super().**init**(timeout=None)
self.manager = manager
self.data_manager = DataManager()

```
    self.add_item(JoinButton("main_team", "Join Main Team", "🏆"))
    self.add_item(JoinButton("team_2", "Join Team 2", "🔸"))
    self.add_item(JoinButton("team_3", "Join Team 3", "🔸"))
    self.add_item(LeaveButton())
```

class JoinButton(Button):
def **init**(self, team_key: str, label: str, emoji: str):
super().**init**(style=discord.ButtonStyle.primary, label=label, emoji=emoji)
self.team_key = team_key

```
async def callback(self, interaction: discord.Interaction):
    manager = self.view.manager
    user_id = str(interaction.user.id)  # Store as string for consistency

    # Check if user is blocked
    if manager.is_user_blocked(interaction.user.id):
        await interaction.response.send_message(
            f"{EMOJIS['ERROR']} You are currently blocked from signing up.",
            ephemeral=True
        )
        return

    # Check role permission for main team
    if self.team_key == "main_team":
        if not any(role.id == MAIN_TEAM_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} You don't have permission to join the Main Team.",
                ephemeral=True
            )
            return

    # Get user's IGN
    profile_cog = interaction.client.get_cog("Profile")
    if profile_cog and profile_cog.has_ign(interaction.user):
        user_display = profile_cog.get_ign(interaction.user)
    else:
        user_display = interaction.user.display_name

    # Remove user from all teams first
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

    # Add to new team
    manager.events[self.team_key].append(user_id)
    manager.save_events()

    logger.info(f"{interaction.user} ({user_display}) joined {self.team_key}")
    await interaction.response.send_message(
        f"{EMOJIS['SUCCESS']} You joined {TEAM_DISPLAY[self.team_key]}!",
        ephemeral=True
    )
```

class LeaveButton(Button):
def **init**(self):
super().**init**(style=discord.ButtonStyle.danger, label=“Leave Team”, emoji=“❌”)

```
async def callback(self, interaction: discord.Interaction):
    manager = self.view.manager
    user_id = str(interaction.user.id)

    # Get user's IGN for logging
    profile_cog = interaction.client.get_cog("Profile")
    if profile_cog and profile_cog.has_ign(interaction.user):
        user_display = profile_cog.get_ign(interaction.user)
    else:
        user_display = interaction.user.display_name

    removed_from = None
    for team in manager.events:
        if user_id in manager.events[team]:
            manager.events[team].remove(user_id)
            removed_from = team
            break

    if removed_from:
        manager.save_events()
        logger.info(f"{interaction.user} ({user_display}) left {removed_from}")
        team_display = TEAM_DISPLAY.get(removed_from, removed_from.replace('_', ' ').title())
        await interaction.response.send_message(
            f"{EMOJIS['WARNING']} You have left {team_display}.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"{EMOJIS['INFO']} You were not signed up to any team.",
            ephemeral=True
        )
```
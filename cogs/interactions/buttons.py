
import discord
from discord.ext import commands
from config.constants import MAIN_TEAM_ROLE_ID, EMOJIS

class EventButtons(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)  # View is now persistent
        self.bot = bot

    async def get_user_ign(self, interaction):
        """Helper to get user's IGN from profile system."""
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            if profile_cog.has_ign(interaction.user):
                return profile_cog.get_ign(interaction.user)
            else:
                await interaction.response.send_message(
                    f"{EMOJIS['WARNING']} You haven't set your IGN yet. Use `!setign YourName`.",
                    ephemeral=True
                )
                return None
        return interaction.user.display_name

    @discord.ui.button(
        label="Join Main Team",
        style=discord.ButtonStyle.primary,
        emoji="🏆",
        custom_id="join_main_team_btn"
    )
    async def join_main_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle main team join button."""
        try:
            # Fixed: Changed from "Events" to "EventManager"
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await interaction.response.send_message(
                    f"{EMOJIS['ERROR']} Event system not available.", ephemeral=True)
                return

            if event_cog.is_user_blocked(interaction.user.id):
                await interaction.response.send_message(
                    f"{EMOJIS['BLOCKED']} You are currently blocked from events.", ephemeral=True)
                return

            user_ign = await self.get_user_ign(interaction)
            if not user_ign:
                return

            if not any(role.id == MAIN_TEAM_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message(
                    f"{EMOJIS['ERROR']} You don't have permission to join the Main Team.", ephemeral=True)
                return

            if user_ign in event_cog.events["main_team"]:
                await interaction.response.send_message(
                    f"{EMOJIS['SUCCESS']} You're already in the Main Team!", ephemeral=True)
                return

            if len(event_cog.events["main_team"]) >= 35:
                await interaction.response.send_message(
                    f"{EMOJIS['ERROR']} Main Team is full (35/35).", ephemeral=True)
                return

            # Remove user from other teams
            for team in event_cog.events:
                if user_ign in event_cog.events[team] and team != "main_team":
                    event_cog.events[team].remove(user_ign)

            event_cog.events["main_team"].append(user_ign)
            event_cog.save_events()

            await interaction.response.send_message(
                f"{EMOJIS['SUCCESS']} {user_ign} joined the Main Team!", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} An error occurred while joining the team.", ephemeral=True)
            print(f"[ERROR] join_main_team: {e}")

    @discord.ui.button(
        label="❌ Leave My Team",
        style=discord.ButtonStyle.danger,
        custom_id="leave_team_btn"
    )
    async def leave_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Allow user to leave their current team."""
        try:
            # Fixed: Changed from "Events" to "EventManager"
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await interaction.response.send_message(
                    f"{EMOJIS['ERROR']} Event system not available.", ephemeral=True)
                return

            user_ign = await self.get_user_ign(interaction)
            if not user_ign:
                return

            left_team = None
            for team, members in event_cog.events.items():
                if user_ign in members:
                    members.remove(user_ign)
                    left_team = team
                    break

            if left_team:
                event_cog.save_events()
                await interaction.response.send_message(
                    f"{EMOJIS['SUCCESS']} {user_ign} has left the **{left_team.replace('_', ' ').title()}**.", 
                    ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"{EMOJIS['INFO']} You're not signed up for any team.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"{EMOJIS['ERROR']} An error occurred while leaving the team.", ephemeral=True)
            print(f"[ERROR] leave_team: {e}")

class ButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(EventButtons(self.bot))  # Register persistent view

async def setup(bot):
    await bot.add_cog(ButtonCog(bot))

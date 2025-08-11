import discord
from discord.ext import commands

from config.constants import MAIN_TEAM_ROLE_ID
from utils.logger import setup_logger

logger = setup_logger("buttons")


class EventButtons(discord.ui.View):
    """
    Persistent view containing buttons for RoW event interactions.

    Features:
    - Team joining buttons with role validation
    - Team leaving functionality
    - Team roster display
    - IGN verification
    - Signup lock handling
    """

    def __init__(self, bot):
        """
        Initialize the event buttons view.

        Args:
            bot: The Discord bot instance
        """
        super().__init__(timeout=None)  # View is now persistent
        self.bot = bot

    async def get_user_ign(self, interaction):
        """
        Helper to get user's IGN from profile system.

        Args:
            interaction: Discord interaction event

        Returns:
            str: User's IGN if set, display name as fallback, or None if IGN required
        """
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            ign = profile_cog.get_ign(interaction.user)
            if not ign:
                await profile_cog.warn_if_no_ign(interaction)
                return None
            return ign
        return interaction.user.display_name

    async def check_signup_permissions(self, interaction, team_key):
        """
        Check if user can join specific team and if signups are open.

        Args:
            interaction: Discord interaction event
            team_key: Team identifier to check permissions for

        Returns:
            tuple: (bool, EventManager) - Success status and event cog instance

        Checks:
            - Event system availability
            - Signup lock status
            - User block status
        """
        # FIXED: Changed from "Events" to "EventManager"
        event_cog = self.bot.get_cog("EventManager")
        if not event_cog or not hasattr(event_cog, 'events'):
            await interaction.response.send_message(
                "❌ Event system not available.", ephemeral=True
            )
            return False, None

        # Check if signups are locked
        if event_cog.is_signup_locked():
            await interaction.response.send_message(
                "🔒 Signups are currently locked! Teams have been finalized for this week.",
                ephemeral=True,
            )
            return False, None

        # Check if user is blocked
        if event_cog.is_user_blocked(interaction.user.id):
            blocked_info = event_cog.blocked_users.get(str(interaction.user.id), {})
            blocked_at = blocked_info.get("blocked_at", "")
            duration = blocked_info.get("ban_duration_days", 0)

            from utils.helpers import Helpers

            days_left = Helpers.days_until_expiry(blocked_at, duration)

            await interaction.response.send_message(
                f"🚫 You are currently blocked from events.\n"
                f"⏰ Time remaining: {days_left} days",
                ephemeral=True,
            )
            return False, None

        return True, event_cog

    @discord.ui.button(
        label="Join Main Team",
        style=discord.ButtonStyle.primary,
        emoji="🏆",
        custom_id="join_main_team_btn",
    )
    async def join_main_team(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle main team join button."""
        try:
            # Check basic permissions
            can_proceed, event_cog = await self.check_signup_permissions(
                interaction, "main_team"
            )
            if not can_proceed:
                return

            # Get user IGN
            user_ign = await self.get_user_ign(interaction)
            if not user_ign:
                return

            # Check Main Team role permission
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ Could not verify guild membership.",
                    ephemeral=True,
                )
                return
                
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                await interaction.response.send_message(
                    "❌ Could not verify your server membership.",
                    ephemeral=True,
                )
                return
                
            user_role_ids = [role.id for role in member.roles]
            logger.debug(
                f"User {interaction.user} role check: {user_role_ids} vs required {MAIN_TEAM_ROLE_ID}"
            )

            if not any(role.id == MAIN_TEAM_ROLE_ID for role in member.roles):
                await interaction.response.send_message(
                    "❌ You don't have permission to join the Main Team.\n"
                    "🏆 The Main Team role is required for this team.",
                    ephemeral=True,
                )
                return

            # Check if already in main team
            if not event_cog or not hasattr(event_cog, 'events'):
                await interaction.response.send_message(
                    "❌ Event system not available.", ephemeral=True
                )
                return

            if user_ign in event_cog.events["main_team"]:
                await interaction.response.send_message(
                    "✅ You're already in the Main Team!", ephemeral=True
                )
                return

            # Check team capacity
            if len(event_cog.events["main_team"]) >= 40:
                await interaction.response.send_message(
                    "❌ Main Team is full (40/40).", ephemeral=True
                )
                return

            # Remove user from other teams first
            removed_from = None
            for team in event_cog.events:
                if user_ign in event_cog.events[team] and team != "main_team":
                    event_cog.events[team].remove(user_ign)
                    removed_from = team
                    break

            # Add to main team
            event_cog.events["main_team"].append(user_ign)
            event_cog.save_events()

            # Log the signup for audit
            try:
                from services.audit_logger import log_signup

                log_signup(
                    interaction.user.id, "main_team", "join", interaction.guild_id
                )
            except ImportError:
                pass  # Audit logging is optional

            # Success message
            message = f"✅ {user_ign} joined the Main Team!"
            if removed_from:
                message += f"\n(Moved from {removed_from.replace('_', ' ').title()})"

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"{interaction.user} ({user_ign}) joined main_team")

        except Exception as e:
            logger.exception(f"Error in join_main_team: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while joining the team.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while joining the team.", ephemeral=True
                )

    @discord.ui.button(
        label="Join Team 2",
        style=discord.ButtonStyle.secondary,
        emoji="🔸",
        custom_id="join_team_2_btn",
    )
    async def join_team_2(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle team 2 join button."""
        try:
            # Check basic permissions
            can_proceed, event_cog = await self.check_signup_permissions(
                interaction, "team_2"
            )
            if not can_proceed:
                return

            # Get user IGN
            user_ign = await self.get_user_ign(interaction)
            if not user_ign:
                return

            # Check if already in team 2
            if not event_cog or not hasattr(event_cog, 'events'):
                await interaction.response.send_message(
                    "❌ Event system not available.", ephemeral=True
                )
                return

            if user_ign in event_cog.events["team_2"]:
                await interaction.response.send_message(
                    "✅ You're already in Team 2!", ephemeral=True
                )
                return

            # Check team capacity
            if len(event_cog.events["team_2"]) >= 40:
                await interaction.response.send_message(
                    "❌ Team 2 is full (40/40).", ephemeral=True
                )
                return

            # Remove user from other teams first
            removed_from = None
            for team in event_cog.events:
                if user_ign in event_cog.events[team] and team != "team_2":
                    event_cog.events[team].remove(user_ign)
                    removed_from = team
                    break

            # Add to team 2
            event_cog.events["team_2"].append(user_ign)
            event_cog.save_events()

            # Log the signup for audit
            try:
                from services.audit_logger import log_signup

                log_signup(interaction.user.id, "team_2", "join", interaction.guild_id)
            except ImportError:
                pass  # Audit logging is optional

            # Success message
            message = f"✅ {user_ign} joined Team 2!"
            if removed_from:
                message += f"\n(Moved from {removed_from.replace('_', ' ').title()})"

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"{interaction.user} ({user_ign}) joined team_2")

        except Exception as e:
            logger.exception(f"Error in join_team_2: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while joining the team.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while joining the team.", ephemeral=True
                )

    @discord.ui.button(
        label="Join Team 3",
        style=discord.ButtonStyle.secondary,
        emoji="🔸",
        custom_id="join_team_3_btn",
    )
    async def join_team_3(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle team 3 join button."""
        try:
            # Check basic permissions
            can_proceed, event_cog = await self.check_signup_permissions(
                interaction, "team_3"
            )
            if not can_proceed:
                return

            # Get user IGN
            user_ign = await self.get_user_ign(interaction)
            if not user_ign:
                return

            # Check if already in team 3
            if not event_cog or not hasattr(event_cog, 'events'):
                await interaction.response.send_message(
                    "❌ Event system not available.", ephemeral=True
                )
                return

            if user_ign in event_cog.events["team_3"]:
                await interaction.response.send_message(
                    "✅ You're already in Team 3!", ephemeral=True
                )
                return

            # Check team capacity
            if len(event_cog.events["team_3"]) >= 40:
                await interaction.response.send_message(
                    "❌ Team 3 is full (40/40).", ephemeral=True
                )
                return

            # Remove user from other teams first
            removed_from = None
            for team in event_cog.events:
                if user_ign in event_cog.events[team] and team != "team_3":
                    event_cog.events[team].remove(user_ign)
                    removed_from = team
                    break

            # Add to team 3
            event_cog.events["team_3"].append(user_ign)
            event_cog.save_events()

            # Log the signup for audit
            try:
                from services.audit_logger import log_signup

                log_signup(interaction.user.id, "team_3", "join", interaction.guild_id)
            except ImportError:
                pass  # Audit logging is optional

            # Success message
            message = f"✅ {user_ign} joined Team 3!"
            if removed_from:
                message += f"\n(Moved from {removed_from.replace('_', ' ').title()})"

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"{interaction.user} ({user_ign}) joined team_3")

        except Exception as e:
            logger.exception(f"Error in join_team_3: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while joining the team.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while joining the team.", ephemeral=True
                )

    @discord.ui.button(
        label="❌ Leave My Team",
        style=discord.ButtonStyle.danger,
        custom_id="leave_team_btn",
    )
    async def leave_team(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Allow user to leave their current team."""
        try:
            # FIXED: Changed from "Events" to "EventManager"
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await interaction.response.send_message(
                    "❌ Event system not available.", ephemeral=True
                )
                return

            # Check if signups are locked
            if event_cog.is_signup_locked():
                await interaction.response.send_message(
                    "🔒 Signups are locked! You cannot leave your team at this time.",
                    ephemeral=True,
                )
                return

            # Get user IGN
            user_ign = await self.get_user_ign(interaction)
            if not user_ign:
                return

            # Find and remove user from their current team
            left_team = None
            for team, members in event_cog.events.items():
                if user_ign in members:
                    members.remove(user_ign)
                    left_team = team
                    break

            if left_team:
                event_cog.save_events()

                # Log the leave action for audit
                try:
                    from services.audit_logger import log_signup

                    log_signup(
                        interaction.user.id, left_team, "leave", interaction.guild_id
                    )
                except ImportError:
                    pass  # Audit logging is optional

                await interaction.response.send_message(
                    f"✅ {user_ign} has left the **{left_team.replace('_', ' ').title()}**.",
                    ephemeral=True,
                )
                logger.info(f"{interaction.user} ({user_ign}) left {left_team}")
            else:
                await interaction.response.send_message(
                    "ℹ️ You're not signed up for any team.", ephemeral=True
                )

        except Exception as e:
            logger.exception(f"Error in leave_team: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while leaving the team.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while leaving the team.", ephemeral=True
                )

    @discord.ui.button(
        label="📋 Show Teams",
        style=discord.ButtonStyle.success,
        emoji="📋",
        custom_id="show_teams_btn",
    )
    async def show_teams(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Show current team signups."""
        try:
            # FIXED: Changed from "Events" to "EventManager"
            event_cog = self.bot.get_cog("EventManager")
            if not event_cog:
                await interaction.response.send_message(
                    "❌ Event system not available.", ephemeral=True
                )
                return

            # Check if user has IGN set (warning)
            profile_cog = self.bot.get_cog("Profile")
            if profile_cog and not profile_cog.has_ign(interaction.user):
                ign_warning = "\n⚠️ You haven't set your IGN yet. Use `!setign YourName` to set it."
            else:
                ign_warning = ""

            from config.constants import COLORS, TEAM_DISPLAY
            from utils.helpers import Helpers

            embed = discord.Embed(
                title="📋 Current RoW Team Signups", color=COLORS["INFO"]
            )

            # Add signup lock status to title if locked
            if event_cog.is_signup_locked():
                embed.title = "📋 Current RoW Team Signups 🔒 [LOCKED]"
                embed.color = COLORS["WARNING"]

            # Add team information
            for team_key in ["main_team", "team_2", "team_3"]:
                members = event_cog.events.get(team_key, [])
                display_name = TEAM_DISPLAY.get(team_key, team_key)
                member_list = Helpers.format_user_list(members)

                embed.add_field(
                    name=f"{display_name} ({len(members)}/40)",
                    value=member_list or "*No signups yet.*",
                    inline=False,
                )

            # Footer with total signups and lock status
            total_signups = sum(len(members) for members in event_cog.events.values())
            footer_text = f"Total signups: {total_signups}"

            if event_cog.is_signup_locked():
                footer_text += " | Signups are locked until next event"

            embed.set_footer(text=footer_text)

            # Send response
            content = (
                f"Here are the current team signups:{ign_warning}"
                if ign_warning
                else None
            )
            await interaction.response.send_message(
                content=content, embed=embed, ephemeral=True
            )

        except Exception as e:
            logger.exception(f"Error in show_teams: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while showing teams.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while showing teams.", ephemeral=True
                )


class ButtonCog(commands.Cog):
    """
    Cog for managing persistent button interactions.

    Handles:
    - Button view registration
    - View persistence across bot restarts
    - Cleanup on unload
    """

    def __init__(self, bot):
        """
        Initialize the button cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot

    async def cog_load(self):
        """
        Register persistent view when cog loads.

        Effects:
            - Adds EventButtons view to bot
            - Ensures buttons persist across restarts
        """
        self.bot.add_view(EventButtons(self.bot))
        logger.info("Event buttons view registered as persistent")

    def cog_unload(self):
        """Clean up resources when cog is unloaded."""
        logger.info("ButtonCog unloaded")


async def setup(bot):
    """
    Set up the ButtonCog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(ButtonCog(bot))


class ButtonHandler(commands.Cog):
    """
    Cog for handling button interactions.

    Listens to button clicks and performs actions like joining/leaving teams.
    """

    def __init__(self, bot):
        """
        Initialize the button handler cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, interaction: discord.Interaction):
        if (interaction.data and 
            interaction.data.get("component_type", 0) == 2 and  # 2 is Button
            "custom_id" in interaction.data and 
            interaction.data["custom_id"].startswith("join_")):
            
            team = interaction.data["custom_id"].split("_")[1]
            event_manager = self.bot.get_cog("EventManager")

            # Add member
            event_manager.events[team].append(interaction.user.display_name)

            # Save with atomic operations
            success = await event_manager.save_events()

            if success:
                await interaction.response.send_message(
                    "✅ Joined team!", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to join team", ephemeral=True
                )

    async def cog_load(self):
        """
        Register the button handler when the cog loads.

        Effects:
            - Activates the on_button_click listener
        """
        logger.info("ButtonHandler cog loaded")

    def cog_unload(self):
        """Clean up resources when cog is unloaded."""
        logger.info("ButtonHandler cog unloaded")

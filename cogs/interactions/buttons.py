                        @discord.ui.button(
                            label="Join Main Team",
                            style=discord.ButtonStyle.primary,
                            emoji="🏆",
                            custom_id="join_main_team_btn"
                        )
                        async def join_main_team(self, interaction: discord.Interaction, button: discord.ui.Button):
                            """Handle main team join button with rate limiting."""
                            try:
                                # Rate limiting check
                                from utils.rate_limiter import check_button_rate_limit
                                allowed, rate_message = check_button_rate_limit(interaction.user.id)

                                if not allowed:
                                    await interaction.response.send_message(
                                        f"⏰ {rate_message}", 
                                        ephemeral=True
                                    )
                                    logger.warning(f"Rate limited button click by {interaction.user.id}: {rate_message}")
                                    return

                                # Get EventManager cog with error handling
                                event_cog = self.bot.get_cog("EventManager")
                                if not event_cog:
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('ERROR', '❌')} Event system not available.", 
                                        ephemeral=True
                                    )
                                    return

                                # Check if user is blocked
                                try:
                                    if event_cog.is_user_blocked(interaction.user.id):
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('BLOCKED', '🚫')} You are currently blocked from events.", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking if user blocked: {e}")

                                # Get user IGN with error handling
                                user_ign = await self.get_user_ign(interaction)
                                if not user_ign:
                                    return  # Error message already sent

                                # Check main team role permission
                                try:
                                    if not any(role.id == MAIN_TEAM_ROLE_ID for role in interaction.user.roles):
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} You don't have permission to join the Main Team.", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking main team role: {e}")

                                # Check if already in main team
                                try:
                                    user_id_str = str(interaction.user.id)
                                    if user_id_str in event_cog.events.get("main_team", []):
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('SUCCESS', '✅')} You're already in the Main Team!", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking team membership: {e}")

                                # Check team capacity
                                try:
                                    if len(event_cog.events.get("main_team", [])) >= MAX_TEAM_SIZE:
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} Main Team is full ({MAX_TEAM_SIZE}/{MAX_TEAM_SIZE}).", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking team capacity: {e}")

                                # Remove user from other teams
                                try:
                                    old_teams = []
                                    for team in event_cog.events:
                                        if user_id_str in event_cog.events[team] and team != "main_team":
                                            event_cog.events[team].remove(user_id_str)
                                            old_teams.append(team)
                                except Exception as e:
                                    logger.warning(f"Error removing from other teams: {e}")

                                # Add to main team
                                try:
                                    if "main_team" not in event_cog.events:
                                        event_cog.events["main_team"] = []
                                    event_cog.events["main_team"].append(user_id_str)

                                    # Save with error handling
                                    if hasattr(event_cog, 'save_events'):
                                        event_cog.save_events()
                                    elif hasattr(event_cog, 'data_manager'):
                                        event_cog.data_manager.save_json(FILES["EVENTS"], event_cog.events)

                                    # Audit logging
                                    try:
                                        from utils.audit_logger import log_signup
                                        log_signup(
                                            user_id=interaction.user.id,
                                            team="main_team",
                                            action="join",
                                            guild_id=interaction.guild.id if interaction.guild else None
                                        )

                                        # Log leaves from old teams
                                        for old_team in old_teams:
                                            log_signup(
                                                user_id=interaction.user.id,
                                                team=old_team,
                                                action="leave",
                                                guild_id=interaction.guild.id if interaction.guild else None
                                            )
                                    except Exception as e:
                                        logger.warning(f"Error logging audit: {e}")

                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('SUCCESS', '✅')} {user_ign} joined the Main Team!", 
                                        ephemeral=True
                                    )
                                    logger.info(f"{interaction.user} ({user_ign}) joined main_team")

                                except Exception as e:
                                    logger.error(f"Error adding to main team: {e}")
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('ERROR', '❌')} Failed to join team. Please try again.", 
                                        ephemeral=True
                                    )

                            except Exception as e:
                                logger.exception(f"Critical error in join_main_team: {e}")
                                try:
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('ERROR', '❌')} An unexpected error occurred.", 
                                        ephemeral=True
                                    )
                                except:
                                    pass  # Don't fail if we can't even send error message

                        async def _join_team(self, interaction: discord.Interaction, team_key: str):
                            """Generic team join handler with rate limiting and audit logging."""
                            try:
                                # Rate limiting check
                                from utils.rate_limiter import check_button_rate_limit
                                allowed, rate_message = check_button_rate_limit(interaction.user.id)

                                if not allowed:
                                    await interaction.response.send_message(
                                        f"⏰ {rate_message}", 
                                        ephemeral=True
                                    )
                                    logger.warning(f"Rate limited button click by {interaction.user.id}: {rate_message}")
                                    return

                                # Get EventManager cog with error handling
                                event_cog = self.bot.get_cog("EventManager")
                                if not event_cog:
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('ERROR', '❌')} Event system not available.", 
                                        ephemeral=True
                                    )
                                    return

                                # Check if user is blocked
                                try:
                                    if event_cog.is_user_blocked(interaction.user.id):
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('BLOCKED', '🚫')} You are currently blocked from events.", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking if user blocked: {e}")

                                # Get user IGN
                                user_ign = await self.get_user_ign(interaction)
                                if not user_ign:
                                    return

                                user_id_str = str(interaction.user.id)

                                # Check if already in this team
                                try:
                                    if user_id_str in event_cog.events.get(team_key, []):
                                        team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('SUCCESS', '✅')} You're already in {team_display}!", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking team membership: {e}")

                                # Check team capacity
                                try:
                                    if len(event_cog.events.get(team_key, [])) >= MAX_TEAM_SIZE:
                                        team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                                        await interaction.response.send_message(
                                            f"{EMOJIS.get('ERROR', '❌')} {team_display} is full ({MAX_TEAM_SIZE}/{MAX_TEAM_SIZE}).", 
                                            ephemeral=True
                                        )
                                        return
                                except Exception as e:
                                    logger.warning(f"Error checking team capacity: {e}")

                                # Remove from other teams and add to selected team
                                try:
                                    old_teams = []
                                    for team in event_cog.events:
                                        if user_id_str in event_cog.events[team] and team != team_key:
                                            event_cog.events[team].remove(user_id_str)
                                            old_teams.append(team)

                                    if team_key not in event_cog.events:
                                        event_cog.events[team_key] = []
                                    event_cog.events[team_key].append(user_id_str)

                                    # Save with error handling
                                    if hasattr(event_cog, 'save_events'):
                                        event_cog.save_events()
                                    elif hasattr(event_cog, 'data_manager'):
                                        event_cog.data_manager.save_json(FILES["EVENTS"], event_cog.events)

                                    # Audit logging
                                    try:
                                        from utils.audit_logger import log_signup
                                        log_signup(
                                            user_id=interaction.user.id,
                                            team=team_key,
                                            action="join",
                                            guild_id=interaction.guild.id if interaction.guild else None
                                        )

                                        # Log leaves from old teams
                                        for old_team in old_teams:
                                            log_signup(
                                                user_id=interaction.user.id,
                                                team=old_team,
                                                action="leave",
                                                guild_id=interaction.guild.id if interaction.guild else None
                                            )
                                    except Exception as e:
                                        logger.warning(f"Error logging audit: {e}")

                                    team_display = TEAM_DISPLAY.get(team_key, team_key.replace('_', ' ').title())
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('SUCCESS', '✅')} {user_ign} joined {team_display}!", 
                                        ephemeral=True
                                    )
                                    logger.info(f"{interaction.user} ({user_ign}) joined {team_key}")

                                except Exception as e:
                                    logger.error(f"Error joining {team_key}: {e}")
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('ERROR', '❌')} Failed to join team. Please try again.", 
                                        ephemeral=True
                                    )

                            except Exception as e:
                                logger.exception(f"Critical error in join {team_key}: {e}")
                                try:
                                    await interaction.response.send_message(
                                        f"{EMOJIS.get('ERROR', '❌')} An unexpected error occurred.", 
                                        ephemeral=True
                                    )
                                except:
                                    pass
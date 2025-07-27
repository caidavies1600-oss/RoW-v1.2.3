# Fixed version for cogs/user/commands.py

@commands.command(name="commands", help="Show available commands.")
async def list_commands(self, ctx):
    """List all available commands dynamically, split by user/admin."""
    is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

    user_cmds = []
    admin_cmds = []

    # Comprehensive list of admin-only command names
    admin_command_names = {
        "startevent", "flagabsent", "clearabsent", "win", "loss",
        "exportteams", "exporthistory", "absencerecord", "rowstats",
        "absent", "present", "absentees", "block", "unblock", "blocklist",
        "backup", "testchannels"
    }

    for command in self.bot.commands:
        if command.hidden or command.name == "commands":
            continue

        if command.name != command.qualified_name:
            continue  # Skip aliases

        name = f"`!{command.name}`"
        desc = command.help or "No description"
        line = f"{name} — {desc}"

        # Check if command is admin-only
        is_admin_cmd = False
        
        # Method 1: Check if command name is in our known admin commands
        if command.name in admin_command_names:
            is_admin_cmd = True
        
        # Method 2: Check if command has role restrictions
        if not is_admin_cmd and hasattr(command, 'checks') and command.checks:
            for check in command.checks:
                # Check for has_any_role decorator
                if hasattr(check, '__name__') and 'has_any_role' in str(check):
                    is_admin_cmd = True
                    break
                
                # Check closure for ADMIN_ROLE_IDS
                if hasattr(check, '__closure__') and check.__closure__:
                    for cell in check.__closure__:
                        if hasattr(cell, 'cell_contents'):
                            cell_content = cell.cell_contents
                            # Check if any admin role ID is in the cell content
                            if isinstance(cell_content, (list, tuple)):
                                if any(role_id in ADMIN_ROLE_IDS for role_id in cell_content if isinstance(role_id, int)):
                                    is_admin_cmd = True
                                    break
                if is_admin_cmd:
                    break

        # Method 3: Check the actual decorator by inspecting the command callback
        if not is_admin_cmd:
            try:
                import inspect
                if hasattr(command, 'callback'):
                    source = inspect.getsource(command.callback)
                    if any(f"@commands.has_any_role(*ADMIN_ROLE_IDS)" in source or 
                           f"commands.has_any_role({role_id}" in source for role_id in ADMIN_ROLE_IDS):
                        is_admin_cmd = True
            except:
                pass  # Ignore if we can't inspect source

        # Categorize the command
        if is_admin_cmd:
            admin_cmds.append(line)
        else:
            user_cmds.append(line)

    # Sort commands alphabetically
    user_cmds.sort()
    admin_cmds.sort()

    embed = discord.Embed(
        title="📜 Available Bot Commands",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="👤 User Commands", 
        value="\n".join(user_cmds) if user_cmds else "None", 
        inline=False
    )

    if is_admin:
        embed.add_field(
            name="🛡️ Admin Commands", 
            value="\n".join(admin_cmds) if admin_cmds else "None", 
            inline=False
        )
    else:
        embed.set_footer(text="Admin commands are only visible if you have the required roles.")

    await ctx.send(embed=embed)
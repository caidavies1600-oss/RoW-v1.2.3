# Simple dynamic version for cogs/user/commands.py

@commands.command(name="commands", help="Show available commands.")
async def list_commands(self, ctx):
    """List all available commands dynamically, split by user/admin."""
    is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

    user_cmds = []
    admin_cmds = []

    for command in self.bot.commands:
        # Skip hidden commands and the commands command itself
        if command.hidden or command.name == "commands":
            continue

        # Skip command aliases (only show the main command)
        if command.name != command.qualified_name:
            continue

        name = f"`!{command.name}`"
        desc = command.help or "No description"
        line = f"{name} — {desc}"

        # Simple dynamic check: does this command have admin role restrictions?
        is_admin_cmd = False
        
        try:
            # Check if command has any role checks
            if hasattr(command, 'checks') and command.checks:
                for check in command.checks:
                    # Convert check function to string and look for admin role IDs
                    check_str = str(check)
                    # Check if any of our admin role IDs appear in the check
                    for role_id in ADMIN_ROLE_IDS:
                        if str(role_id) in check_str:
                            is_admin_cmd = True
                            break
                    if is_admin_cmd:
                        break
            
            # If no checks found, it's a user command (commands without restrictions)
            
        except Exception:
            # If we can't determine, assume it's a user command
            pass

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
        embed.set_footer(text=f"Found {len(user_cmds)} user commands, {len(admin_cmds)} admin commands")
    else:
        embed.set_footer(text="Admin commands are only visible if you have the required roles.")

    await ctx.send(embed=embed)
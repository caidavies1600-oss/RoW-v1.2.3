# Super simple debug version for cogs/user/commands.py

@commands.command(name="commands", help="Show available commands.")
async def list_commands(self, ctx):
    """List all available commands dynamically, split by user/admin."""
    try:
        is_admin = any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

        # Just get all commands first
        all_commands = []
        for command in self.bot.commands:
            if command.name != "commands":  # Skip the commands command itself
                all_commands.append(f"`!{command.name}` — {command.help or 'No description'}")

        # Simple hardcoded split for now (we'll make it dynamic once this works)
        admin_commands = [
            "`!win` — Record a win for a team",
            "`!loss` — Record a loss for a team", 
            "`!block` — Block a user from signing up",
            "`!unblock` — Unblock a user manually",
            "`!blocklist` — List all currently blocked users",
            "`!absent` — Mark player absent from this week's RoW event",
            "`!present` — Remove a user's absence mark",
            "`!absentees` — Show all users marked absent",
            "`!rowstats` — Show comprehensive RoW stats",
            "`!exportteams` — Export current team signups to a text file",
            "`!exporthistory` — Export event history to a text file",
            "`!startevent` — Start a new event",
            "`!backup` — Create a manual backup of all data files",
            "`!testchannels` — Test channel access"
        ]

        user_commands = [
            "`!myign` — View your stored IGN",
            "`!setign` — Set your in-game name", 
            "`!clearign` — Clear your stored IGN",
            "`!showteams` — Show current teams"
        ]

        embed = discord.Embed(
            title="📜 Available Bot Commands",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="👤 User Commands", 
            value="\n".join(user_commands),
            inline=False
        )

        if is_admin:
            embed.add_field(
                name="🛡️ Admin Commands", 
                value="\n".join(admin_commands),
                inline=False
            )
        else:
            embed.set_footer(text="Admin commands are only visible if you have the required roles.")

        # Debug info
        embed.add_field(
            name="🐛 Debug Info",
            value=f"Total bot commands found: {len(list(self.bot.commands))}\nYour admin status: {is_admin}",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error in commands: {str(e)}")
        print(f"Commands error: {e}")
        import traceback
        traceback.print_exc()
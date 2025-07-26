import discord
from discord.ext import commands
from datetime import datetime, timedelta

from utils.logger import setup_logger
from config.constants import ADMIN_ROLE_IDS, FILES, TEAM_DISPLAY, ALERT_CHANNEL_IDS
from config.settings import BOT_ADMIN_USER_ID
from utils.helpers import Helpers
from utils.data_manager import DataManager

logger = setup_logger("admin_actions")

class AdminActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

    def load_results(self):
        """Load results using DataManager."""
        default_results = {
            "total_wins": 0,
            "total_losses": 0,
            "history": []
        }
        return self.data_manager.load_json(FILES["RESULTS"], default_results)

    def load_blocked_users(self):
        """Load blocked users using DataManager."""
        return self.data_manager.load_json(FILES["BLOCKED"], {})

    def save_blocked_users(self, data):
        """Save blocked users using DataManager."""
        success = self.data_manager.save_json(FILES["BLOCKED"], data)
        if not success:
            logger.error("❌ Failed to save blocked users")
        return success

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def block(self, ctx, member: discord.Member, days: int):
        """Block a user from signing up for a number of days."""
        user_id = str(member.id)
        blocked_by = str(ctx.author)
        blocked_at = datetime.utcnow().isoformat()
        duration = max(days, 1)

        data = self.load_blocked_users()
        data[user_id] = {
            "blocked_by": blocked_by,
            "blocked_at": blocked_at,
            "ban_duration_days": duration
        }
        
        if self.save_blocked_users(data):
            await ctx.send(f"✅ {member.mention} has been blocked for `{duration}` day(s).")
            logger.info(f"{ctx.author} blocked {member} for {duration} days")

            try:
                admin = self.bot.get_user(BOT_ADMIN_USER_ID)
                if admin:
                    embed = discord.Embed(
                        title="🚫 User Blocked",
                        description=f"**{member}** has been blocked from RoW signups.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Nickname", value=member.display_name, inline=True)
                    embed.add_field(name="Duration", value=f"{duration} days", inline=True)
                    embed.add_field(name="Blocked By", value=ctx.author.mention, inline=True)
                    await admin.send(embed=embed)
            except Exception as e:
                logger.warning(f"Failed to DM bot admin: {e}")
        else:
            await ctx.send("❌ Failed to save block record. Please try again.")

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def unblock(self, ctx, member: discord.Member):
        """Unblock a user manually."""
        user_id = str(member.id)
        data = self.load_blocked_users()

        if user_id not in data:
            await ctx.send("⚠️ That user is not currently blocked.")
            return

        del data[user_id]
        if self.save_blocked_users(data):
            await ctx.send(f"✅ {member.mention} has been unblocked.")
            logger.info(f"{ctx.author} manually unblocked {member}")

            try:
                admin = self.bot.get_user(BOT_ADMIN_USER_ID)
                if admin:
                    embed = discord.Embed(
                        title="✅ User Unblocked (Manual)",
                        description=f"**{member}** has been manually unblocked.",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Unblocked By", value=ctx.author.mention, inline=True)
                    await admin.send(embed=embed)
            except Exception as e:
                logger.warning(f"Failed to DM bot admin: {e}")

            try:
                for channel_id in ALERT_CHANNEL_IDS:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(f"✅ {member.mention} has been unblocked.")
            except Exception as e:
                logger.warning(f"Failed to send unblock alert: {e}")
        else:
            await ctx.send("❌ Failed to save unblock changes. Please try again.")

    @commands.command(name="blocklist")
    async def blocklist(self, ctx):
        """List all currently blocked users and remaining ban time."""
        data = self.load_blocked_users()
        if not data:
            await ctx.send("✅ No users are currently blocked.")
            return

        lines = []
        for user_id, info in data.items():
            try:
                user = ctx.guild.get_member(int(user_id)) or await self.bot.fetch_user(int(user_id))
                name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{user_id}>"
                
                blocked_at = datetime.fromisoformat(info.get("blocked_at"))
                duration = info.get("ban_duration_days", 0)
                expires_at = blocked_at + timedelta(days=duration)
                remaining = expires_at - datetime.utcnow()
                
                if remaining.total_seconds() > 0:
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    time_left = f"{days}d {hours}h" if days > 0 else f"{hours}h"
                else:
                    time_left = "Expired"
                    
                lines.append(f"{name} - `{time_left}`")
            except Exception as e:
                logger.warning(f"Error processing blocked user {user_id}: {e}")
                lines.append(f"<@{user_id}> - `Error`")

        embed = discord.Embed(
            title=f"🚫 Blocked Users ({len(lines)})",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLE_IDS)
    async def rowstats(self, ctx):
        """Show comprehensive RoW stats."""
        try:
            event_cog = self.bot.get_cog("EventManager")
            profile_cog = self.bot.get_cog("Profile")

            if not event_cog or not profile_cog:
                await ctx.send("❌ Event or profile system not available.")
                return

            results = self.load_results()
            blocked_data = self.load_blocked_users()
            
            wins = results.get("total_wins", 0)
            losses = results.get("total_losses", 0)
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

            embed = discord.Embed(title="📊 RoW Stats Report", color=discord.Color.blurple())

            for team, members in event_cog.events.items():
                igns = []
                for uid in members:
                    try:
                        user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
                        ign = profile_cog.get_ign(user) if user else "Unknown"
                        name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
                        igns.append(f"{name} (`{ign}`)")
                    except Exception as e:
                        logger.warning(f"Error getting user info for {uid}: {e}")
                        igns.append(f"<@{uid}> (`Unknown`)")
                
                team_display = TEAM_DISPLAY.get(team, team.replace("_", " ").title())
                value = "\n".join(igns) if igns else "No members"
                embed.add_field(
                    name=f"{team_display} ({len(igns)} signed up)",
                    value=value,
                    inline=False
                )

            blocked_info = []
            for uid, info in blocked_data.items():
                try:
                    user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
                    name = user.display_name if isinstance(user, discord.Member) else user.name if user else f"<@{uid}>"
                    
                    blocked_at = datetime.fromisoformat(info.get("blocked_at"))
                    duration = info.get("ban_duration_days", 0)
                    expires_at = blocked_at + timedelta(days=duration)
                    remaining = expires_at - datetime.utcnow()
                    
                    if remaining.total_seconds() > 0:
                        days = remaining.days
                        time_left = f"{days}d" if days > 0 else "< 1d"
                    else:
                        time_left = "Expired"
                        
                    blocked_info.append(f"{name} - `{time_left}` remaining")
                except Exception as e:
                    logger.warning(f"Error processing blocked user {uid}: {e}")
                    blocked_info.append(f"<@{uid}> - `Error`")

            embed.add_field(
                name=f"🚫 Blocked Users ({len(blocked_info)})",
                value="\n".join(blocked_info) if blocked_info else "None",
                inline=False
            )

            embed.add_field(
                name="📊 Overall Record",
                value=f"🏆 {wins} Wins | 💔 {losses} Losses\n📈 Win Rate: `{win_rate:.1f}%`",
                inline=False
            )

            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} requested !rowstats")

        except Exception as e:
            logger.exception("Error in !rowstats command:")
            await ctx.send("❌ Failed to generate stats report.")

async def setup(bot):
    await bot.add_cog(AdminActions(bot))
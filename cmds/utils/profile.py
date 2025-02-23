import discord
from discord.ext import commands
import urllib.parse
import config
from datetime import datetime

class ProfileCog(commands.Cog):
    """Enhanced cog for user profile-related commands with improved layout."""

    def __init__(self, bot):
        self.bot = bot

    async def resolve_user(self, ctx, member_input: str = None) -> discord.User:
        """Resolve input to a User or Member object."""
        if member_input is None:
            return ctx.author

        try:
            # Try converting as a Member first (in-server user)
            member = await commands.MemberConverter().convert(ctx, member_input)
            return member
        except commands.MemberNotFound:
            # Fall back to global user fetch if not in server
            try:
                user_id = int(member_input) if member_input.isdigit() else int(member_input.split('#')[-1])
                return await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound):
                raise commands.UserNotFound(member_input)
            except Exception as e:
                raise commands.CommandError(f"Error resolving user: {str(e)}")

    @commands.command(name="profile")
    async def profile(self, ctx, member: str = None):
        """Displays detailed user info with a polished layout."""
        try:
            user = await self.resolve_user(ctx, member)
            is_member = isinstance(user, discord.Member) and ctx.guild is not None

            embed = discord.Embed(
                title=f"👤 Profile: {user.name}#{user.discriminator}",
                description="━━━━━━━━━━━━━━━━━━━━━━━",
                color=user.color if is_member and user.color != discord.Color.default() else discord.Color.(),
                timestamp=datetime.utcnow()
            )

            # Avatar and Banner
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed.set_thumbnail(url=avatar_url)
            if user.banner:
                embed.set_image(url=user.banner.url)

            # User Info
            embed.add_field(
                name="🔍 User Details",
                value=(
                    f"**Username:** {user.name}#{user.discriminator}\n"
                    f"**ID:** `{user.id}`\n"
                    f"**Created:** {user.created_at.strftime('%d/%m/%y')}"
                ),
                inline=True
            )

            # Server Info (if member)
            if is_member:
                embed.add_field(
                    name="🏠 Server Info",
                    value=(
                        f"**Joined:** {user.joined_at.strftime('%d/%m/%y') if user.joined_at else 'N/A'}\n"
                        f"**Top Role:** {user.top_role.mention if user.top_role else 'None'}\n"
                        f"**Roles:** {len([r for r in user.roles if r.name != '@everyone'])}"
                    ),
                    inline=True
                )

            # Status and Activity (if member)
            if is_member:
                status = {
                    discord.Status.online: "🟢 Online",
                    discord.Status.idle: "🌙 Idle",
                    discord.Status.dnd: "🔴 Do Not Disturb",
                    discord.Status.offline: "⚫ Offline"
                }.get(user.status, "⚫ Offline")
                activity = "None"
                if user.activity:
                    if isinstance(user.activity, discord.Game):
                        activity = f"Playing **{user.activity.name}**"
                    elif isinstance(user.activity, discord.Streaming):
                        activity = f"Streaming **{user.activity.name}** ([Watch]({user.activity.url}))"
                    elif isinstance(user.activity, discord.Spotify):
                        activity = f"Listening to **{user.activity.title}** by {', '.join(user.activity.artists)}"
                    elif isinstance(user.activity, discord.Activity):
                        activity = f"{user.activity.type.name.capitalize()} **{user.activity.name}**"
                embed.add_field(
                    name="💡 Status & Activity",
                    value=f"**Status:** {status}\n**Activity:** {activity}",
                    inline=False
                )

            # OSINT Links (updated Twitter to X)
            username = user.name
            google_query = f"{username}#{user.discriminator} discord site:*.edu | site:*.org | site:*.gov -inurl:(signup | login)"
            osint_links = (
                f"[🔍 Google](https://www.google.com/search?q={urllib.parse.quote(google_query)})\n"
                f"[✖️ X](https://x.com/{urllib.parse.quote(username)})\n"  # Updated Twitter to X
                f"[🌐 Reddit](https://www.reddit.com/user/{urllib.parse.quote(username)})\n"
                f"[💻 GitHub](https://github.com/{urllib.parse.quote(username)})\n"
                f"[📸 Instagram](https://www.instagram.com/{urllib.parse.quote(username)})\n"
                f"[💼 LinkedIn](https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(username)})"
            )
            embed.add_field(
                name="🌍 OSINT Links",
                value=osint_links,
                inline=False
            )

            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

        except commands.UserNotFound:
            error_embed = discord.Embed(
                title="❌ User Not Found",
                description="Could not find a user with that name, ID, or mention. Please try again.",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ Error",
                description=f"An unexpected error occurred: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot))

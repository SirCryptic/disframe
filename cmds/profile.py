import discord
from discord.ext import commands
import urllib.parse

class ProfileCog(commands.Cog):
    """Cog for managing user profile-related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile(self, ctx, member: str = None):
        """
        Command to get detailed information about a member or user, including their avatar, OSINT search links, etc.
        If no member is specified, it shows the command author's profile.
        """
        # Default to the command author if no member is mentioned
        if member is None:
            member = ctx.author

        try:
            # Resolve the user as a Member (someone in the server)
            if isinstance(member, str):
                member = await commands.MemberConverter().convert(ctx, member)

            # Gather member-specific data
            username = member.name
            discriminator = member.discriminator
            user_id = member.id

            # OSINT search queries (using Google and other platforms)
            google_query = f"{username}#{discriminator}"
            google_url = f"https://www.google.com/search?q={urllib.parse.quote(google_query)}+discord+social+accounts"
            twitter_url = f"https://twitter.com/{urllib.parse.quote(username)}"
            reddit_url = f"https://www.reddit.com/user/{urllib.parse.quote(username)}"
            github_url = f"https://github.com/{urllib.parse.quote(username)}"

            embed = discord.Embed(
                title=f"{member.name}'s Profile",
                color=discord.Color.blue()
            )

            # Use member's avatar or their default avatar
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)

            # Member information
            embed.add_field(name="Username", value=f"{username}#{discriminator}", inline=True)
            embed.add_field(name="User ID", value=user_id, inline=True)
            embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"), inline=True)
            embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
            embed.add_field(name="Top Role", value=member.top_role.mention if member.top_role else "None", inline=True)

            # Add OSINT search links
            embed.add_field(name="Google Search", value=f"[Search {username} on Google]({google_url})", inline=False)
            embed.add_field(name="Twitter Profile", value=f"[Visit Twitter]({twitter_url})", inline=False)
            embed.add_field(name="Reddit Profile", value=f"[Visit Reddit]({reddit_url})", inline=False)
            embed.add_field(name="GitHub Profile", value=f"[Visit GitHub]({github_url})", inline=False)

            embed.set_footer(text="OSINT powered by Open Sources")

            # Send the profile embed
            await ctx.send(embed=embed)

        except commands.MemberNotFound:
            # Handle users who are not members of the server
            try:
                user = await self.bot.fetch_user(member)  # Fetch the user globally via ID or tag
                username = user.name
                discriminator = user.discriminator
                user_id = user.id

                # OSINT search queries (using Google and other platforms)
                google_query = f"{username}#{discriminator}"
                google_url = f"https://www.google.com/search?q={urllib.parse.quote(username)}"
                twitter_url = f"https://twitter.com/{urllib.parse.quote(username)}"
                reddit_url = f"https://www.reddit.com/user/{urllib.parse.quote(username)}"
                github_url = f"https://github.com/{urllib.parse.quote(username)}"

                embed = discord.Embed(
                    title=f"{user.name}'s Profile",
                    color=discord.Color.blue()
                )

                # Use user's avatar or their default avatar
                avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
                embed.set_thumbnail(url=avatar_url)

                # Global user information
                embed.add_field(name="Username", value=f"{username}#{discriminator}", inline=True)
                embed.add_field(name="User ID", value=user_id, inline=True)
                embed.add_field(name="Account Created", value=user.created_at.strftime("%b %d, %Y"), inline=True)

                # Add OSINT search links
                embed.add_field(name="Google Search", value=f"[Search {username} on Google]({google_url})", inline=False)
                embed.add_field(name="Twitter Profile", value=f"[Visit Twitter]({twitter_url})", inline=False)
                embed.add_field(name="Reddit Profile", value=f"[Visit Reddit]({reddit_url})", inline=False)
                embed.add_field(name="GitHub Profile", value=f"[Visit GitHub]({github_url})", inline=False)

                embed.set_footer(text="OSINT powered by Open Sources")

                # Send the embed
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"Could not find a user with that name or ID. Error: {e}")

        except Exception as e:
            # Handle unexpected errors
            await ctx.send(f"An unexpected error occurred: {e}")


# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))

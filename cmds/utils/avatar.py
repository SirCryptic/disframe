import discord
from discord.ext import commands
import config
from config import BOT_PREFIX
from datetime import datetime

class Avatar(commands.Cog):
    """A cog to fetch and display a user's avatar."""

    def __init__(self, bot):
        self.bot = bot

    def create_embed(self, title, description, color=discord.Color.blue(), image_url=None):
        """Helper method for clean embeds."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed

    @commands.command(name="avatar")
    async def fetch_avatar(self, ctx, target: str = None):
        """Fetch a user's avatar by ID or mention. Usage: <prefix>avatar [@user or ID]"""
        if not target:
            user = ctx.author  # Default to command invoker if no target
        else:
            try:
                # Handle mention (e.g., <@123456789012345678> or <@!123456789012345678>)
                if target.startswith("<@") and target.endswith(">"):
                    user_id = target[2:-1].replace("!", "")  # Strip <@> or <@!> to get ID
                    user = await self.bot.fetch_user(int(user_id))
                # Handle raw ID
                else:
                    user = await self.bot.fetch_user(int(target))
            except ValueError:
                embed = self.create_embed(
                    "❌ Invalid Input",
                    f"Please provide a valid user ID or mention (e.g., `{BOT_PREFIX}avatar @SirCryptic` or `{BOT_PREFIX}avatar 123456789012345678`).",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, delete_after=10)
                return
            except discord.errors.NotFound:
                embed = self.create_embed(
                    "❌ User Not Found",
                    f"No user found with ID or mention '{target}'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, delete_after=10)
                return
            except discord.errors.Forbidden:
                embed = self.create_embed(
                    "❌ Permission Error",
                    "I don’t have permission to fetch that user’s info.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, delete_after=10)
                return

        # Fetch avatar URL (PNG format, 1024 size for clarity)
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

        embed = self.create_embed(
            f"{user.name}'s Avatar",
            f"User: {user.mention} (`{user.id}`)",
            color=discord.Color.blue(),
            image_url=avatar_url
        )
        await ctx.send(embed=embed)

    @fetch_avatar.error
    async def avatar_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            embed = self.create_embed(
                "❌ Error",
                "Something went wrong while fetching the avatar. Try again!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
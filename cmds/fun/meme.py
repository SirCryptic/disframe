import discord
from discord.ext import commands
import aiohttp
import config

class Meme(commands.Cog):
    """Fun meme command."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='meme')
    async def meme(self, ctx):
        """Fetch and display a random meme."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme") as response:
                    if response.status == 200:
                        data = await response.json()
                        embed = discord.Embed(title=data["title"], color=discord.Color.blue())
                        embed.set_image(url=data["url"])
                        embed.set_footer(
                        text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                        icon_url=self.bot.user.avatar.url
            )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Couldn't fetch a meme right now, please try again later.")
        except Exception as e:
            await ctx.send(f"Error: {e}")

async def setup(bot):
    await bot.add_cog(Meme(bot))

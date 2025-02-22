import discord
from discord.ext import commands
import aiohttp
import config
import random
import asyncio

class Meme(commands.Cog):
    """Enhanced meme commands with multiple safe sources and cooldown."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.meme_sources = {
            "meme-api": "https://meme-api.com/gimme",
            "wholesome": "https://meme-api.com/gimme/wholesomememes",
            "clean": "https://meme-api.com/gimme/cleanmemes",
            "dank": "https://meme-api.com/gimme/memes_of_the_dank",
            "aww": "https://meme-api.com/gimme/aww",
            "programmer": "https://meme-api.com/gimme/ProgrammerHumor",
            "coding": "https://meme-api.com/gimme/codingmemes", 
            "nerd": "https://meme-api.com/gimme/geek",
            "puns": "https://meme-api.com/gimme/puns"
        }
        # Config values
        self.bot_name = config.BOT_NAME
        self.bot_version = config.BOT_VERSION
        self.bot_prefix = config.BOT_PREFIX

    def cog_unload(self):
        """Cleanup the aiohttp session when cog is unloaded."""
        asyncio.create_task(self.session.close())

    async def fetch_meme(self, source_url):
        """Fetch a meme from the specified source URL, filtering NSFW."""
        async with self.session.get(source_url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("nsfw", False):
                    return None
                return data
            return None

    def create_meme_embed(self, data, source):
        """Create an embed for displaying the meme."""
        embed = discord.Embed(
            title=data.get("title", "Random Meme"),
            url=data.get("postLink", "https://meme-api.com"),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_image(url=data["url"])
        embed.add_field(name="Source", value=f"{source.capitalize()} ({data.get('subreddit', 'N/A')})", inline=True)
        embed.add_field(name="Author", value=data.get("author", "Unknown"), inline=True)
        embed.set_footer(text=f"{self.bot_name} v{self.bot_version} | Powered by Meme API", icon_url=self.bot.user.avatar.url)
        return embed

    def error_embed(self, message, details=None):
        """Create an embed for error messages."""
        embed = discord.Embed(
            title="❌ Meme Error",
            description=message,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        if details:
            embed.add_field(name="Details", value=str(details)[:1000], inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{self.bot_name} v{self.bot_version}", icon_url=self.bot.user.avatar.url)
        return embed

    def help_embed(self):
        """Create an embed for meme command help."""
        embed = discord.Embed(
            title="🎭 Meme Help",
            description="Fetch safe, fun memes with these commands!",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name=f"`{self.bot_prefix}meme [source]`",
            value="Get a random meme from a safe source (2s cooldown).\n"
                  "**Sources**: `meme-api`, `wholesome`, `clean`, `dank`, `aww`, `programmer`, `coding`, `nerd`, `puns`\n"
                  "**Examples**:\n"
                  f"- `{self.bot_prefix}meme` - Random safe meme\n"
                  f"- `{self.bot_prefix}meme programmer` - Programming meme\n"
                  f"- `{self.bot_prefix}meme clean` - Clean meme",
            inline=False
        )
        embed.add_field(
            name=f"`{self.bot_prefix}memehelp`",
            value="Show this help message.",
            inline=False
        )
        embed.add_field(
            name=f"`{self.bot_prefix}memesources`",
            value="List all available meme sources with descriptions.",
            inline=False
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"{self.bot_name} v{self.bot_version}", icon_url=self.bot.user.avatar.url)
        return embed

    @commands.command(name="meme")
    @commands.cooldown(1, 2, commands.BucketType.user)  # 2-second cooldown per user
    async def meme(self, ctx, source: str = None):
        """Fetch and display a random meme from a safe source.

        Args:
            source: Optional. Choose from: meme-api, wholesome, clean, dank, aww, programmer, coding, nerd, puns. Default: random safe source.
        Examples:
            {prefix}meme          - Random safe meme
            {prefix}meme programmer - Programming meme
            {prefix}meme clean    - Clean meme
        Tip:
            Use `{prefix}memehelp` or `{prefix}memesources` for more info. 2-second cooldown applies.
        """
        available_sources = ", ".join(self.meme_sources.keys())
        if source:
            source = source.lower()
            if source not in self.meme_sources:
                embed = self.error_embed(
                    "Invalid meme source.",
                    f"Try: {available_sources}. Example: `{self.bot_prefix}meme wholesome`"
                )
                error_msg = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await error_msg.delete()
                return
            source_url = self.meme_sources[source]
        else:
            source = random.choice(list(self.meme_sources.keys()))
            source_url = self.meme_sources[source]

        try:
            async with ctx.typing():
                max_attempts = 3
                for _ in range(max_attempts):
                    data = await self.fetch_meme(source_url)
                    if data and data.get("url"):
                        embed = self.create_meme_embed(data, source)
                        await ctx.send(embed=embed)
                        return
                    await asyncio.sleep(1)
                embed = self.error_embed(
                    "Couldn’t fetch a safe meme.",
                    f"All attempts failed. Try: {available_sources} or `{self.bot_prefix}memehelp` for options."
                )
                error_msg = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await error_msg.delete()
        except Exception as e:
            embed = self.error_embed(
                "Failed to fetch meme.",
                f"Error: {str(e)}. Try: {available_sources}"
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()

    @commands.command(name="memehelp")
    async def meme_help(self, ctx):
        """Display help for meme-related commands."""
        embed = self.help_embed()
        await ctx.send(embed=embed)

    @commands.command(name="memesources")
    async def meme_sources(self, ctx):
        """Display available safe meme sources."""
        embed = discord.Embed(
            title="🎭 Safe Meme Sources",
            description=f"Here are the available family-friendly meme sources for `{self.bot_prefix}meme <source>`:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="Sources",
            value="\n".join([f"`{source}` - {self.describe_source(source)}" for source in self.meme_sources.keys()]),
            inline=False
        )
        embed.add_field(
            name="Example",
            value=f"`{self.bot_prefix}meme programmer` - Fetch a programming meme.",
            inline=False
        )
        embed.set_footer(text=f"{self.bot_name} v{self.bot_version}", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    def describe_source(self, source):
        """Provide a brief description of each meme source."""
        descriptions = {
            "meme-api": "General memes (filtered for safety)",
            "wholesome": "Heartwarming and positive memes",
            "clean": "Family-friendly clean memes",
            "dank": "Dank but wholesome memes",
            "aww": "Cute and adorable content",
            "programmer": "Programming-related humor",
            "coding": "Memes for coders",
            "nerd": "Geeky, safe humor",
            "puns": "Pun-based safe memes"
        }
        return descriptions.get(source, "Unknown source")

async def setup(bot):
    await bot.add_cog(Meme(bot))

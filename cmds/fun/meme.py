import discord
from discord.ext import commands
import aiohttp
import config
import json
import os
import random
import asyncio

class Meme(commands.Cog):
    """Enhanced meme commands with channel restrictions, safe sources, and NSFW toggle."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.safe_sources = {
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
        self.nsfw_sources = {
            "memes": "https://meme-api.com/gimme/memes",
            "dankmemes": "https://meme-api.com/gimme/dankmemes",
            "porn": "https://meme-api.com/gimme/porn"
        }
        self.settings_file = "meme_settings.json"
        self.load_settings()

    def cog_unload(self):
        """Cleanup the aiohttp session when cog is unloaded."""
        asyncio.create_task(self.session.close())

    def load_settings(self):
        """Load guild-specific settings from JSON file, fixing old formats."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                try:
                    self.settings = json.load(f)
                    for guild_id, value in list(self.settings.items()):
                        if isinstance(value, bool):
                            self.settings[guild_id] = {"allow_nsfw": value, "allowed_channels": []}
                except json.JSONDecodeError:
                    self.settings = {}
        else:
            self.settings = {}

    def save_settings(self):
        """Save guild-specific settings to JSON file."""
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=4)

    def is_nsfw_allowed(self, guild_id):
        """Check if NSFW is allowed for the given guild, defaulting to False."""
        if guild_id is None:  # DMs
            return False
        guild_settings = self.settings.get(str(guild_id), {})
        return guild_settings.get("allow_nsfw", False)

    def get_allowed_channels(self, guild_id):
        """Get list of allowed channels for the guild, defaulting to empty list."""
        if guild_id is None:  # DMs
            return []
        guild_settings = self.settings.get(str(guild_id), {})
        return guild_settings.get("allowed_channels", [])

    async def fetch_meme(self, source_url, guild_id=None):
        """Fetch a meme from the specified source URL, enforcing safe content in DMs."""
        async with self.session.get(source_url) as response:
            if response.status == 200:
                data = await response.json()
                if "url" not in data or not data["url"]:
                    return None
                if data.get("nsfw", False) and (guild_id is None or not self.is_nsfw_allowed(guild_id)):
                    return None
                return data
            return None

    def get_available_sources(self, guild_id=None):
        """Get available sources based on NSFW setting."""
        if guild_id and self.is_nsfw_allowed(guild_id):
            return {**self.safe_sources, **self.nsfw_sources}
        return self.safe_sources

    def create_meme_embed(self, data, source):
        """Create an embed for displaying the meme."""
        title = data.get("title", "Random Meme")
        guild_id = data.get("guild_id")
        if source == "porn" and guild_id and self.is_nsfw_allowed(guild_id):
            title = "meme porn - Adult meme (NSFW is enabled)"
        
        embed = discord.Embed(
            title=title,
            url=data.get("postLink", "https://meme-api.com"),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_image(url=data["url"])
        embed.add_field(name="Source", value=f"{source.capitalize()} ({data.get('subreddit', 'N/A')})", inline=True)
        embed.add_field(name="Author", value=data.get("author", "Unknown"), inline=True)
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
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
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        return embed

    def help_embed(self, guild_id=None):
        """Create an embed for meme command help, adjusting for NSFW and DMs."""
        is_dm = guild_id is None
        nsfw_enabled = self.is_nsfw_allowed(guild_id)
        embed = discord.Embed(
            title="🎭 Meme Help",
            description="Fetch fun memes with these commands!",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        available_sources = self.get_available_sources(guild_id)
        sources_list = ", ".join(available_sources.keys())
        
        examples = (
            f"- `{config.BOT_PREFIX}meme` - Random meme (safe in DMs)\n"
            f"- `{config.BOT_PREFIX}meme programmer` - Programming meme"
        )
        if nsfw_enabled and not is_dm:
            examples += f"\n- `{config.BOT_PREFIX}meme porn` - Adult meme (NSFW is enabled)"
        
        embed.add_field(
            name=f"`{config.BOT_PREFIX}meme [source]`",
            value=f"Get a random meme (2s cooldown) in allowed channels.\n"
                  f"**Sources**: `{sources_list}`\n"
                  f"**Examples**:\n{examples}\n"
                  f"{'Managers can set channels with `setmemechan` and toggle NSFW with `setnsfw`. ' if not is_dm else ''}DMs are always safe.",
            inline=False
        )
        embed.add_field(
            name=f"`{config.BOT_PREFIX}memehelp`",
            value="Show this help message.",
            inline=False
        )
        embed.add_field(
            name=f"`{config.BOT_PREFIX}memesources`",
            value="List all available meme sources with descriptions.",
            inline=False
        )
        if not is_dm:
            embed.add_field(
                name=f"`{config.BOT_PREFIX}setnsfw <true/false>`",
                value="Managers only: Enable/disable NSFW memes in servers.",
                inline=False
            )
            embed.add_field(
                name=f"`{config.BOT_PREFIX}setmemechan <channel>`",
                value="Managers only: Set a channel where memes can be used.",
                inline=False
            )
            embed.add_field(
                name=f"`{config.BOT_PREFIX}clearmemechan`",
                value="Managers only: Clear allowed meme channels (allows all).",
                inline=False
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION}{' | NSFW Disabled' if not nsfw_enabled else ''}",
                icon_url=self.bot.user.avatar.url
            )
        else:
            embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        return embed

    @commands.command(name="meme")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def meme(self, ctx, source: str = None):
        """Fetch and display a random meme from a source."""
        guild_id = str(ctx.guild.id) if ctx.guild else None
        available_sources = self.get_available_sources(guild_id)
        sources_list = ", ".join(available_sources.keys())

        if ctx.guild:
            allowed_channels = self.get_allowed_channels(guild_id)
            if allowed_channels and str(ctx.channel.id) not in allowed_channels:
                accessible_channels = [
                    f"<#{chan_id}>"
                    for chan_id in allowed_channels
                    if ctx.guild.get_channel(int(chan_id)) and ctx.guild.get_channel(int(chan_id)).permissions_for(ctx.author).read_messages
                ]
                channels_text = ", ".join(accessible_channels) if accessible_channels else "none you can access"
                embed = self.error_embed(
                    "Channel restricted.",
                    f"Memes are only allowed in: {channels_text}. Managers can set with `{config.BOT_PREFIX}setmemechan`."
                )
                error_msg = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await error_msg.delete()
                return

        if source:
            source = source.lower()
            # Check for porn in DMs or guild with NSFW disabled
            if source == "porn":
                if guild_id is None:  # DMs
                    embed = self.error_embed(
                        "😂 Nope!",
                        "NSFW content isn’t available in DMs. Try this in a server with NSFW enabled!"
                    )
                    error_msg = await ctx.send(embed=embed)
                    await asyncio.sleep(5)
                    await error_msg.delete()
                    return
                elif not self.is_nsfw_allowed(guild_id):  # Guild with NSFW off
                    embed = self.error_embed(
                        "😂 Nope!",
                        "NSFW content is disabled in this server. Ask a manager to enable it with `!setnsfw true`."
                    )
                    error_msg = await ctx.send(embed=embed)
                    await asyncio.sleep(5)
                    await error_msg.delete()
                    return
                
            if source not in available_sources:
                embed = self.error_embed(
                    "Invalid meme source.",
                    f"Try: {sources_list}. Example: `{config.BOT_PREFIX}meme wholesome`"
                )
                error_msg = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await error_msg.delete()
                return
            source_url = available_sources[source]
        else:
            source = random.choice(list(available_sources.keys()))
            source_url = available_sources[source]

        try:
            async with ctx.typing():
                max_attempts = 3
                for _ in range(max_attempts):
                    data = await self.fetch_meme(source_url, guild_id)
                    if data and data.get("url"):
                        if guild_id:
                            data["guild_id"] = guild_id
                        embed = self.create_meme_embed(data, source)
                        await ctx.send(embed=embed)
                        return
                    await asyncio.sleep(1)
                embed = self.error_embed(
                    "Couldn’t fetch a meme.",
                    f"API failed after {max_attempts} attempts. Try: {sources_list} or `{config.BOT_PREFIX}memehelp` for options."
                )
                error_msg = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await error_msg.delete()
        except Exception as e:
            embed = self.error_embed(
                "Failed to fetch meme.",
                f"Unexpected error: {str(e)}. Try: {sources_list}"
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()

    @commands.command(name="memehelp")
    async def meme_help(self, ctx):
        """Display help for meme-related commands."""
        guild_id = str(ctx.guild.id) if ctx.guild else None
        embed = self.help_embed(guild_id)
        await ctx.send(embed=embed)

    @commands.command(name="memesources")
    async def meme_sources(self, ctx):
        """Display available meme sources."""
        guild_id = str(ctx.guild.id) if ctx.guild else None
        available_sources = self.get_available_sources(guild_id)
        embed = discord.Embed(
            title="🎭 Meme Sources",
            description=f"Here are the available meme sources for `{config.BOT_PREFIX}meme <source>`:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="Sources",
            value="\n".join([f"`{source}` - {self.describe_source(source)}" for source in available_sources.keys()]),
            inline=False
        )
        embed.add_field(
            name="Example",
            value=f"`{config.BOT_PREFIX}meme programmer` - Fetch a programming meme.",
            inline=False
        )
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="setnsfw")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_nsfw(self, ctx, setting: str = None):
        """Set whether NSFW memes are allowed in this guild (managers only)."""
        if ctx.guild is None:
            embed = self.error_embed(
                "Guild-only command.",
                "NSFW settings can only be changed in a server channel. DMs are always safe."
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()
            return

        if setting is None or setting.lower() not in ["true", "false"]:
            embed = self.error_embed(
                "Invalid setting.",
                f"Use `{config.BOT_PREFIX}setnsfw true` or `{config.BOT_PREFIX}setnsfw false`."
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()
            return

        guild_id = str(ctx.guild.id)
        allow_nsfw = setting.lower() == "true"
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["allow_nsfw"] = allow_nsfw
        self.save_settings()

        embed = discord.Embed(
            title="✅ NSFW Setting Updated",
            description=f"NSFW memes are now **{'allowed' if allow_nsfw else 'disallowed'}** in this guild. DMs remain safe.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="setmemechan")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_meme_channel(self, ctx, channel: discord.TextChannel = None):
        """Set a channel where memes can be used (managers only)."""
        if ctx.guild is None:
            embed = self.error_embed(
                "Guild-only command.",
                "Channel settings can only be changed in a server channel."
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()
            return

        if channel is None:
            embed = self.error_embed(
                "Invalid channel.",
                f"Specify a channel with `{config.BOT_PREFIX}setmemechan #channel-name`."
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        allowed_channels = self.settings[guild_id].get("allowed_channels", [])
        channel_id = str(channel.id)
        if channel_id not in allowed_channels:
            allowed_channels.append(channel_id)
            self.settings[guild_id]["allowed_channels"] = allowed_channels
            self.save_settings()

        embed = discord.Embed(
            title="✅ Meme Channel Set",
            description=f"Memes can now be used in {channel.mention}.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="clearmemechan")
    @commands.has_guild_permissions(manage_guild=True)
    async def clear_meme_channel(self, ctx):
        """Clear allowed meme channels, enabling memes everywhere in the guild (managers only)."""
        if ctx.guild is None:
            embed = self.error_embed(
                "Guild-only command.",
                "Channel settings can only be changed in a server channel."
            )
            error_msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await error_msg.delete()
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        if "allowed_channels" in self.settings[guild_id]:
            del self.settings[guild_id]["allowed_channels"]
            self.save_settings()

        embed = discord.Embed(
            title="✅ Meme Channels Cleared",
            description="Memes can now be used in all channels in this guild.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    def describe_source(self, source):
        """Provide a brief description of each meme source."""
        descriptions = {
            "meme-api": "General memes",
            "wholesome": "Heartwarming and positive memes",
            "clean": "Family-friendly clean memes",
            "dank": "Dank but wholesome memes",
            "aww": "Cute and adorable content",
            "programmer": "Programming-related humor",
            "coding": "Memes for coders",
            "nerd": "Geeky humor",
            "puns": "Pun-based memes",
            "memes": "Popular memes (may include NSFW)",
            "dankmemes": "Dank memes (may include NSFW)",
            "porn": "Adult content (NSFW)"
        }
        return descriptions.get(source, "Unknown source")

async def setup(bot):
    await bot.add_cog(Meme(bot))

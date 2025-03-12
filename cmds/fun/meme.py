import discord
from discord.ext import commands
import praw
import config
import sqlite3
import json
import os
import random
import asyncio

class Meme(commands.Cog):
    """Enhanced meme commands with Reddit scraping, channel restrictions, and NSFW toggle."""

    def __init__(self, bot):
        self.bot = bot
        try:
            self.reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent=config.REDDIT_USER_AGENT
            )
            print("[Meme Cog] Reddit API initialized successfully")
        except Exception:
            self.reddit = None
        self.safe_subreddits = {
            "meme-api": "memes",              # General memes (safe subset)
            "wholesome": "wholesomememes",    # Heartwarming memes
            "clean": "cleanmemes",            # Family-friendly memes
            "dank": "memes_of_the_dank",      # Dank but safe memes
            "aww": "aww",                     # Cute content
            "programmer": "ProgrammerHumor",  # Programming humor
            "coding": "codingmemes",          # Coding memes
            "nerd": "geek",                   # Geeky humor
            "puns": "puns",                   # Pun-based memes
            "funny": "funny",                 # General humor
            "comics": "comics",               # Comic-style memes
            "bonehurtingjuice": "bonehurtingjuice"  # Absurd humor
        }
        self.nsfw_subreddits = {
            "memes": "memes",                 # General memes (may include NSFW)
            "dankmemes": "dankmemes",         # Dank memes (often NSFW)
            "nsfwmemes": "NSFWmemes",         # General NSFW memes
            "porn": "porn",                   # Explicit adult content
            "nsfwfunny": "NSFWFunny",         # NSFW humor
            "adult": "adultmemes"             # Adult-themed memes
        }
        self.fallback_meme = {
            "title": "Fallback Meme",
            "url": "https://i.imgur.com/3XJ2R4K.png",
            "postLink": "https://example.com",
            "subreddit": "fallback",
            "author": "Bot"
        }
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_file = os.path.join(self.data_dir, "meme_settings.db")
        self.setup_database()
        self.settings = self.load_settings()

    def setup_database(self):
        """Create the SQLite database and table if they don't exist."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meme_settings (
                    guild_id TEXT PRIMARY KEY,
                    allow_nsfw INTEGER DEFAULT 0,
                    allowed_channels TEXT DEFAULT '[]'  -- Stored as JSON string
                )
            """)
            conn.commit()

    def load_settings(self):
        """Load guild-specific settings from SQLite, fixing old formats."""
        settings = {}
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT guild_id, allow_nsfw, allowed_channels FROM meme_settings")
            rows = cursor.fetchall()
            for row in rows:
                guild_id, allow_nsfw, allowed_channels_json = row
                settings[guild_id] = {
                    "allow_nsfw": bool(allow_nsfw),
                    "allowed_channels": json.loads(allowed_channels_json)
                }
        return settings

    def save_settings(self):
        """Save guild-specific settings to SQLite."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            for guild_id, data in self.settings.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO meme_settings (
                        guild_id, allow_nsfw, allowed_channels
                    ) VALUES (?, ?, ?)
                """, (
                    guild_id,
                    int(data["allow_nsfw"]),
                    json.dumps(data["allowed_channels"])
                ))
            conn.commit()

    def is_nsfw_allowed(self, guild_id):
        """Check if NSFW is allowed for the given guild, defaulting to False."""
        return False if guild_id is None else self.settings.get(str(guild_id), {}).get("allow_nsfw", False)

    def get_allowed_channels(self, guild_id):
        """Get list of allowed channels for the guild, defaulting to empty list."""
        return [] if guild_id is None else self.settings.get(str(guild_id), {}).get("allowed_channels", [])

    async def fetch_meme(self, subreddit, guild_id=None):
        """Fetch a random meme from a subreddit, enforcing NSFW rules."""
        if not self.reddit:
            return None
        try:
            def get_posts():
                sub = self.reddit.subreddit(subreddit)
                return [post for post in sub.hot(limit=50) if not post.stickied and (
                    post.url.lower().endswith(('.jpg', '.png', '.gif')) or
                    'imgur.com' in post.url.lower() or
                    'gfycat.com' in post.url.lower()
                )]

            posts = await asyncio.to_thread(get_posts)
            if not posts:
                return None
            
            post = random.choice(posts)
            if post.over_18 and (guild_id is None or not self.is_nsfw_allowed(guild_id)):
                return None
            
            data = {
                "title": post.title,
                "url": post.url,
                "postLink": f"https://reddit.com{post.permalink}",
                "subreddit": subreddit,
                "author": post.author.name if post.author else "Anonymous"
            }
            return data
        except Exception:
            return None

    def get_available_sources(self, guild_id=None):
        """Get available subreddits based on NSFW setting."""
        return {**self.safe_subreddits, **self.nsfw_subreddits} if guild_id and self.is_nsfw_allowed(guild_id) else self.safe_subreddits

    def create_meme_embed(self, data, source):
        """Create an embed for displaying the meme."""
        title = data.get("title", "Random Meme")
        guild_id = data.get("guild_id")
        nsfw_status = "NSFW Enabled" if guild_id and self.is_nsfw_allowed(guild_id) else "NSFW Disabled"
        
        embed = discord.Embed(
            title=title[:256],
            url=data.get("postLink", "https://reddit.com"),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_image(url=data["url"])
        embed.add_field(name="Source", value=f"r/{data.get('subreddit', 'N/A')}", inline=True)
        embed.add_field(name="Author", value=data.get("author", "Unknown"), inline=True)
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION} | {nsfw_status}", icon_url=self.bot.user.avatar.url)
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
            description="Fetch fun memes from Reddit with these commands!",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        available_sources = self.get_available_sources(guild_id)
        sources_list = ", ".join(available_sources.keys())
        
        examples = (
            f"- `{config.BOT_PREFIX}meme` - Random safe meme\n"
            f"- `{config.BOT_PREFIX}meme programmer` - Programming meme"
        )
        if nsfw_enabled and not is_dm:
            examples += f"\n- `{config.BOT_PREFIX}meme porn` - Adult meme from r/porn"
        
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
                value="Managers only: Enable/disable NSFW memes.",
                inline=False
            )
            embed.add_field(
                name=f"`{config.BOT_PREFIX}setmemechan <channel>`",
                value="Managers only: Add a channel for meme use.",
                inline=False
            )
            embed.add_field(
                name=f"`{config.BOT_PREFIX}clearmemechan`",
                value="Managers only: Clear allowed channels (all allowed).",
                inline=False
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION}{' | NSFW Disabled' if not nsfw_enabled else ' | NSFW Enabled'}",
                icon_url=self.bot.user.avatar.url
            )
        else:
            embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}", icon_url=self.bot.user.avatar.url)
        return embed

    @commands.command(name="meme")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def meme(self, ctx, source: str = None):
        """Fetch and display a random meme from a subreddit."""
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
                    "Channel restricted",
                    f"Memes are only allowed in: {channels_text}. Managers can set with `{config.BOT_PREFIX}setmemechan`."
                )
                await ctx.send(embed=embed, delete_after=5)
                return

        if source:
            source = source.lower()
            if source in self.nsfw_subreddits and source != "memes" and source != "dankmemes":  # Allow "memes" and "dankmemes" regardless, but restrict explicit NSFW
                if guild_id is None:
                    embed = self.error_embed("NSFW not allowed in DMs", "Try this in a server with NSFW enabled!")
                    await ctx.send(embed=embed, delete_after=5)
                    return
                elif not self.is_nsfw_allowed(guild_id):
                    embed = self.error_embed("NSFW disabled", f"Enable with `{config.BOT_PREFIX}setnsfw true` in this server.")
                    await ctx.send(embed=embed, delete_after=5)
                    return
                
            if source not in available_sources:
                embed = self.error_embed("Invalid source", f"Try: {sources_list}. Example: `{config.BOT_PREFIX}meme wholesome`")
                await ctx.send(embed=embed, delete_after=5)
                return
            selected_sources = [source]
        else:
            selected_sources = list(available_sources.keys())

        async with ctx.typing():
            max_attempts = 3
            for attempt in range(max_attempts):
                source = random.choice(selected_sources)
                subreddit = available_sources[source]
                data = await self.fetch_meme(subreddit, guild_id)
                if data and data.get("url"):
                    if guild_id:
                        data["guild_id"] = guild_id
                    embed = self.create_meme_embed(data, source)
                    await ctx.send(embed=embed)
                    return
                await asyncio.sleep(1)
            
            embed = self.create_meme_embed(self.fallback_meme, "fallback")
            embed.description = "Reddit fetch failed after 3 attempts. Check bot credentials or try again later!"
            await ctx.send(embed=embed)

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
            description=f"Available sources for `{config.BOT_PREFIX}meme <source>`:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="Safe Sources",
            value="\n".join([f"`{source}` - {self.describe_source(source)}" for source in self.safe_subreddits.keys()]),
            inline=False
        )
        if guild_id and self.is_nsfw_allowed(guild_id):
            embed.add_field(
                name="NSFW Sources",
                value="\n".join([f"`{source}` - {self.describe_source(source)}" for source in self.nsfw_subreddits.keys()]),
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
            embed = self.error_embed("Guild-only command", "NSFW settings can only be changed in a server channel.")
            await ctx.send(embed=embed, delete_after=5)
            return

        if setting is None or setting.lower() not in ["true", "false"]:
            embed = self.error_embed("Invalid setting", f"Use `{config.BOT_PREFIX}setnsfw true` or `{config.BOT_PREFIX}setnsfw false`.")
            await ctx.send(embed=embed, delete_after=5)
            return

        guild_id = str(ctx.guild.id)
        allow_nsfw = setting.lower() == "true"
        if guild_id not in self.settings:
            self.settings[guild_id] = {"allow_nsfw": False, "allowed_channels": []}
        self.settings[guild_id]["allow_nsfw"] = allow_nsfw
        self.save_settings()

        embed = discord.Embed(
            title="✅ NSFW Setting Updated",
            description=f"NSFW memes are now **{'allowed' if allow_nsfw else 'disallowed'}** in this guild.",
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
            embed = self.error_embed("Guild-only command", "Channel settings can only be changed in a server channel.")
            await ctx.send(embed=embed, delete_after=5)
            return

        if channel is None:
            embed = self.error_embed("Invalid channel", f"Specify a channel with `{config.BOT_PREFIX}setmemechan #channel-name`.")
            await ctx.send(embed=embed, delete_after=5)
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {"allow_nsfw": False, "allowed_channels": []}
        allowed_channels = self.settings[guild_id]["allowed_channels"]
        channel_id = str(channel.id)
        if channel_id not in allowed_channels:
            allowed_channels.append(channel_id)
            self.settings[guild_id]["allowed_channels"] = allowed_channels
            self.save_settings()

        embed = discord.Embed(
            title="✅ Meme Channel Added",
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
            embed = self.error_embed("Guild-only command", "Channel settings can only be changed in a server channel.")
            await ctx.send(embed=embed, delete_after=5)
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {"allow_nsfw": False, "allowed_channels": []}
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
            # Safe Sources
            "meme-api": "General memes from r/memes (safe subset)",
            "wholesome": "Heartwarming memes from r/wholesomememes",
            "clean": "Family-friendly memes from r/cleanmemes",
            "dank": "Dank wholesome memes from r/memes_of_the_dank",
            "aww": "Cute content from r/aww",
            "programmer": "Programming humor from r/ProgrammerHumor",
            "coding": "Coding memes from r/codingmemes",
            "nerd": "Geeky humor from r/geek",
            "puns": "Pun-based memes from r/puns",
            "funny": "General humor from r/funny",
            "comics": "Comic-style memes from r/comics",
            "bonehurtingjuice": "Absurd humor from r/bonehurtingjuice",
            # NSFW Sources
            "memes": "Popular memes from r/memes (may include NSFW)",
            "dankmemes": "Dank memes from r/dankmemes (may include NSFW)",
            "nsfwmemes": "General NSFW memes from r/NSFWmemes",
            "porn": "Explicit adult content from r/porn",
            "nsfwfunny": "NSFW humor from r/NSFWFunny",
            "adult": "Adult-themed memes from r/adultmemes"
        }
        return descriptions.get(source, "Unknown source")

async def setup(bot):
    await bot.add_cog(Meme(bot))

import discord
from discord.ext import commands
import psutil
from datetime import timedelta
import time
import os
from config import BOT_VERSION, BOT_NAME
import config  # Import your config file

# Uptime logic
start_time = time.time()  # Record the time when the bot starts

def get_uptime():
    """Calculate the bot's uptime."""
    return time.time() - start_time

class Info(commands.Cog):
    """Information related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="info")
    async def info(self, ctx):
        """
        Get detailed information about the bot, including system stats.
        """
        try:
            # Fetch the owner using the ID stored in config.py
            owner = await self.bot.fetch_user(config.OWNER_ID)  # Fetch user based on the stored ID
            
            # System stats
            process = psutil.Process(os.getpid())
            cpu_usage = psutil.cpu_percent(interval=0.5)
            memory_usage = process.memory_info().rss / 1024 ** 2  # Convert bytes to MB
            uptime_seconds = get_uptime()  # Get uptime in seconds
            uptime = str(timedelta(seconds=int(uptime_seconds)))  # Format uptime into HH:MM:SS

            # Fetch all members across all shards and convert to a list
            all_members = list(self.bot.get_all_members())  # Convert generator to list
            total_members = len(all_members)

            # Shard Information (Ensure these are not None before using them)
            shard_count = self.bot.shard_count if self.bot.shard_count is not None else 0
            shard_id = self.bot.shard_id if self.bot.shard_id is not None else "N/A"
            bot_status = "Running" if shard_count > 0 else "Not running"

            # Create the embed for the info command
            embed = discord.Embed(
                title=f"ℹ️ {self.bot.user.name} Info",
                color=discord.Color.blue()
            )
            embed.add_field(name="🖥 Host", value=f"[Raspberry Pi](https://www.raspberrypi.org/)", inline=True)
            embed.add_field(name="📚 Library", value="[discord.py](https://discordpy.readthedocs.io/)", inline=True)
            embed.add_field(name="🐍 Language", value="[Python](https://www.python.org/)", inline=True)
            embed.add_field(name="⏱ Uptime", value=uptime, inline=True)
            embed.add_field(name="💻 CPU Usage", value=f"{cpu_usage}%", inline=True)
            embed.add_field(name="🧠 Memory Usage", value=f"{memory_usage:.2f} MB", inline=True)
            embed.add_field(name="👥 Total Members", value=total_members, inline=True)
            embed.add_field(name="🌍 Server Count", value=len(self.bot.guilds), inline=True)
            embed.add_field(name="🔧 Version", value=BOT_VERSION, inline=True)

            # Add shard information to the embed
            embed.add_field(
                name="🔢 Shard Information",
                value=f"This bot is running {shard_count} shards.\nCurrent shard ID: {shard_id}\nStatus: {bot_status}",
                inline=False
            )

            # Check if the bot has an avatar, else use the default avatar
            avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            embed.set_thumbnail(url=avatar_url)

            # Add footer
            embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )

            # Send the embed
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ An error occurred: {e}")

# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(Info(bot))

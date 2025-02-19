import discord
from discord.ext import commands
import config
from datetime import datetime
import re
import json
import os

class Log(commands.Cog):
    """Now Logs user actions and server events with custom logging channels per guild."""

    def __init__(self, bot):
        self.bot = bot
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.log_channels = self.load_log_channels()

    def load_log_channels(self):
        """Load log channel IDs from JSON file, creating the file if it doesn't exist."""
        if not os.path.exists('log_channels.json'):
            with open('log_channels.json', 'w') as f:
                json.dump({}, f)
        
        with open('log_channels.json', 'r') as f:
            return json.load(f)

    def save_log_channels(self):
        """Save log channel IDs to JSON file."""
        with open('log_channels.json', 'w') as f:
            json.dump(self.log_channels, f, indent=4)

    def get_current_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def contains_url(self, message):
        return self.url_pattern.search(message.content) is not None

    async def get_log_channel(self, guild_id):
        """Fetch the log channel for a guild, or None if not set."""
        channel_id = self.log_channels.get(str(guild_id))
        if channel_id:
            return self.bot.get_channel(int(channel_id))
        return None

    @commands.command(name="setlogchannel")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set or change the logging channel for this server."""
        if channel is None:
            await ctx.send(f"{config.BOT_PREFIX}setlogchannel: Please specify a channel for logging.")
            return
        
        self.log_channels[str(ctx.guild.id)] = str(channel.id)
        self.save_log_channels()
        await ctx.send(f"{config.BOT_PREFIX}setlogchannel: Logging channel has been set to {channel.mention}")

    @commands.command(name="unsetlogchannel")
    @commands.has_permissions(administrator=True)
    async def unset_log_channel(self, ctx):
        """Remove the logging channel setting for this server."""
        if str(ctx.guild.id) in self.log_channels:
            del self.log_channels[str(ctx.guild.id)]
            self.save_log_channels()
            await ctx.send(f"{config.BOT_PREFIX}unsetlogchannel: Logging channel has been unset.")
        else:
            await ctx.send(f"{config.BOT_PREFIX}unsetlogchannel: No logging channel was set for this server.")

    # Event Listeners for Logging

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            
            # Check for timeout changes using roles instead
            timeout_role = discord.utils.get(after.guild.roles, name=config.TIMEOUT_ROLE_NAME)
            if timeout_role:
                if timeout_role not in before.roles and timeout_role in after.roles:
                    embed = discord.Embed(
                        title="🔇 User Muted",
                        description=f"**User:** {after.mention}\n**Time:** {timestamp}",
                        color=discord.Color.red()
                    )
                    await log_channel.send(embed=embed)
                elif timeout_role in before.roles and timeout_role not in after.roles:
                    embed = discord.Embed(
                        title="🔊 User Unmuted",
                        description=f"**User:** {after.mention}\n**Time:** {timestamp}",
                        color=discord.Color.green()
                    )
                    await log_channel.send(embed=embed)

            if before.nick != after.nick:
                embed = discord.Embed(
                    title="✏️ User Nickname Changed",
                    description=f"**User:** {after.mention}\n**Old Nickname:** {before.nick or 'None'}\n**New Nickname:** {after.nick or 'None'}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="👋 User Joined",
                description=f"**User:** {member.mention}\n**Account Created:** {member.created_at}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="👋 User Left",
                description=f"**User:** {member.mention}\n**Joined At:** {member.joined_at}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_channel = await self.get_log_channel(guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"**User:** {user.mention}\n**User ID:** {user.id}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        log_channel = await self.get_log_channel(guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="🔓 User Unbanned",
                description=f"**User:** {user.mention}\n**User ID:** {user.id}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="🆕 Channel Created",
                description=f"**Channel:** #{channel.name}\n**Type:** {channel.type}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="❌ Channel Deleted",
                description=f"**Channel:** #{channel.name}\n**Type:** {channel.type}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if before.channel != after.channel:
                if after.channel:
                    embed = discord.Embed(
                        title="🎤 User Joined Voice Channel",
                        description=f"**User:** {member.mention}\n**Channel:** {after.channel.name}\n**Time:** {timestamp}",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="🎤 User Left Voice Channel",
                        description=f"**User:** {member.mention}\n**Channel:** {before.channel.name}\n**Time:** {timestamp}",
                        color=discord.Color.red()
                    )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_channel = await self.get_log_channel(role.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="📝 Role Created",
                description=f"**Role:** {role.name}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_channel = await self.get_log_channel(role.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="❌ Role Deleted",
                description=f"**Role:** {role.name}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if before.permissions != after.permissions or before.name != after.name:
                changes = []
                if before.name != after.name:
                    changes.append(f"Name: {before.name} → {after.name}")
                if before.permissions != after.permissions:
                    changes.append(f"Permissions Updated")
                embed = discord.Embed(
                    title="⚙️ Role Updated",
                    description=f"**Role:** {after.name}\n**Changes:** {'; '.join(changes)}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return
        log_channel = await self.get_log_channel(message.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if message.attachments:
                file_names = [attachment.filename for attachment in message.attachments]
                embed = discord.Embed(
                    title="📎 File Sent",
                    description=f"**User:** {message.author.mention}\n**Files:** {', '.join(file_names)}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)
            
            if self.contains_url(message):
                urls = self.url_pattern.findall(message.content)
                embed = discord.Embed(
                    title="🔗 URL Sent",
                    description=f"**User:** {message.author.mention}\n**URLs:** {', '.join(urls)}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.guild is None or after.author.bot:
            return
        log_channel = await self.get_log_channel(after.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if before.content != after.content:
                embed = discord.Embed(
                    title="✏️ Message Edited",
                    description=f"**User:** {after.author.mention}\n**Channel:** {after.channel.mention}\n**Old Message:** {before.content[:1000]}\n**New Message:** {after.content[:1000]}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild is None or message.author.bot:
            return
        log_channel = await self.get_log_channel(message.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = discord.Embed(
                title="🗑️ Message Deleted",
                description=f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:1000]}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Log(bot))
import discord
from discord.ext import commands
import os
import json
import asyncio
import config
from config import OWNER_ID, BOT_PREFIX, MOD_ROLE, TIMEOUT_ROLE_NAME
from datetime import datetime, timedelta

class Mod(commands.Cog):
    """Moderation commands such as kick, ban, mute, etc."""

    def __init__(self, bot):
        self.bot = bot
        self.warns_file = "warnings.json"
        if not os.path.exists(self.warns_file):
            with open(self.warns_file, "w") as f:
                json.dump({}, f)

    def load_warns(self, guild_id):
        """Load warnings from the JSON file for a specific guild."""
        with open(self.warns_file, "r") as f:
            data = json.load(f)
        return data.get(str(guild_id), {})

    def save_warns(self, guild_id, warns):
        """Save warnings to the JSON file for a specific guild."""
        with open(self.warns_file, "r+") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
            data[str(guild_id)] = warns
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    async def _check_dm(self, ctx):
        """Check if the command is used in a DM and send an error."""
        if ctx.guild is None:
            embed = discord.Embed(
                title="❌ Cannot Use in DMs",
                description="Moderation commands can only be used in a server.",
                color=discord.Color.red()
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed, delete_after=10)
            return False
        return True

    async def _send_error_message(self, ctx, message, details=None):
        """Send error messages with optional details, lasting longer."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        if details:
            embed.add_field(name="Details", value=str(details), inline=False)
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        error_message = await ctx.send(embed=embed)
        await asyncio.sleep(10)  # Increased from 5s to 10s for readability
        try:
            await ctx.message.delete()
            await error_message.delete()
        except discord.errors.Forbidden:
            pass

    async def ensure_timeout_role(self, guild):
        """Ensure the timeout role exists with proper permissions."""
        timeout_role = discord.utils.get(guild.roles, name=TIMEOUT_ROLE_NAME)
        if not timeout_role:
            try:
                timeout_role = await guild.create_role(
                    name=TIMEOUT_ROLE_NAME,
                    colour=discord.Colour.dark_grey(),
                    permissions=discord.Permissions.none(),
                    reason="Created for mute functionality"
                )
                # Apply role to channels to deny speaking permissions
                for channel in guild.text_channels:
                    await channel.set_permissions(timeout_role, send_messages=False, add_reactions=False)
                for channel in guild.voice_channels:
                    await channel.set_permissions(timeout_role, speak=False, connect=False)
                print(f"Created and configured timeout role '{TIMEOUT_ROLE_NAME}' in guild {guild.name}")
            except discord.errors.Forbidden:
                print(f"Failed to create timeout role in guild {guild.name}. Insufficient permissions.")
                return None
        return timeout_role

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kick a member from the server."""
        if not await self._check_dm(ctx):
            return

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="✋ Member Kicked",
                description=f"{member.mention} (`{member.id}`) has been kicked.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")  # Moderation icon
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="✋ Kicked",
                description=f"You were kicked from **{ctx.guild.name}**.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to kick {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to kick {member.mention}.", str(e))

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        if not await self._check_dm(ctx):
            return

        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="⛔ Member Banned",
                description=f"{member.mention} (`{member.id}`) has been banned.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="⛔ Banned",
                description=f"You were banned from **{ctx.guild.name}**.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to ban {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to ban {member.mention}.", str(e))

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str, *, reason: str = None):
        """Unban a user by ID from the server."""
        if not await self._check_dm(ctx):
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user, reason=reason)
            embed = discord.Embed(
                title="🔓 User Unbanned",
                description=f"{user.mention} (`{user.id}`) has been unbanned.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="🔓 Unbanned",
                description=f"You have been unbanned from **{ctx.guild.name}**.",
                color=discord.Color.green()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
            try:
                await user.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {user.name}")

        except ValueError:
            await self._send_error_message(ctx, "Invalid user ID. Please provide a numeric ID.")
        except discord.errors.NotFound:
            await self._send_error_message(ctx, f"No banned user found with ID {user_id}.")
        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to unban user ID {user_id}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to unban user ID {user_id}.", str(e))

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Clear a specified number of messages from the channel."""
        if not await self._check_dm(ctx):
            return

        try:
            if amount <= 0:
                await self._send_error_message(ctx, "Amount must be greater than 0.")
                return
            if amount > 100:
                await self._send_error_message(ctx, "Cannot delete more than 100 messages at once.")
                return

            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 includes command message
            embed = discord.Embed(
                title="🧹 Messages Cleared",
                description=f"Cleared {len(deleted) - 1} messages from {ctx.channel.mention}.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed, delete_after=10)

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, "I lack permission to clear messages.")
        except Exception as e:
            await self._send_error_message(ctx, "Failed to clear messages.", str(e))

    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: int = None, *, reason: str = None):
        """Mute a member for a specified duration (in minutes) or indefinitely."""
        if not await self._check_dm(ctx):
            return

        try:
            mute_role = await self.ensure_timeout_role(ctx.guild)
            if not mute_role:
                raise Exception("Failed to ensure or create the mute role.")

            if mute_role in member.roles:
                await self._send_error_message(ctx, f"{member.mention} is already muted.")
                return

            await member.add_roles(mute_role, reason=reason)
            embed = discord.Embed(
                title="🤐 Member Muted",
                description=f"{member.mention} (`{member.id}`) has been muted.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
            embed.add_field(name="Duration", value=f"{duration} minutes" if duration else "Indefinite", inline=True)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="🤐 Muted",
                description=f"You were muted in **{ctx.guild.name}**.",
                color=discord.Color.orange()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
            dm_embed.add_field(name="Duration", value=f"{duration} minutes" if duration else "Indefinite", inline=False)
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

            if duration:
                await asyncio.sleep(duration * 60)
                if mute_role in member.roles:
                    await member.remove_roles(mute_role)
                    unmute_embed = discord.Embed(
                        title="🗣️ Mute Expired",
                        description=f"{member.mention} (`{member.id}`) has been unmuted after {duration} minutes.",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    await ctx.send(embed=unmute_embed)

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to mute {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to mute {member.mention}.", str(e))

    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member in the server."""
        if not await self._check_dm(ctx):
            return

        try:
            mute_role = discord.utils.get(ctx.guild.roles, name=TIMEOUT_ROLE_NAME)
            if not mute_role in member.roles:
                await self._send_error_message(ctx, f"{member.mention} is not muted.")
                return

            await member.remove_roles(mute_role)
            embed = discord.Embed(
                title="🗣️ Member Unmuted",
                description=f"{member.mention} (`{member.id}`) has been unmuted.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="🗣️ Unmuted",
                description=f"You have been unmuted in **{ctx.guild.name}**.",
                color=discord.Color.green()
            )
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to unmute {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to unmute {member.mention}.", str(e))

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member for inappropriate behavior."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            warns = self.load_warns(guild_id)
            max_warns = 5  # Configurable threshold

            if str(member.id) not in warns:
                warns[str(member.id)] = []

            warns[str(member.id)].append({
                "reason": reason or "No reason provided",
                "timestamp": datetime.utcnow().isoformat(),
                "moderator": str(ctx.author)
            })

            warn_count = len(warns[str(member.id)])
            if warn_count >= max_warns:
                await member.ban(reason=f"Auto-ban after {max_warns} warnings. Last reason: {reason}")
                embed = discord.Embed(
                    title="⛔ Member Auto-Banned",
                    description=f"{member.mention} (`{member.id}`) banned after {max_warns} warnings.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Last Reason", value=reason or "No reason provided", inline=True)
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

                dm_embed = discord.Embed(
                    title="⛔ Auto-Banned",
                    description=f"You were banned from **{ctx.guild.name}** after {max_warns} warnings.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="Last Reason", value=reason or "No reason provided", inline=False)
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"Could not send DM to {member.name}")
            else:
                self.save_warns(guild_id, warns)
                embed = discord.Embed(
                    title="⚠️ Member Warned",
                    description=f"{member.mention} (`{member.id}`) has been warned.",
                    color=discord.Color.yellow(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
                embed.add_field(name="Warn Count", value=f"{warn_count}/{max_warns}", inline=True)
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

                dm_embed = discord.Embed(
                    title="⚠️ Warned",
                    description=f"You were warned in **{ctx.guild.name}**.",
                    color=discord.Color.yellow()
                )
                dm_embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
                dm_embed.add_field(name="Warn Count", value=f"{warn_count}/{max_warns}", inline=False)
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"Could not send DM to {member.name}")

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to warn/ban {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to warn {member.mention}.", str(e))

    @commands.command(name="warnings")
    async def warnings(self, ctx, member: discord.Member):
        """Display a member’s warnings with details."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            warns = self.load_warns(guild_id)

            if str(member.id) in warns and warns[str(member.id)]:
                embed = discord.Embed(
                    title=f"📜 Warnings for {member}",
                    description=f"{member.mention} (`{member.id}`) has {len(warns[str(member.id)])} warnings.",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                for i, warn in enumerate(warns[str(member.id)], 1):
                    embed.add_field(
                        name=f"Warn {i}",
                        value=f"**Reason:** {warn['reason']}\n**Date:** {warn['timestamp'][:10]}\n**Moderator:** {warn['moderator']}",
                        inline=False
                    )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            else:
                embed = discord.Embed(
                    title="📜 No Warnings",
                    description=f"{member.mention} (`{member.id}`) has no warnings.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

        except Exception as e:
            await self._send_error_message(ctx, f"Failed to retrieve warnings for {member.mention}.", str(e))

    @commands.command(name="clearwarnings")
    @commands.has_permissions(kick_members=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            warns = self.load_warns(guild_id)

            if str(member.id) in warns and warns[str(member.id)]:
                del warns[str(member.id)]
                self.save_warns(guild_id, warns)
                embed = discord.Embed(
                    title="🧹 Warnings Cleared",
                    description=f"All warnings for {member.mention} (`{member.id}`) have been cleared.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

                dm_embed = discord.Embed(
                    title="✅ Warnings Cleared",
                    description=f"All your warnings in **{ctx.guild.name}** have been cleared.",
                    color=discord.Color.green()
                )
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"Could not send DM to {member.name}")
            else:
                embed = discord.Embed(
                    title="🧹 No Warnings to Clear",
                    description=f"{member.mention} (`{member.id}`) has no warnings.",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to manage warnings for {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to clear warnings for {member.mention}.", str(e))

    @commands.group(name='modhelp', invoke_without_command=True)
    async def mod_help_group(self, ctx):
        """Display help for moderation commands."""
        if not await self._check_dm(ctx):
            return

        try:
            mod_role = discord.utils.get(ctx.guild.roles, name=MOD_ROLE)
            if mod_role not in ctx.author.roles and ctx.author.id != OWNER_ID:
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description=f"You need the `{MOD_ROLE}` role to use moderation commands.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(
                    text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                    icon_url=self.bot.user.avatar.url
                )
                appeal_message = await ctx.send(embed=embed)
                await asyncio.sleep(10)
                await appeal_message.delete()
                return

            help_embed = discord.Embed(
                title="🛡️ Moderation Commands",
                description=f"Commands for managing {ctx.guild.name}:",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            help_embed.add_field(name=f"✋ {BOT_PREFIX}kick <member> [reason]", value="Kick a member.", inline=False)
            help_embed.add_field(name=f"⛔ {BOT_PREFIX}ban <member> [reason]", value="Ban a member.", inline=False)
            help_embed.add_field(name=f"🔓 {BOT_PREFIX}unban <user_id> [reason]", value="Unban a user by ID.", inline=False)
            help_embed.add_field(name=f"🧹 {BOT_PREFIX}clear <amount>", value="Clear messages (max 100).", inline=False)
            help_embed.add_field(name=f"🤐 {BOT_PREFIX}mute <member> [minutes] [reason]", value="Mute a member (optional duration).", inline=False)
            help_embed.add_field(name=f"🗣️ {BOT_PREFIX}unmute <member>", value="Unmute a member.", inline=False)
            help_embed.add_field(name=f"⚠️ {BOT_PREFIX}warn <member> [reason]", value="Warn a member (auto-ban at 5).", inline=False)
            help_embed.add_field(name=f"📜 {BOT_PREFIX}warnings <member>", value="View a member’s warnings.", inline=False)
            help_embed.add_field(name=f"🧹⚠️ {BOT_PREFIX}clearwarnings <member>", value="Clear a member’s warnings.", inline=False)
            help_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            help_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=help_embed)

        except Exception as e:
            await self._send_error_message(ctx, "Failed to display moderation help.", str(e))

async def setup(bot):
    await bot.add_cog(Mod(bot))

import discord
from discord.ext import commands
import os
import json
import asyncio
import config
from config import OWNER_ID, BOT_PREFIX, MOD_ROLE, TIMEOUT_ROLE_NAME
import traceback

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
        """Check if the command is used in a DM and send an appropriate message."""
        if ctx.guild is None:
            dm_error_embed = discord.Embed(
                title="Error",
                description="Unable to use moderation commands in DMs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=dm_error_embed)
            return False
        return True

    async def _send_error_message(self, ctx, message, details=None):
        """Helper method to send error messages with optional details."""
        error_embed = discord.Embed(
            title="Error",
            description=message,
            color=discord.Color.red()
        )
        if details:
            error_embed.add_field(name="Details", value=str(details), inline=False)
        error_message = await ctx.send(embed=error_embed)
        await asyncio.sleep(5)
        await ctx.message.delete()
        await error_message.delete()

    async def ensure_timeout_role(self, guild):
        """Ensure the timeout role exists in the guild."""
        timeout_role = discord.utils.get(guild.roles, name=TIMEOUT_ROLE_NAME)
        if not timeout_role:
            try:
                # Creating a role with minimal permissions for timeout
                timeout_role = await guild.create_role(
                    name=TIMEOUT_ROLE_NAME, 
                    colour=discord.Colour.dark_grey(), 
                    permissions=discord.Permissions.none()
                )
                print(f"Created timeout role '{TIMEOUT_ROLE_NAME}' in guild {guild.name}")
            except discord.errors.Forbidden:
                print(f"Failed to create timeout role in guild {guild.name}. Insufficient permissions.")
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
                title="Member Kicked",
                description=f"{member} has been kicked from the server.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="🔄 Kicked",
                description=f"You have been kicked from **{ctx.guild.name}**.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided.")
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while trying to kick {member}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        if not await self._check_dm(ctx):
            return

        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member} has been banned from the server.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="⛔ Banned",
                description=f"You have been banned from **{ctx.guild.name}**.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided.")
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while trying to ban {member}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str = None):
        """Unban a member from the server."""
        if not await self._check_dm(ctx):
            return

        try:
            await ctx.guild.unban(user, reason=reason)
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"{user} has been unbanned from the server.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="🔓 Unbanned",
                description=f"You have been unbanned from **{ctx.guild.name}**.",
                color=discord.Color.green()
            )
            try:
                await user.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {user.name}")

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while trying to unban {user}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Clear a specified number of messages from the channel."""
        if not await self._check_dm(ctx):
            return

        try:
            if amount <= 0:
                await self._send_error_message(ctx, "You must specify a number greater than 0.")
                return

            await ctx.channel.purge(limit=amount)
            embed = discord.Embed(
                title="Messages Cleared",
                description=f"Successfully cleared {amount} messages.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed, delete_after=5)

        except Exception as e:
            await self._send_error_message(ctx, "An error occurred while trying to clear messages.", str(e))
            print(traceback.format_exc())

    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = None):
        """Mute a member in the server."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            # Ensure the timeout role exists
            mute_role = await self.ensure_timeout_role(ctx.guild)
            
            if not mute_role:
                raise Exception("Failed to ensure or create the mute role.")

            if mute_role in member.roles:
                await ctx.send(f"{member} is already muted.")
                return

            await member.add_roles(mute_role, reason=reason)
            
            embed = discord.Embed(
                title="Member Muted",
                description=f"{member} has been muted.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            dm_embed = discord.Embed(
                title="🤐 Muted",
                description=f"You have been muted in **{ctx.guild.name}**.",
                color=discord.Color.orange()
            )
            dm_embed.add_field(name="Reason", value=reason or "No reason provided.")
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}")

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while trying to mute {member}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member in the server."""
        if not await self._check_dm(ctx):
            return

        try:
            mute_role = discord.utils.get(ctx.guild.roles, name=TIMEOUT_ROLE_NAME)
            
            if mute_role not in member.roles:
                await ctx.send(f"{member} is not muted.")
                return

            await member.remove_roles(mute_role)
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"{member} has been unmuted.",
                color=discord.Color.green()
            )
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

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while trying to unmute {member}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member for inappropriate behavior."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            warns = self.load_warns(guild_id)

            if str(member.id) not in warns:
                warns[str(member.id)] = []

            warns[str(member.id)].append(reason or "No reason provided")

            if len(warns[str(member.id)]) >= 5:
                await member.ban(reason=f"Auto-ban after 5 warnings. Reason: {reason}")
                embed = discord.Embed(
                    title="Member Banned",
                    description=f"{member} has been automatically banned after receiving 5 warnings.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value=reason or "No reason provided.")
                await ctx.send(embed=embed)

                dm_embed = discord.Embed(
                    title="⚠️ Auto-Banned",
                    description=f"You have been banned from **{ctx.guild.name}** after receiving 5 warnings.",
                    color=discord.Color.red()
                )
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"Could not send DM to {member.name}")
            else:
                self.save_warns(guild_id, warns)

                embed = discord.Embed(
                    title="Member Warned",
                    description=f"{member} has been warned.",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Reason", value=reason or "No reason provided.")
                embed.add_field(name="Total Warnings", value=len(warns[str(member.id)]))
                await ctx.send(embed=embed)

                dm_embed = discord.Embed(
                    title="⚠️ Warned",
                    description=f"You have been warned in **{ctx.guild.name}**.",
                    color=discord.Color.yellow()
                )
                dm_embed.add_field(name="Reason", value=reason or "No reason provided.")
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"Could not send DM to {member.name}")

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while trying to warn {member}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="warnings")
    async def warnings(self, ctx, member: discord.Member):
        """Display the number of warnings a member has."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            warns = self.load_warns(guild_id)

            if str(member.id) in warns:
                embed = discord.Embed(
                    title=f"Warnings for {member}",
                    description=f"{member} has {len(warns[str(member.id)])} warnings.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Warnings", value="\n".join(warns[str(member.id)]))
            else:
                embed = discord.Embed(
                    title="No Warnings",
                    description=f"{member} has no warnings.",
                    color=discord.Color.green()
                )
            await ctx.send(embed=embed)

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while retrieving warnings for {member}.", str(e))
            print(traceback.format_exc())

    @commands.command(name="clearwarnings")
    @commands.has_permissions(kick_members=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            warns = self.load_warns(guild_id)

            if str(member.id) in warns:
                del warns[str(member.id)]
                self.save_warns(guild_id, warns)
                embed = discord.Embed(
                    title="Warnings Cleared",
                    description=f"All warnings for {member} have been cleared.",
                    color=discord.Color.green()
                )

                dm_embed = discord.Embed(
                    title="✅ Warnings Cleared",
                    description=f"All of your warnings have been cleared in **{ctx.guild.name}**.",
                    color=discord.Color.green()
                )
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"Could not send DM to {member.name}")
            else:
                embed = discord.Embed(
                    title="No Warnings",
                    description=f"{member} has no warnings to clear.",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)

        except Exception as e:
            await self._send_error_message(ctx, f"An error occurred while clearing warnings for {member}.", str(e))
            print(traceback.format_exc())

    @commands.group(name='modhelp', invoke_without_command=True)
    async def mod_help_group(self, ctx):
        """Display help for moderation commands."""
        if not await self._check_dm(ctx):
            return

        try:
            mod_role = discord.utils.get(ctx.guild.roles, name=MOD_ROLE)
            if mod_role not in ctx.author.roles:  
                appeal_message = await ctx.send(
                    f"{BOT_PREFIX}modhelp: You need the ```{MOD_ROLE}``` role to access the moderation commands."
                )
                await asyncio.sleep(5)  
                await appeal_message.delete() 
                return

            help_embed = discord.Embed(
                title="Moderation Commands",
                description="Here are the available commands for moderation:",
                color=discord.Color.blue()
            )
            help_embed.add_field(name="✋ " + f"{BOT_PREFIX}kick <member>", value="Kick a member from the server.", inline=False)
            help_embed.add_field(name="⛔ " + f"{BOT_PREFIX}ban <member>", value="Ban a member from the server.", inline=False)
            help_embed.add_field(name="🔓 " + f"{BOT_PREFIX}unban <user>", value="Unban a member from the server.", inline=False)
            help_embed.add_field(name="🧹 " + f"{BOT_PREFIX}clear <amount>", value="Clear a specified number of messages.", inline=False)
            help_embed.add_field(name="🤐 " + f"{BOT_PREFIX}mute <member>", value="Mute a member in the server.", inline=False)
            help_embed.add_field(name="🗣️ " + f"{BOT_PREFIX}unmute <member>", value="Unmute a member in the server.", inline=False)
            help_embed.add_field(name="⚠️ " + f"{BOT_PREFIX}warn <member>", value="Warn a member for inappropriate behavior.", inline=False)
            help_embed.add_field(name="📜 " + f"{BOT_PREFIX}warnings <member>", value="View the warnings of a member.", inline=False)
            help_embed.add_field(name="🧹⚠️ " + f"{BOT_PREFIX}clearwarnings <member>", value="Clear all warnings for a member.", inline=False)
            help_embed.set_footer(
                            text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                            icon_url=self.bot.user.avatar.url
                )
            await ctx.send(embed=help_embed)

        except Exception as e:
            await self._send_error_message(ctx, "An error occurred while displaying help.", str(e))
            print(traceback.format_exc())

async def setup(bot):
    await bot.add_cog(Mod(bot))
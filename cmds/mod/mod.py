import discord
from discord.ext import commands
import os
import json
import asyncio
from config import OWNER_ID, BOT_PREFIX, MOD_ROLE

class Mod(commands.Cog):
    """Moderation commands such as kick, ban, mute, etc."""

    def __init__(self, bot):
        self.bot = bot
        self.warns_file = "warnings.json"
        if not os.path.exists(self.warns_file):
            with open(self.warns_file, "w") as f:
                json.dump({}, f)

    def load_warns(self):
        """Load warnings from the JSON file."""
        with open(self.warns_file, "r") as f:
            return json.load(f)

    def save_warns(self, warns):
        """Save warnings to the JSON file."""
        with open(self.warns_file, "w") as f:
            json.dump(warns, f, indent=4)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kick a member from the server."""
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member} has been kicked from the server.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            # Send a DM to the kicked member
            try:
                await member.send(f"You have been kicked from {ctx.guild.name}. Reason: {reason or 'No reason provided.'}")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while trying to kick {member}.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Details", value=str(e))
            error_message = await ctx.send(embed=error_embed)
            await asyncio.sleep(5)
            await ctx.message.delete()
            await error_message.delete()

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member} has been banned from the server.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            # Send a DM to the banned member
            try:
                await member.send(f"You have been banned from {ctx.guild.name}. Reason: {reason or 'No reason provided.'}")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while trying to ban {member}.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Details", value=str(e))
            error_message = await ctx.send(embed=error_embed)
            await asyncio.sleep(5)
            await ctx.message.delete()
            await error_message.delete()

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str = None):
        """Unban a member from the server."""
        try:
            await ctx.guild.unban(user, reason=reason)
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"{user} has been unbanned from the server.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            # Send a DM to the unbanned member
            try:
                await user.send(f"You have been unbanned from {ctx.guild.name}.")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while trying to unban {user}.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Details", value=str(e))
            error_message = await ctx.send(embed=error_embed)
            await asyncio.sleep(5)
            await ctx.message.delete()
            await error_message.delete()

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Clear a specified number of messages from the channel."""
        if amount <= 0:
            error_embed = discord.Embed(
                title="Error",
                description="You must specify a number greater than 0.",
                color=discord.Color.red()
            )
            error_message = await ctx.send(embed=error_embed)
            await asyncio.sleep(5)
            await ctx.message.delete()
            await error_message.delete()
            return

        await ctx.channel.purge(limit=amount)
        embed = discord.Embed(
            title="Messages Cleared",
            description=f"Successfully cleared {amount} messages.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = None):
        """Mute a member in the server."""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
            for channel in ctx.guild.text_channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)

        # Check if the member is already muted
        if mute_role in member.roles:
            await ctx.send(f"{member} is already muted.")
            return

        try:
            await member.add_roles(mute_role, reason=reason)
            
            embed = discord.Embed(
                title="Member Muted",
                description=f"{member} has been muted.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            # Send a DM to the muted member
            try:
                await member.send(f"You have been muted in {ctx.guild.name}. Reason: {reason or 'No reason provided.'}")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while trying to mute {member}.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Details", value=str(e))
            error_message = await ctx.send(embed=error_embed)
            await asyncio.sleep(5)
            await ctx.message.delete()
            await error_message.delete()

    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member in the server."""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        
        if mute_role not in member.roles:
            await ctx.send(f"{member} is not muted.")
            return

        try:
            await member.remove_roles(mute_role)
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"{member} has been unmuted.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # Send a DM to the unmuted member
            try:
                await member.send(f"You have been unmuted in {ctx.guild.name}.")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while trying to unmute {member}.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Details", value=str(e))
            error_message = await ctx.send(embed=error_embed)
            await asyncio.sleep(5)
            await ctx.message.delete()
            await error_message.delete()

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member for inappropriate behavior."""
        warns = self.load_warns()

        # If the member doesn't have a record yet, initialize their list
        if str(member.id) not in warns:
            warns[str(member.id)] = []

        # Add a new warning
        warns[str(member.id)].append(reason or "No reason provided")

        # Check if the member has reached 5 warnings
        if len(warns[str(member.id)]) >= 5:
            await member.ban(reason=f"Auto-ban after 5 warnings. Reason: {reason}")
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member} has been automatically banned after receiving 5 warnings.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            await ctx.send(embed=embed)

            # Send a DM to the banned member
            try:
                await member.send(f"You have been banned from {ctx.guild.name}. Reason: Auto-ban after 5 warnings.")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

        else:
            # Save the updated warning list
            self.save_warns(warns)

            # Send embed with the warning details
            embed = discord.Embed(
                title="Member Warned",
                description=f"{member} has been warned.",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided.")
            embed.add_field(name="Total Warnings", value=len(warns[str(member.id)]))
            await ctx.send(embed=embed)

            # Send a DM to the warned member
            try:
                await member.send(f"You have been warned in {ctx.guild.name}. Reason: {reason or 'No reason provided.'}")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member

    @commands.command(name="warnings")
    async def warnings(self, ctx, member: discord.Member):
        """Display the number of warnings a member has."""
        warns = self.load_warns()

        # Get the number of warnings for the member
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

    @commands.command(name="clearwarnings")
    @commands.has_permissions(kick_members=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member."""
        warns = self.load_warns()

        if str(member.id) in warns:
            del warns[str(member.id)]
            self.save_warns(warns)
            embed = discord.Embed(
                title="Warnings Cleared",
                description=f"All warnings for {member} have been cleared.",
                color=discord.Color.green()
            )

            # Send a DM to the member whose warnings were cleared
            try:
                await member.send(f"All of your warnings have been cleared in {ctx.guild.name}.")
            except discord.errors.Forbidden:
                pass  # Handle if the bot cannot DM the member
        else:
            embed = discord.Embed(
                title="No Warnings",
                description=f"{member} has no warnings to clear.",
                color=discord.Color.red()
            )
        await ctx.send(embed=embed)

    @commands.group(name='modhelp', invoke_without_command=True)
    async def mod_help_group(self, ctx):
        """Display help for moderation commands."""
        
        # Check if the user has the "mod" role
        mod_role = discord.utils.get(ctx.guild.roles, name=MOD_ROLE)
        if mod_role not in ctx.author.roles:  # If the user doesn't have the "mod" role
            appeal_message = await ctx.send(
                f"{BOT_PREFIX}modhelp: You need the ```{MOD_ROLE}``` role to access the moderation commands."
            )
            await asyncio.sleep(5)  # Wait for 5 seconds before deleting the message
            await appeal_message.delete()  # Delete the appeal message
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

        await ctx.send(embed=help_embed)


async def setup(bot):
    await bot.add_cog(Mod(bot))

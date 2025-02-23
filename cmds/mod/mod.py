import discord
from discord.ext import commands
import os
import json
import asyncio
import config
from config import OWNER_ID, BOT_PREFIX, MOD_ROLE, TIMEOUT_ROLE_NAME
from datetime import datetime, timedelta

class Mod(commands.Cog):
    """Enhanced moderation commands such as kick, ban, mute, etc., integrating AutoModeration warnings."""

    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_file = os.path.join(self.data_dir, "automod_data.json")

    def load_settings(self, guild_id):
        """Load settings from automod_data.json for a specific guild."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                try:
                    data = json.load(f)
                    return data.get(str(guild_id), {})
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_settings(self, guild_id, settings):
        """Save settings to automod_data.json for a specific guild."""
        with open(self.settings_file, "r+") as f:
            try:
                data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = {}
            data[str(guild_id)] = settings
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    def get_guild_settings(self, guild_id):
        """Get or initialize guild settings from automod_data.json."""
        guild_id_str = str(guild_id)
        settings = self.load_settings(guild_id)
        if not settings:
            settings = {
                "enabled": False,
                "banned_words": [],
                "mute_threshold": 5,
                "ban_threshold": 10,
                "mute_duration": 60,
                "warnings": [],
                "log_channel": None,
                "ban_default_offensive": False
            }
            self.save_settings(guild_id, settings)
        else:
            # Migrate old integer warnings if present
            if "warnings" in settings and not isinstance(settings["warnings"], list):
                settings["warnings"] = [{"reason": "Legacy warning", "issuer": "Unknown", "timestamp": datetime.utcnow().isoformat(), "user_id": "unknown"}] if settings["warnings"] > 0 else []
                self.save_settings(guild_id, settings)
        return settings

    def create_embed(self, title, description, color=discord.Color.blue(), fields=None):
        """Helper method to create embeds."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        if fields:
            for name, value in fields:
                embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        return embed

    async def _check_dm(self, ctx):
        """Check if the command is used in a DM and send an error."""
        if ctx.guild is None:
            embed = self.create_embed(
                "❌ Cannot Use in DMs",
                "Moderation commands can only be used in a server.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
            return False
        return True

    async def _send_error_message(self, ctx, message, details=None):
        """Send error messages with optional details, lasting longer."""
        embed = self.create_embed(
            "❌ Error",
            message,
            color=discord.Color.red(),
            fields=[("Details", str(details))] if details else None
        )
        error_message = await ctx.send(embed=embed)
        await asyncio.sleep(10)
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
                for channel in guild.text_channels:
                    await channel.set_permissions(timeout_role, send_messages=False, add_reactions=False)
                for channel in guild.voice_channels:
                    await channel.set_permissions(timeout_role, speak=False, connect=False)
            except discord.errors.Forbidden:
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
            embed = self.create_embed(
                "✋ Member Kicked",
                f"{member.mention} (`{member.id}`) has been kicked.",
                color=discord.Color.green(),
                fields=[
                    ("Moderator", ctx.author.mention),
                    ("Reason", reason or "No reason provided")
                ]
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = self.create_embed(
                "✋ Kicked",
                f"You were kicked from **{ctx.guild.name}**.",
                color=discord.Color.red(),
                fields=[("Reason", reason or "No reason provided")]
            )
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                pass

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
            embed = self.create_embed(
                "⛔ Member Banned",
                f"{member.mention} (`{member.id}`) has been banned.",
                color=discord.Color.red(),
                fields=[
                    ("Moderator", ctx.author.mention),
                    ("Reason", reason or "No reason provided")
                ]
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = self.create_embed(
                "⛔ Banned",
                f"You were banned from **{ctx.guild.name}**.",
                color=discord.Color.red(),
                fields=[("Reason", reason or "No reason provided")]
            )
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                pass

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
            embed = self.create_embed(
                "🔓 User Unbanned",
                f"{user.mention} (`{user.id}`) has been unbanned.",
                color=discord.Color.green(),
                fields=[
                    ("Moderator", ctx.author.mention),
                    ("Reason", reason or "No reason provided")
                ]
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = self.create_embed(
                "🔓 Unbanned",
                f"You have been unbanned from **{ctx.guild.name}**.",
                color=discord.Color.green(),
                fields=[("Reason", reason or "No reason provided")]
            )
            try:
                await user.send(embed=dm_embed)
            except discord.errors.Forbidden:
                pass

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

            deleted = await ctx.channel.purge(limit=amount + 1)
            embed = self.create_embed(
                "🧹 Messages Cleared",
                f"Cleared {len(deleted) - 1} messages from {ctx.channel.mention}.",
                color=discord.Color.green(),
                fields=[("Moderator", ctx.author.mention)]
            )
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
            embed = self.create_embed(
                "🤐 Member Muted",
                f"{member.mention} (`{member.id}`) has been muted.",
                color=discord.Color.orange(),
                fields=[
                    ("Moderator", ctx.author.mention),
                    ("Reason", reason or "No reason provided"),
                    ("Duration", f"{duration} minutes" if duration else "Indefinite")
                ]
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = self.create_embed(
                "🤐 Muted",
                f"You were muted in **{ctx.guild.name}**.",
                color=discord.Color.orange(),
                fields=[
                    ("Reason", reason or "No reason provided"),
                    ("Duration", f"{duration} minutes" if duration else "Indefinite")
                ]
            )
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                pass

            if duration:
                await asyncio.sleep(duration * 60)
                if mute_role in member.roles:
                    await member.remove_roles(mute_role)
                    unmute_embed = self.create_embed(
                        "🗣️ Mute Expired",
                        f"{member.mention} (`{member.id}`) has been unmuted after {duration} minutes.",
                        color=discord.Color.green()
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
            embed = self.create_embed(
                "🗣️ Member Unmuted",
                f"{member.mention} (`{member.id}`) has been unmuted.",
                color=discord.Color.green(),
                fields=[("Moderator", ctx.author.mention)]
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=embed)

            dm_embed = self.create_embed(
                "🗣️ Unmuted",
                f"You have been unmuted in **{ctx.guild.name}**.",
                color=discord.Color.green()
            )
            try:
                await member.send(embed=dm_embed)
            except discord.errors.Forbidden:
                pass

        except discord.errors.Forbidden:
            await self._send_error_message(ctx, f"I lack permission to unmute {member.mention}.")
        except Exception as e:
            await self._send_error_message(ctx, f"Failed to unmute {member.mention}.", str(e))

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member for inappropriate behavior, integrating with AutoModeration warnings."""
        if not await self._check_dm(ctx):
            return

        try:
            guild_id = ctx.guild.id
            settings = self.get_guild_settings(guild_id)
            max_warns = settings["ban_threshold"]
            user_id_str = str(member.id)

            warning = {
                "reason": reason or "No reason provided",
                "issuer": str(ctx.author),
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id_str
            }
            settings["warnings"].append(warning)
            user_warnings = [w for w in settings["warnings"] if w.get("user_id", "unknown") == user_id_str]
            warning_count = len(user_warnings)

            if warning_count >= max_warns:
                await member.ban(reason=f"Auto-ban after {max_warns} warnings. Last reason: {reason}")
                embed = self.create_embed(
                    "⛔ Member Auto-Banned",
                    f"{member.mention} (`{member.id}`) banned after {max_warns} warnings.",
                    color=discord.Color.red(),
                    fields=[
                        ("Last Reason", warning["reason"]),
                        ("Moderator", ctx.author.mention),
                        ("Timestamp", warning["timestamp"]),
                        ("Total Warnings", f"{warning_count}")
                    ]
                )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

                dm_embed = self.create_embed(
                    "⛔ Auto-Banned",
                    f"You were banned from **{ctx.guild.name}** after exceeding the warning threshold.",
                    color=discord.Color.red(),
                    fields=[
                        ("Reason", warning["reason"]),
                        ("Warned By", ctx.author.mention),
                        ("Timestamp", warning["timestamp"]),
                        ("Total Warnings", f"{warning_count}/{max_warns}")
                    ]
                )
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    pass
                settings["warnings"] = [w for w in settings["warnings"] if w.get("user_id", "unknown") != user_id_str]
            else:
                self.save_settings(guild_id, settings)
                embed = self.create_embed(
                    "⚠️ Member Warned",
                    f"{member.mention} (`{member.id}`) has been warned.",
                    color=discord.Color.yellow(),
                    fields=[
                        ("Reason", warning["reason"]),
                        ("Warn Count", f"{warning_count}/{settings['mute_threshold']} Before Mute | (Ban at {max_warns})"),
                        ("Moderator", ctx.author.mention),
                        ("Timestamp", warning["timestamp"])
                    ]
                )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

                dm_embed = self.create_embed(
                    "⚠️ Warned",
                    f"You were warned in **{ctx.guild.name}**.",
                    color=discord.Color.yellow(),
                    fields=[
                        ("Reason", warning["reason"]),
                        ("Warned By", ctx.author.mention),
                        ("Timestamp", warning["timestamp"]),
                        ("Warn Count", f"{warning_count}/{settings['mute_threshold']} Before Mute | (Ban at {max_warns})")
                    ]
                )
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    pass

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
            settings = self.get_guild_settings(guild_id)
            user_id_str = str(member.id)
            # Handle both old (no user_id) and new (with user_id) warnings
            user_warnings = [w for w in settings["warnings"] if w.get("user_id", user_id_str) == user_id_str]

            if user_warnings:
                embed = self.create_embed(
                    f"📜 Warnings for {member}",
                    f"{member.mention} (`{member.id}`) has {len(user_warnings)} warnings.",
                    color=discord.Color.orange()
                )
                for i, warning in enumerate(user_warnings, 1):
                    embed.add_field(
                        name=f"Warning {i}",
                        value=f"**Reason:** {warning['reason']}\n**Issuer:** {warning['issuer']}\n**Timestamp:** {warning['timestamp']}",
                        inline=False
                    )
                embed.add_field(
                    name="Total",
                    value=f"{len(user_warnings)}/{settings['mute_threshold']} Before Mute | (Ban at {settings['ban_threshold']})",
                    inline=True
                )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            else:
                embed = self.create_embed(
                    "📜 No Warnings",
                    f"{member.mention} (`{member.id}`) has no warnings.",
                    color=discord.Color.green()
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
            settings = self.get_guild_settings(guild_id)
            user_id_str = str(member.id)
            user_warnings = [w for w in settings["warnings"] if w.get("user_id", user_id_str) == user_id_str]

            if user_warnings:
                settings["warnings"] = [w for w in settings["warnings"] if w.get("user_id", user_id_str) != user_id_str]
                self.save_settings(guild_id, settings)
                embed = self.create_embed(
                    "🧹 Warnings Cleared",
                    f"All warnings for {member.mention} (`{member.id}`) have been cleared.",
                    color=discord.Color.green(),
                    fields=[
                        ("Moderator", ctx.author.mention),
                        ("Timestamp", datetime.utcnow().isoformat())
                    ]
                )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
                await ctx.send(embed=embed)

                dm_embed = self.create_embed(
                    "✅ Warnings Cleared",
                    f"All your warnings in **{ctx.guild.name}** have been cleared.",
                    color=discord.Color.green(),
                    fields=[("Moderator", ctx.author.mention)]
                )
                try:
                    await member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    pass
            else:
                embed = self.create_embed(
                    "🧹 No Warnings to Clear",
                    f"{member.mention} (`{member.id}`) has no warnings.",
                    color=discord.Color.orange()
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
                embed = self.create_embed(
                    "❌ Access Denied",
                    f"You need the `{MOD_ROLE}` role to use moderation commands.",
                    color=discord.Color.red()
                )
                appeal_message = await ctx.send(embed=embed)
                await asyncio.sleep(10)
                await appeal_message.delete()
                return

            help_embed = self.create_embed(
                "🛡️ Moderation Commands",
                f"Commands for managing {ctx.guild.name} (warnings shared with AutoModeration):",
                color=discord.Color.blue(),
                fields=[
                    (f"✋ {BOT_PREFIX}kick <member> [reason]", "Kick a member."),
                    (f"⛔ {BOT_PREFIX}ban <member> [reason]", "Ban a member."),
                    (f"🔓 {BOT_PREFIX}unban <user_id> [reason]", "Unban a user by ID."),
                    (f"🧹 {BOT_PREFIX}clear <amount>", "Clear messages (max 100)."),
                    (f"🤐 {BOT_PREFIX}mute <member> [minutes] [reason]", "Mute a member (optional duration)."),
                    (f"🗣️ {BOT_PREFIX}unmute <member>", "Unmute a member."),
                    (f"⚠️ {BOT_PREFIX}warn <member> [reason]", "Warn a member (auto-ban at threshold)."),
                    (f"📜 {BOT_PREFIX}warnings <member>", "View a member’s warnings."),
                    (f"🧹⚠️ {BOT_PREFIX}clearwarnings <member>", "Clear a member’s warnings.")
                ]
            )
            help_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7235/7235288.png")
            await ctx.send(embed=help_embed)

        except Exception as e:
            await self._send_error_message(ctx, "Failed to display moderation help.", str(e))

async def setup(bot):
    await bot.add_cog(Mod(bot))

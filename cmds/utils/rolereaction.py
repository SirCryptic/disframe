import discord
from discord.ext import commands
import config
import json
import os
import asyncio

class RoleReaction(commands.Cog):
    """A cog for setting up role reaction channels with user-defined emojis."""

    def __init__(self, bot):
        self.bot = bot
        self.BOT_USER_ROLE = config.BOT_USER_ROLE
        self.data_file = "role_reaction_data.json"
        self.load_data()

    def load_data(self):
        """Load the role reaction data from JSON file."""
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                try:
                    self.data = json.load(f)
                except json.JSONDecodeError:
                    self.data = {}
        else:
            self.data = {}

    def save_data(self):
        """Save the role reaction data to JSON file."""
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def create_reaction_embed(self, roles):
        """Create an embed for the role reaction message with bot's avatar."""
        embed = discord.Embed(
            title="🎨 Role Assignment",
            description="React with the emoji below to toggle the role:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        for emoji, role_name in roles.items():
            embed.add_field(name=f"{emoji} {role_name}", value="Click to toggle!", inline=False)
        embed.set_thumbnail(url=self.bot.user.avatar.url)  # Use bot's avatar
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}")
        return embed

    def setup_prompt_embed(self):
        """Create an embed for the setup prompt."""
        return discord.Embed(
            title="🎨 Setup Role Reaction",
            description="Let’s set up role reactions!\n"
                        "1. List roles (comma-separated, e.g., `Role1, Role2`).\n"
                        "2. List emojis in the same order (e.g., `😊, 🚀`).\n"
                        "3. I’ll create a message for role assignment.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

    def role_list_embed(self):
        """Create an embed for asking about roles."""
        return discord.Embed(
            title="📋 Role List",
            description=f"List roles to include (e.g., `Role1, Role2`). Separate with commas. Mentions or names work!",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

    def emoji_list_embed(self):
        """Create an embed for asking about emojis."""
        return discord.Embed(
            title="🎉 Emoji List",
            description="List emojis for each role in order (e.g., `😊, 🚀`). "
                        "Separate with commas. Must match role count!",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

    def confirmation_embed(self, roles, emojis):
        """Create an embed for confirmation."""
        embed = discord.Embed(
            title="✅ Confirm Setup",
            description="Please confirm the role-emoji pairs below:\n"
                        "React with ✅ to proceed or ❌ to cancel.",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        for emoji, role in zip(emojis, roles):
            embed.add_field(name=f"{emoji}", value=role, inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}")
        return embed

    def timeout_error_embed(self):
        """Create an embed for timeout error."""
        return discord.Embed(
            title="⏳ Setup Timeout",
            description="Setup timed out. All messages will be cleaned up.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

    def no_valid_roles_embed(self):
        """Create an embed for when no valid roles are provided."""
        return discord.Embed(
            title="❌ No Valid Roles",
            description="No valid roles were provided or found in this server.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

    def setup_complete_embed(self):
        """Create an embed for completion of setup."""
        return discord.Embed(
            title="✅ Setup Complete",
            description="Role reaction system is set up! Users can now react to toggle roles.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

    def dm_error_embed(self, is_owner_or_dev=False):
        """Create an embed for DM error with special message for owner/devs."""
        if is_owner_or_dev:
            embed = discord.Embed(
                title="❌ Server-Only Feature",
                description=f"`{self.bot.command_prefix}setuprolereaction` and `{self.bot.command_prefix}clearrolereaction` are server-only commands.\n"
                            "Please use these in a guild channel where you have `Manage Server` permissions.\n"
                            f"Example: In a server, type `{self.bot.command_prefix}setuprolereaction` to start the setup process.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
        else:
            embed = discord.Embed(
                title="❌ Guild Only",
                description="This command must be used in a server channel.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}")
        return embed

    async def _check_dm(self, ctx):
        """Check if the command is used in a DM and send an appropriate message."""
        if ctx.guild is None:
            is_owner_or_dev = ctx.author.id == config.OWNER_ID or ctx.author.id in config.DEV_IDS
            await ctx.send(embed=self.dm_error_embed(is_owner_or_dev))
            return False
        return True

    @commands.command(name="setuprolereaction")
    @commands.has_guild_permissions(manage_guild=True)
    async def setup_role_reaction(self, ctx):
        """Set up a role reaction system with cleanup."""
        if not await self._check_dm(ctx):
            return

        setup_messages = []

        # Prompt for setup
        prompt = await ctx.send(embed=self.setup_prompt_embed())
        setup_messages.append(prompt)
        role_prompt = await ctx.send(embed=self.role_list_embed())
        setup_messages.append(role_prompt)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            role_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            setup_messages.append(role_msg)
            roles_input = [r.strip() for r in role_msg.content.split(',')]

            # Process roles (mentions or names)
            valid_roles = []
            for role in roles_input:
                if role.startswith('<@&') and role.endswith('>'):
                    role_id = int(role[3:-1])
                    role_obj = ctx.guild.get_role(role_id)
                    if role_obj:
                        valid_roles.append(role_obj.name)
                elif discord.utils.get(ctx.guild.roles, name=role):
                    valid_roles.append(role)

            if not valid_roles or not any(r in [role.name for role in ctx.guild.roles] for r in valid_roles):
                error_msg = await ctx.send(embed=self.no_valid_roles_embed())
                setup_messages.append(error_msg)
                await asyncio.sleep(5)
                await self.cleanup_messages(setup_messages)
                return

            # Ask for emojis
            emoji_prompt = await ctx.send(embed=self.emoji_list_embed())
            setup_messages.append(emoji_prompt)
            emoji_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            setup_messages.append(emoji_msg)
            emojis_input = [e.strip() for e in emoji_msg.content.split(',')]

            if len(emojis_input) != len(valid_roles):
                error_msg = await ctx.send(embed=discord.Embed(
                    title="❌ Mismatch",
                    description=f"Number of emojis ({len(emojis_input)}) doesn’t match roles ({len(valid_roles)}).",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                ))
                setup_messages.append(error_msg)
                await asyncio.sleep(5)
                await self.cleanup_messages(setup_messages)
                return

            # Validate emojis
            roles_with_emojis = {}
            for emoji, role_name in zip(emojis_input, valid_roles):
                try:
                    await ctx.message.add_reaction(emoji)
                    roles_with_emojis[emoji] = role_name
                except discord.HTTPException:
                    error_msg = await ctx.send(embed=discord.Embed(
                        title="❌ Invalid Emoji",
                        description=f"Emoji `{emoji}` is not valid or usable by the bot.",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    ))
                    setup_messages.append(error_msg)
                    await asyncio.sleep(5)
                    await self.cleanup_messages(setup_messages)
                    return

            # Confirmation step
            confirm_embed = self.confirmation_embed(valid_roles, roles_with_emojis.keys())
            confirm_msg = await ctx.send(embed=confirm_embed)
            setup_messages.append(confirm_msg)
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")

            def confirm_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id

            reaction, _ = await self.bot.wait_for('reaction_add', check=confirm_check, timeout=60.0)
            if str(reaction.emoji) == "❌":
                cancel_msg = await ctx.send(embed=discord.Embed(
                    title="❌ Setup Cancelled",
                    description="Role reaction setup has been cancelled.",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                ))
                setup_messages.append(cancel_msg)
                await asyncio.sleep(5)
                await self.cleanup_messages(setup_messages)
                return

            # Final setup
            embed = self.create_reaction_embed(roles_with_emojis)
            reaction_msg = await ctx.send(embed=embed)
            for emoji in roles_with_emojis.keys():
                await reaction_msg.add_reaction(emoji)

            guild_id = str(ctx.guild.id)
            self.data[guild_id] = {
                "message_id": reaction_msg.id,
                "roles": roles_with_emojis
            }
            self.save_data()

            complete_msg = await ctx.send(embed=self.setup_complete_embed())
            setup_messages.append(complete_msg)
            await asyncio.sleep(5)
            await self.cleanup_messages(setup_messages)

        except asyncio.TimeoutError:
            timeout_msg = await ctx.send(embed=self.timeout_error_embed())
            setup_messages.append(timeout_msg)
            await asyncio.sleep(5)
            await self.cleanup_messages(setup_messages)
            return

    async def cleanup_messages(self, messages):
        """Clean up setup messages."""
        for msg in messages:
            try:
                await msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

    @commands.command(name="clearrolereaction")
    @commands.has_guild_permissions(manage_guild=True)
    async def clear_role_reaction(self, ctx):
        """Remove the role reaction setup for this guild."""
        if not await self._check_dm(ctx):
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in self.data:
            embed = discord.Embed(
                title="❌ No Setup",
                description="There’s no role reaction setup in this guild.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}")
            await ctx.send(embed=embed)
            return

        message_id = self.data[guild_id]["message_id"]
        channel = ctx.channel
        try:
            message = await channel.fetch_message(message_id)
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass  # Message already deleted or bot lacks permission

        del self.data[guild_id]
        self.save_data()

        embed = discord.Embed(
            title="🧹 Role Reaction Cleared",
            description="The role reaction setup has been removed.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction adds for role assignment."""
        if payload.guild_id is None:
            return

        guild_id = str(payload.guild_id)
        if guild_id not in self.data or payload.message_id != self.data[guild_id]["message_id"]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        emoji = str(payload.emoji)
        if emoji in self.data[guild_id]["roles"]:
            role_name = self.data[guild_id]["roles"][emoji]
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                try:
                    await member.add_roles(role)
                    await member.send(embed=discord.Embed(
                        title="🎉 Role Assigned",
                        description=f"You’ve been assigned the **{role.name}** role!",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    ))
                except discord.Forbidden:
                    print(f"[ERROR] Failed to assign role {role_name} to {member}: Insufficient permissions")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removes for role removal."""
        if payload.guild_id is None:
            return

        guild_id = str(payload.guild_id)
        if guild_id not in self.data or payload.message_id != self.data[guild_id]["message_id"]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        emoji = str(payload.emoji)
        if emoji in self.data[guild_id]["roles"]:
            role_name = self.data[guild_id]["roles"][emoji]
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                try:
                    await member.remove_roles(role)
                    await member.send(embed=discord.Embed(
                        title="🔄 Role Removed",
                        description=f"The **{role.name}** role has been removed from you.",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow()
                    ))
                except discord.Forbidden:
                    print(f"[ERROR] Failed to remove role {role_name} from {member}: Insufficient permissions")

async def setup(bot):
    await bot.add_cog(RoleReaction(bot))

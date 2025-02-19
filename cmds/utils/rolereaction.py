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
                self.data = json.load(f)
        else:
            self.data = {}

    def save_data(self):
        """Save the role reaction data to JSON file."""
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def create_reaction_embed(self, roles):
        """Create an embed for the role reaction message."""
        embed = discord.Embed(
            title="🎨 Role Assignment",
            description="React with the corresponding emoji to gain/lose the role:",
            color=discord.Color.blue()
        )
        for emoji, role_name in roles.items():
            embed.add_field(name=f"{emoji} {role_name}", value="Click to toggle this role!", inline=False)
        embed.set_footer(text="Hover over the emoji to see the role name!")
        return embed

    def setup_prompt_embed(self):
        """Create an embed for the setup prompt."""
        return discord.Embed(
            title="Setup Role Reaction",
            description="Let's set up the role reaction system! Here's how it works:\n"
                        "- I'll ask you which roles you want to include.\n"
                        "- You tell me the roles, separated by commas.\n"
                        "- I'll then ask for corresponding emojis.\n"
                        "- I'll set up the message in this channel with reactions for each role.",
            color=discord.Color.blue()
        )

    def role_list_embed(self):
        """Create an embed for asking about roles."""
        return discord.Embed(
            title="Role List",
            description=f"Please list the roles you want for reactions. Include `{self.BOT_USER_ROLE}` if you want. "
                        f"Separate roles with commas, like: `Role1, Role2, {self.BOT_USER_ROLE}`",
            color=discord.Color.green()
        )

    def emoji_list_embed(self):
        """Create an embed for asking about emojis."""
        return discord.Embed(
            title="Emoji List",
            description=f"Please list the emojis you want to use for each role. "
                        f"Separate emojis with commas, matching the order of roles. "
                        f"Example: `:emoji1:, :emoji2:, :emoji3:`",
            color=discord.Color.orange()
        )

    def timeout_error_embed(self):
        """Create an embed for timeout error."""
        return discord.Embed(
            title="Setup Timeout",
            description="❌ Setup timed out. Please try again later.",
            color=discord.Color.red()
        )

    def no_valid_roles_embed(self):
        """Create an embed for when no valid roles are provided."""
        return discord.Embed(
            title="No Valid Roles",
            description="❌ No valid roles were provided or found in this server.",
            color=discord.Color.red()
        )

    def setup_complete_embed(self):
        """Create an embed for completion of setup."""
        return discord.Embed(
            title="Setup Complete",
            description="✅ Role reaction setup complete! Users can now react to the message to gain roles.",
            color=discord.Color.green()
        )

    def dm_error_embed(self):
        """Create an embed for DM error."""
        return discord.Embed(
            title="Error",
            description="This command must be used in a guild channel.",
            color=discord.Color.red()
        )

    @commands.command(name="setuprolereaction")
    @commands.has_guild_permissions(manage_guild=True)
    async def setup_role_reaction(self, ctx):
        if not await self._check_dm(ctx):
            return

        await ctx.send(embed=self.setup_prompt_embed())

        await ctx.send(embed=self.role_list_embed())

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            roles_input = msg.content.split(',')
            
            # Handle both name and mention formats
            role_names = []
            for role in roles_input:
                stripped_role = role.strip()
                if stripped_role.startswith('<@&') and stripped_role.endswith('>'):
                    role_id = int(stripped_role[3:-1])  # Extract the ID from mention format
                    role_obj = ctx.guild.get_role(role_id)
                    if role_obj:
                        role_names.append(role_obj.name)
                else:
                    role_names.append(stripped_role)
            
           # print(f"Roles input after processing: {role_names}")  # Debug print
            
            if self.BOT_USER_ROLE not in role_names:
                role_names.append(self.BOT_USER_ROLE)
          #  print(f"Roles with bot user added: {role_names}")  # Debug print
        except asyncio.TimeoutError:
            await ctx.send(embed=self.timeout_error_embed())
            return

        # Filter out roles that don't exist in the guild while maintaining order
        valid_roles = [role for role in role_names if role in [r.name for r in ctx.guild.roles]]
       # print(f"Valid roles in order: {valid_roles}")  # Debug print

        if not valid_roles:
            await ctx.send(embed=self.no_valid_roles_embed())
            return

        # Ask for emojis
        await ctx.send(embed=self.emoji_list_embed())

        try:
            emoji_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            emojis_input = [emoji.strip() for emoji in emoji_msg.content.split(',')]
          #  print(f"Emojis input: {emojis_input}")  # Debug print
            if len(emojis_input) != len(valid_roles):
             #   print(f"Role count: {len(valid_roles)}, Emoji count: {len(emojis_input)}")  # Debug print
                raise ValueError("Mismatch in number of roles and emojis provided.")
        except asyncio.TimeoutError:
            await ctx.send(embed=self.timeout_error_embed())
            return
        except ValueError as e:
            await ctx.send(embed=discord.Embed(title="Error", description=str(e), color=discord.Color.red()))
            return

        roles_with_emojis = {}
        available_emojis = []

        for emoji, role_name in zip(emojis_input, valid_roles):
            try:
                await ctx.message.add_reaction(emoji)
                roles_with_emojis[emoji] = role_name
                available_emojis.append(emoji)
            except discord.errors.HTTPException:
                print(f"Emoji {emoji} not available, skipping.")
        
        if not available_emojis:
            await ctx.send(embed=self.no_valid_roles_embed())
            return

        # Create and send the embed
        embed = self.create_reaction_embed(roles_with_emojis)
        reaction_msg = await ctx.send(embed=embed)

        # Add reactions
        for emoji in available_emojis:
            await reaction_msg.add_reaction(emoji)

        # Save the message ID and roles mapping for this guild
        guild_id = str(ctx.guild.id)
        self.data[guild_id] = {
            "message_id": reaction_msg.id,
            "roles": roles_with_emojis
        }
        self.save_data()

        await ctx.send(embed=self.setup_complete_embed())

    async def _check_dm(self, ctx):
        """Check if the command is used in a DM and send an appropriate message."""
        if ctx.guild is None:
            await ctx.send(embed=self.dm_error_embed())
            return False
        return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id is None:  # Ignore reactions from DMs
            return

        guild_id = str(payload.guild_id)
        if guild_id not in self.data:
            return

        if payload.message_id != self.data[guild_id]["message_id"]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            return

        emoji = str(payload.emoji)
        if emoji in self.data[guild_id]["roles"]:
            role_name = self.data[guild_id]["roles"][emoji]
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await member.add_roles(role)
                try:
                    await member.send(embed=discord.Embed(
                        title="Role Assigned",
                        description=f"🎉 You've been assigned the **{role.name}** role!",
                        color=discord.Color.green()
                    ))
                except discord.errors.Forbidden:
                    pass  # User has DMs closed

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.guild_id is None:
            return

        guild_id = str(payload.guild_id)
        if guild_id not in self.data:
            return

        if payload.message_id != self.data[guild_id]["message_id"]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            return

        emoji = str(payload.emoji)
        if emoji in self.data[guild_id]["roles"]:
            role_name = self.data[guild_id]["roles"][emoji]
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await member.remove_roles(role)
                try:
                    await member.send(embed=discord.Embed(
                        title="Role Removed",
                        description=f"🔄 The **{role.name}** role has been removed from you.",
                        color=discord.Color.orange()
                    ))
                except discord.errors.Forbidden:
                    pass  # User has DMs closed

async def setup(bot):
    await bot.add_cog(RoleReaction(bot))

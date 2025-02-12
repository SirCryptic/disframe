import discord
from discord.ext import commands
import config

class Help(commands.Cog):
    """Custom help command with organized sections for General, Mod, and Dev commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def custom_help(self, ctx):
        """Display the help menu with organized sections and buttons for pagination."""
        
        # Get the bot owner's profile dynamically
        owner = await self.bot.fetch_user(config.OWNER_ID)
        footer_text = f"{config.BOT_NAME} - Beta v{config.BOT_VERSION} - developed by {owner.name}"

        # General Help Page (Always Visible)
        general_embed = discord.Embed(
            title="Help Menu - General Commands",
            description="The following commands are available for everyone:",
            color=discord.Color.blue(),
        )
        general_embed.add_field(name=f"```{config.BOT_PREFIX}example```", value="An example command.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}info```", value="Displays Information About The Bot.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}serverinfo```", value="Displays Information About The Server.", inline=False)
        general_embed.set_footer(text=footer_text)

        # If in DMs
        if isinstance(ctx.channel, discord.DMChannel):
            if ctx.author.id == config.OWNER_ID or ctx.author.id in config.DEV_IDS:
                # Dev Page (Accessible to DEV_IDS and OWNER_ID only)
                dev_embed = discord.Embed(
                    title="Help Menu - Dev Commands",
                    description="The following commands are available for developers only:",
                    color=discord.Color.blue(),
                )
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}lock```", value="Lock the bot to dev users only.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}unlock```", value="Unlock the bot to all users.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}adminhelp```", value="List full available commands. [Owner Only]", inline=False)
                dev_embed.set_footer(text=footer_text)

                help_pages = [general_embed, dev_embed]
            else:
                # Non-dev users in DMs only see the general page
                help_pages = [general_embed]
            
            # Send help menu with pagination
            view = HelpView(help_pages)
            await view.send(ctx)
            return

        # If in a Guild
        help_pages = [general_embed]
        user_roles = [role.name.lower() for role in ctx.author.roles]

        # Mod Page (Accessible to MOD_ROLE, OWNER_ID, or DEV_IDS)
        if config.MOD_ROLE.lower() in user_roles or ctx.author.guild_permissions.manage_messages or ctx.author.id == config.OWNER_ID or ctx.author.id in config.DEV_IDS:
            mod_embed = discord.Embed(
                title="Help Menu - Mod Commands",
                description="The following commands are available for moderators:",
                color=discord.Color.blue(),
            )
            mod_embed.add_field(name=f"```{config.BOT_PREFIX}modhelp```", value="Lists available moderation commands. [Mod Only]", inline=False)
            mod_embed.set_footer(text=footer_text)
            help_pages.append(mod_embed)

        # Dev Page (Accessible to DEV_IDS and OWNER_ID only)
        if ctx.author.id == config.OWNER_ID or ctx.author.id in config.DEV_IDS:
            dev_embed = discord.Embed(
                title="Help Menu - Dev Commands",
                description="The following commands are available for developers only:",
                color=discord.Color.blue(),
            )
            dev_embed.add_field(name=f"```{config.BOT_PREFIX}lock```", value="Lock the bot to dev users only.", inline=False)
            dev_embed.add_field(name=f"```{config.BOT_PREFIX}unlock```", value="Unlock the bot to all users.", inline=False)
            dev_embed.add_field(name=f"```{config.BOT_PREFIX}adminhelp```", value="List full available commands. [Owner Only]", inline=False)
            dev_embed.set_footer(text=footer_text)
            help_pages.append(dev_embed)

        # Send help menu with pagination
        view = HelpView(help_pages)
        await view.send(ctx)

class HelpView(discord.ui.View):
    """View to handle button interactions for pagination."""
    
    def __init__(self, help_pages):
        super().__init__(timeout=120)  # Set a 2-minute timeout for interactions
        self.embeds = help_pages
        self.current_page = 0
        self.message = None  # Store the message reference

    async def send(self, ctx):
        """Send the message and store it for pagination."""
        self.message = await ctx.send(embed=self.embeds[0], view=self)

    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.secondary, disabled=True)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigate to the previous page."""
        self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigate to the next page."""
        self.current_page += 1
        await self.update_page(interaction)

    async def update_page(self, interaction: discord.Interaction):
        """Update the embed based on the current page and handle button states."""
        self.children[0].disabled = self.current_page == 0  # Disable Back button on first page
        self.children[1].disabled = self.current_page == len(self.embeds) - 1  # Disable Next button on last page

        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def on_timeout(self):
        """Disable buttons when the interaction timeout expires."""
        if self.message:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass  # Ignore error if message was deleted

async def setup(bot):
    await bot.add_cog(Help(bot))

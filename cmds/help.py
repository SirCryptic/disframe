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
        owner = await self.bot.fetch_user(config.OWNER_ID)  # Fetch user based on the stored ID
        footer_text = f"{config.BOT_NAME} - Beta v{config.BOT_VERSION} - developed by {owner.name}"

        # Define general help page (always visible)
        general_embed = discord.Embed(
            title="Help Menu - General Commands",
            description="The following commands are available for everyone:",
            color=discord.Color.blue(),
        )
        general_embed.add_field(name=f"```{config.BOT_PREFIX}example```", value="An example command.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}info```", value="Displays Information About The Bot.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}serverinfo```", value="Displays Information About The Server.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}profile <@/ID>```", value="Fetch OSINT profile information of a Discord user.", inline=False)
        general_embed.set_footer(text=footer_text)

        # If in DMs and the user is NOT the owner, only show the general help page
        if isinstance(ctx.channel, discord.DMChannel) and ctx.author.id != config.OWNER_ID:
            await ctx.send(embed=general_embed)
            return

        # Initialize list of help pages with general commands
        help_pages = [general_embed]

        # Check if this is in a server (so we can check roles)
        if not isinstance(ctx.channel, discord.DMChannel):
            user_roles = [role.name.lower() for role in ctx.author.roles]  # Convert to lowercase for consistency

            # Check if user has the mod role
            if config.MOD_ROLE.lower() in user_roles or ctx.author.guild_permissions.manage_messages:
                mod_embed = discord.Embed(
                    title="Help Menu - Mod Commands",
                    description="The following commands are available for moderators:",
                    color=discord.Color.blue(),
                )
                mod_embed.add_field(name=f"```{config.BOT_PREFIX}modhelp```", value="To List Available Moderation Commands. [Mod Only]", inline=False)
                mod_embed.set_footer(text=footer_text)
                help_pages.append(mod_embed)

            # Check if user has the dev role OR is the bot owner
            if config.DEV_ROLE.lower() in user_roles or ctx.author.id == config.OWNER_ID:
                dev_embed = discord.Embed(
                    title="Help Menu - Dev Commands",
                    description="The following commands are available for developers only:",
                    color=discord.Color.blue(),
                )
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}lock```", value="Lock the bot to dev users only.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}unlock```", value="Unlock the bot to all users.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}adminhelp```", value="To List Full Available Commands [Owner Only].", inline=False)
                dev_embed.set_footer(text=footer_text)
                help_pages.append(dev_embed)

        # If the user is the bot owner, show the Dev commands even in DMs
        if ctx.author.id == config.OWNER_ID:
            dev_embed = discord.Embed(
                title="Help Menu - Dev Commands",
                description="The following commands are available for developers only:",
                color=discord.Color.blue(),
            )
            dev_embed.add_field(name=f"```{config.BOT_PREFIX}lock```", value="Lock the bot to dev users only.", inline=False)
            dev_embed.add_field(name=f"```{config.BOT_PREFIX}unlock```", value="Unlock the bot to all users.", inline=False)
            dev_embed.add_field(name=f"```{config.BOT_PREFIX}adminhelp```", value="To List Full Available Commands [Owner Only].", inline=False)
            dev_embed.set_footer(text=footer_text)
            help_pages.append(dev_embed)

        # Send the first help page using HelpView
        view = HelpView(help_pages)
        await view.send(ctx)  # Send message and store it in HelpView

class HelpView(discord.ui.View):
    """View to handle button interactions for pagination."""
    
    def __init__(self, help_pages):
        super().__init__(timeout=120)  # Set a 2-minute timeout for interactions
        self.embeds = help_pages
        self.current_page = 0
        self.message = None  # Store the message reference

    async def send(self, ctx):
        """Send the message and store it for future edits."""
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

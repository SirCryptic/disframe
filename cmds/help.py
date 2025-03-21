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
        owner = await self.bot.fetch_user(config.OWNER_ID)  # Fetch bot owner dynamically
        footer_text = f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {owner.name}"

        # General Help Page (Visible to everyone)
        general_embed = discord.Embed(
            title="Help Menu - General Commands",
            description="The following commands are available for everyone:",
            color=discord.Color.blue(),
        )
        general_embed.add_field(name=f"```{config.BOT_PREFIX}weather <CITY/COUNTRY>```", value="Get the weather for a specific country / city using openweathermap.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}translate <LANGUAGE_CODE> <TEXT>```", value="Translate a message into another language using Google Translate.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}bug```", value="Report a bug to the Developers.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}info```", value="Displays Information About The Bot.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}serverinfo```", value="Displays Information About The Server.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}profile <@/ID>```", value="Fetch profile information of a Discord user.", inline=False)
        general_embed.add_field(name=f"```{config.BOT_PREFIX}avatar <@/ID>```", value="Display your own or another Discord user's avatar.", inline=False)
        general_embed.set_footer(
            text=footer_text,
            icon_url=self.bot.user.avatar.url
        )

        # Fun Help Page (Visible to everyone)
        fun_embed = discord.Embed(
            title="Help Menu - Fun Commands",
            description="The following commands are available for everyone:",
            color=discord.Color.blue(),
        )
        fun_embed.add_field(name=f"```{config.BOT_PREFIX}meme```", value="Generate a random meme.", inline=False)
        fun_embed.add_field(name=f"```{config.BOT_PREFIX}creatememe```", value="Create your own custom meme.", inline=False)
        fun_embed.add_field(name=f"```{config.BOT_PREFIX}avacreate```", value="Create Your Own Avatar!.", inline=False)
        fun_embed.set_footer(
            text=footer_text,
            icon_url=self.bot.user.avatar.url
        )

        # Games Help Page (Visible to everyone)
        games_embed = discord.Embed(
            title="Help Menu - Games",
            description="The following game commands are available for everyone:",
            color=discord.Color.blue(),
        )
        games_embed.add_field(
            name=f"```{config.BOT_PREFIX}coinhelp``` or ```{config.BOT_PREFIX}coin```",
            value="CoinRush: An economy game with jobs, coins, items, trading, and a casino (guild-only). Use `coinhelp` for info or `coin` for the UI.",
            inline=False
        )
        games_embed.add_field(
            name=f"```{config.BOT_PREFIX}guess```",
            value="GuessGame: Guess a number between 1-100. Multiplayer in guild channels, solo in DMs. Start with `guess` and guess with `guess <number>`.",
            inline=False
        )
        games_embed.set_footer(
            text=footer_text,
            icon_url=self.bot.user.avatar.url
        )

        # Help pages initialization
        help_pages = [general_embed, fun_embed, games_embed]

        # Handle permissions and role-based embeds
        if isinstance(ctx.channel, discord.DMChannel):
            # In DMs
            if ctx.author.id == config.OWNER_ID or ctx.author.id in config.DEV_IDS:
                # Dev Page (Accessible to DEV_IDS and OWNER_ID only)
                dev_embed = discord.Embed(
                    title="Help Menu - Dev Commands",
                    description="The following commands are available for the owner & devs only:",
                    color=discord.Color.blue(),
                )
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}lock```", value="Lock the bot to dev users only.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}unlock```", value="Unlock the bot to all users.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}toggle_dm```", value="Toggle DM allowance for non-privileged users.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}adminhelp```", value="List full available commands.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}bugreportenable```", value="Enable bug reporting.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}bugreportdisable```", value="Disable bug reporting.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}subscriptions```", value="Bring Up The Subscriptions UI.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}status```", value="Check the bot's lock and DM status.", inline=False)
                dev_embed.set_footer(
                    text=footer_text,
                    icon_url=self.bot.user.avatar.url
                )
                help_pages.append(dev_embed)
            # Mod page excluded in DMs
        else:
            # In servers
            user_roles = [role.name.lower() for role in ctx.author.roles]

            # Mod Page (Accessible to MOD_ROLE, OWNER_ID, DEV_IDS, or manage_messages permission)
            if config.MOD_ROLE.lower() in user_roles or ctx.author.guild_permissions.manage_messages or ctx.author.id == config.OWNER_ID or ctx.author.id in config.DEV_IDS:
                mod_embed = discord.Embed(
                    title="Help Menu - Mod Commands",
                    description="The following commands are available for moderators and admins:",
                    color=discord.Color.blue(),
                )
                mod_embed.add_field(name=f"```{config.BOT_PREFIX}modhelp```", value="Lists available moderation commands.", inline=False)
                mod_embed.add_field(name=f"```{config.BOT_PREFIX}automod```", value="Configure auto-moderation settings, including log channel setup.", inline=False)
                mod_embed.add_field(name=f"```{config.BOT_PREFIX}setuprolereaction```", value="Set up role reactions in your desired channel. [Requires Manage Guild]", inline=False)
                mod_embed.add_field(name=f"```{config.BOT_PREFIX}setup```", value="Set up guild roles (e.g., Bot User, Moderator). [Requires Administrator]", inline=False)
                mod_embed.set_footer(
                    text=footer_text,
                    icon_url=self.bot.user.avatar.url
                )
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
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}toggle_dm```", value="Toggle DM allowance for non-privileged users.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}adminhelp```", value="List full available commands.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}bugreportenable```", value="Enable bug reporting.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}bugreportdisable```", value="Disable bug reporting.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}subscriptions```", value="Bring Up The Subscriptions UI.", inline=False)
                dev_embed.add_field(name=f"```{config.BOT_PREFIX}status```", value="Check the bot's lock and DM status.", inline=False)
                dev_embed.set_footer(
                    text=footer_text,
                    icon_url=self.bot.user.avatar.url
                )
                help_pages.append(dev_embed)

        # Send help menu with pagination
        view = HelpView(help_pages)
        await view.send(ctx)

class HelpView(discord.ui.View):
    """View to handle button interactions for pagination."""
    
    def __init__(self, help_pages):
        super().__init__(timeout=120)
        self.embeds = help_pages
        self.current_page = 0
        self.message = None

    async def send(self, ctx):
        """Send the message and store it for pagination."""
        self.message = await ctx.send(embed=self.embeds[0], view=self)

    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.secondary, disabled=True)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page."""
        self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page."""
        self.current_page += 1
        await self.update_page(interaction)

    async def update_page(self, interaction: discord.Interaction):
        """Update the displayed embed based on the current page."""
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == len(self.embeds) - 1
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def on_timeout(self):
        """Disable buttons when interaction times out."""
        if self.message:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

async def setup(bot):
    await bot.add_cog(Help(bot))

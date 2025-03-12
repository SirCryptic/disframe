# cmds/avacreate.py
import discord
from discord.ext import commands
import aiohttp
import io
import config
import asyncio

class AvatarSelect(discord.ui.Select):
    """Dropdown for selecting avatar styles."""
    def __init__(self, cog):
        self.cog = cog
        options = [
            discord.SelectOption(label=style.capitalize(), value=style, description=f"Generate a {style} avatar")
            for style in cog.styles
        ]
        super().__init__(
            placeholder="Choose an avatar style...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle style selection."""
        self.view.style = self.values[0]
        self.disabled = True
        await interaction.response.edit_message(
            content="Configure your avatar below:",
            view=self.view
        )

class BackgroundSelect(discord.ui.Select):
    """Dropdown for selecting background color."""
    def __init__(self):
        options = [
            discord.SelectOption(label="Red", value="ff0000", description="Red background"),
            discord.SelectOption(label="Blue", value="0000ff", description="Blue background"),
            discord.SelectOption(label="Green", value="00ff00", description="Green background"),
            discord.SelectOption(label="Purple", value="800080", description="Purple background")
            # Removed "random" to ensure valid hex codes only
        ]
        super().__init__(
            placeholder="Choose a background color...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle background color selection."""
        self.view.background_color = self.values[0]
        self.disabled = True
        await interaction.response.edit_message(
            content=f"Background color set to: `{self.values[0]}`\nConfigure your avatar below:",
            view=self.view
        )

class SizeSelect(discord.ui.Select):
    """Dropdown for selecting avatar size."""
    def __init__(self):
        options = [
            discord.SelectOption(label="Small (128px)", value="128", description="Small avatar"),
            discord.SelectOption(label="Medium (256px)", value="256", description="Medium avatar"),
            discord.SelectOption(label="Large (512px)", value="512", description="Large avatar")
        ]
        super().__init__(
            placeholder="Choose an avatar size...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle size selection."""
        self.view.size = self.values[0]
        self.disabled = True
        await interaction.response.edit_message(
            content=f"Size set to: `{self.values[0]}px`\nConfigure your avatar below:",
            view=self.view
        )

class SeedModal(discord.ui.Modal):
    """Modal for entering a custom seed."""
    def __init__(self, view):
        super().__init__(title="Set Avatar Seed")
        self.view = view
        self.add_item(discord.ui.TextInput(
            label="Seed",
            placeholder="e.g., 'lol', 'MyName', or '123'",
            required=False,
            max_length=50
        ))

    async def on_submit(self, interaction: discord.Interaction):
        """Handle seed submission."""
        seed = self.children[0].value.strip() or None
        self.view.seed = seed
        await interaction.response.edit_message(
            content=f"Seed set to: `{seed or 'Your ID will be used'}`\nConfigure your avatar below:",
            view=self.view
        )

class AvaCreateView(discord.ui.View):
    """View with style, background, size, seed, generate, and cancel options."""
    def __init__(self, ctx, cog, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.cog = cog
        self.style = None
        self.background_color = "ff0000"  # Default to red hex code
        self.size = "256"  # Default
        self.seed = None
        self.add_item(AvatarSelect(cog))
        self.add_item(BackgroundSelect())
        self.add_item(SizeSelect())

    def disable_all_items(self):
        """Custom method to disable all items in the view."""
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Set Seed", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def seed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Prompt user to enter a seed via modal."""
        if not self.style:
            await interaction.response.send_message("Please select a style first!", ephemeral=True)
            return
        await interaction.response.send_modal(SeedModal(self))

    @discord.ui.button(label="Generate", style=discord.ButtonStyle.green, emoji="✨")
    async def generate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle avatar generation."""
        if not self.style:
            await interaction.response.send_message("Please select a style first!", ephemeral=True)
            return

        seed = self.seed or str(self.ctx.author.id)[:10]  # Truncate to 10 chars
        await self.cog.generate_avatar(self.ctx, interaction, self.style, seed, self.background_color, self.size)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the avatar creation process."""
        self.disable_all_items()
        await interaction.response.edit_message(content="Avatar creation cancelled.", view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command invoker can interact."""
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        """Disable all items on timeout."""
        self.disable_all_items()
        await self.ctx.message.edit(content="Avatar creation timed out.", view=self)

class AvaCreate(commands.Cog):
    """A cog for generating random avatars using the DiceBear API."""

    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://api.dicebear.com/9.x"
        self.styles = [
            "avataaars", "bottts", "pixel-art", "identicon", "initials", 
            "big-ears", "croodles", "micah", "adventurer", "adventurer-neutral",
            "big-smile", "bottts-neutral", "dylan", "fun-emoji", "icons",
            "jason", "lorelei", "lorelei-neutral", "miniavs",
            "open-peeps", "personas", "pixel-art-neutral", "rings", "shapes"
        ]

    async def generate_avatar(self, ctx, interaction, style: str, seed: str, background_color: str, size: str):
        """Generate and send the avatar with options."""
        url = f"{self.base_url}/{style}/png?seed={seed}&size={size}&backgroundColor={background_color}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"API returned status {response.status}")
                    
                    image_data = await response.read()
                    image_file = discord.File(io.BytesIO(image_data), filename=f"avatar_{seed}.png")

                    embed = discord.Embed(
                        title="✨ Your Generated Avatar",
                        description=f"Style: `{style}`\nSeed: `{seed}`\nBackground: `{background_color}`\nSize: `{size}px`",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_image(url="attachment://avatar_{}.png".format(seed))
                    embed.set_footer(
                        text=f"{config.BOT_NAME} v{config.BOT_VERSION}",
                        icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
                    )

                    await ctx.send(embed=embed, file=image_file)
                    await interaction.response.edit_message(content="Avatar generated below!", view=None)

            except Exception as e:
                await ctx.send(embed=discord.Embed(
                    title="❌ Avatar Generation Failed",
                    description=f"Something went wrong while generating the avatar: {str(e)}. Try again later!",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                ).set_footer(text=f"{config.BOT_NAME} v{config.BOT_VERSION}"))

    @commands.command(name="avacreate")
    async def avacreate_command(self, ctx, style: str = None, seed: str = None):
        """Generate a random avatar using DiceBear API.
        
        Usage: !avacreate [style] [seed]
        - style: Optional avatar style (e.g., avataaars, bottts).
        - seed: Optional string to customize the avatar (e.g., your name).
        """
        if style is None and seed is None and len(ctx.message.content.split()) == 1:
            # Show UI if no arguments are provided
            view = AvaCreateView(ctx, self)
            await ctx.send("Pick an avatar style below:", view=view)
            return

        # Handle direct command with arguments (default options)
        style = style.lower() if style else "avataaars"
        if style not in self.styles:
            style = "avataaars"
            await ctx.send(f"Invalid style! Using default 'avataaars'. Available styles: {', '.join(self.styles)}", delete_after=5)
        
        seed = seed or str(ctx.author.id)[:10]  # Truncate to 10 chars
        
        class FakeInteraction:
            def __init__(self, ctx):
                self.response = type('Response', (), {'edit_message': lambda *args, **kwargs: ctx.message.edit(*args, **kwargs)})()
                self.ctx = ctx

            async def followup_send(self, *args, **kwargs):
                await self.ctx.send(*args, **kwargs)

        await self.generate_avatar(ctx, FakeInteraction(ctx), style, seed, "ff0000", "256")

    @property
    def version(self):
        """Return the cog's version."""
        return "1.0.0"  # Unused but kept for potential future use

async def setup(bot):
    """Load the AvaCreate cog."""
    await bot.add_cog(AvaCreate(bot))
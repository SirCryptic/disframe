import discord
from discord.ext import commands
import aiohttp
import asyncio
import config
from config import BOT_PREFIX
from datetime import datetime

class MemeGen(commands.Cog):
    """An advanced cog to create custom memes using memegen.link API with Discord UI."""

    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://memegen.link"
        self.api_templates_url = f"{self.base_url}/api/templates/"
        self.popular_templates = [
            "drake", "buzz", "keanu", "grumpy", "success",
            "both", "fry", "iw", "paw", "rollsafe"
        ]
        self.fonts = ["titilliumweb", "kalam", "impact", "notosans", "hgminchob"]

    def create_embed(self, title, description, color=discord.Color.blue(), image_url=None, fields=None):
        """Helper method for clean embeds."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        if image_url:
            embed.set_image(url=image_url)
        if fields:
            for name, value in fields:
                embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION} | Powered by memegen.link",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed

    async def fetch_templates(self):
        """Fetch available templates from memegen.link API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.api_templates_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return sorted(data.keys())
                return self.popular_templates

    class TextModal(discord.ui.Modal, title="Meme Text"):
        top_text = discord.ui.TextInput(label="Top Text", placeholder="Enter top text", max_length=50)
        bottom_text = discord.ui.TextInput(label="Bottom Text", placeholder="Enter bottom text (optional)", required=False, max_length=50)

        def __init__(self, view):
            super().__init__()
            self.view = view

        async def on_submit(self, interaction: discord.Interaction):
            self.view.top_text = self.top_text.value.replace(" ", "_").replace("/", "-")
            self.view.bottom_text = self.bottom_text.value.replace(" ", "_").replace("/", "-") if self.bottom_text.value else "_"
            await self.view.update_embed(interaction)

    class ConfirmView(discord.ui.View):
        def __init__(self, cog, ctx, meme_embed):
            super().__init__(timeout=30)
            self.cog = cog
            self.ctx = ctx
            self.meme_embed = meme_embed
            self.confirmed = False

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji="✅")
        async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = True
            await self.ctx.send(embed=self.meme_embed)
            await interaction.response.edit_message(embed=self.cog.create_embed(
                "🖼️ Meme Posted",
                f"{interaction.user.mention}, your meme has been posted!",
                color=discord.Color.green()
            ), view=None)
            self.stop()

        @discord.ui.button(label="No", style=discord.ButtonStyle.red, emoji="❌")
        async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(embed=self.cog.create_embed(
                "🖼️ Meme Discarded",
                f"{interaction.user.mention}, your meme was not posted.",
                color=discord.Color.orange()
            ), view=None)
            self.stop()

        async def on_timeout(self):
            if not self.confirmed:
                await self.ctx.send(f"{self.ctx.author.mention}, preview timed out—no meme posted.", delete_after=10)
            if self.message:
                await self.message.edit(embed=self.cog.create_embed(
                    "⏳ Preview Timed Out",
                    f"{self.ctx.author.mention}, you didn’t confirm in time!",
                    color=discord.Color.orange()
                ), view=None)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user == self.ctx.author

    class MemeView(discord.ui.View):
        def __init__(self, cog, ctx):
            super().__init__(timeout=60)
            self.cog = cog
            self.ctx = ctx
            self.template = "drake"  # Default to drake
            self.top_text = None
            self.bottom_text = None
            self.font = "impact"
            self.preview = False
            self.message = None
            self.font_index = 0
            self.template_index = 0

        async def update_embed(self, interaction):
            """Update the embed with current selections."""
            desc = (
                f"**Template:** {self.template}\n"
                f"**Top Text:** {self.top_text.replace('_', ' ') if self.top_text else 'Not set'}\n"
                f"**Bottom Text:** {self.bottom_text.replace('_', ' ') if self.bottom_text and self.bottom_text != '_' else 'None'}\n"
                f"**Font:** {self.font.capitalize()}\n"
                f"**Preview:** {'Yes' if self.preview else 'No'}"
            )
            embed = self.cog.create_embed(
                "🖼️ Meme Generator",
                desc,
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Template: Drake", style=discord.ButtonStyle.secondary, emoji="😏", row=0)
        async def toggle_template(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.template_index = (self.template_index + 1) % len(self.cog.popular_templates)
            self.template = self.cog.popular_templates[self.template_index]
            button.label = f"Template: {self.template.capitalize()}"
            await self.update_embed(interaction)

        @discord.ui.button(label="Preview: Off", style=discord.ButtonStyle.grey, emoji="👀", row=0)
        async def toggle_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.preview = not self.preview
            button.label = f"Preview: {'On' if self.preview else 'Off'}"
            await self.update_embed(interaction)

        @discord.ui.button(label="Set Text", style=discord.ButtonStyle.primary, emoji="📝", row=1)
        async def set_text(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(self.cog.TextModal(self))

        @discord.ui.button(label="Font: Impact", style=discord.ButtonStyle.grey, emoji="🔤", row=1)
        async def toggle_font(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.font_index = (self.font_index + 1) % len(self.cog.fonts)
            self.font = self.cog.fonts[self.font_index]
            button.label = f"Font: {self.font.capitalize()}"
            await self.update_embed(interaction)

        @discord.ui.button(label="Generate", style=discord.ButtonStyle.green, emoji="✅", row=2)
        async def generate(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.template or not self.top_text:
                embed = self.cog.create_embed(
                    "❌ Incomplete Meme",
                    "Please set a template and top text before generating!",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)
                self.stop()
                return

            meme_url = f"{self.cog.base_url}/{self.template}/{self.top_text}/{self.bottom_text}.jpg?font={self.font}"
            async with aiohttp.ClientSession() as session:
                async with session.get(meme_url) as resp:
                    if resp.status != 200:
                        try:
                            response_text = await resp.text()
                        except UnicodeDecodeError:
                            response_text = "Unable to decode response (binary data)"
                        embed = self.cog.create_embed(
                            "❌ Meme Generation Failed",
                            f"Failed to generate meme with template '{self.template}'. Status: {resp.status}\nResponse: {response_text[:100]}...\nTry again or check template validity at {self.cog.api_templates_url}",
                            color=discord.Color.red()
                        )
                        await interaction.response.edit_message(embed=embed, view=None)
                        self.stop()
                        return

            embed = self.cog.create_embed(
                "🖼️ Your Custom Meme",
                f"Created by {interaction.user.mention}",
                color=discord.Color.blue(),
                image_url=meme_url,
                fields=[
                    ("Template", self.template),
                    ("Top Text", self.top_text.replace("_", " ")),
                    ("Bottom Text", self.bottom_text.replace("_", " ") if self.bottom_text != "_" else "None"),
                    ("Font", self.font.capitalize())
                ]
            )

            if self.preview and self.ctx.guild:
                await interaction.user.send(embed=embed)
                confirm_embed = self.cog.create_embed(
                    "🖼️ Preview Sent",
                    f"{interaction.user.mention}, check your DMs for a preview! Confirm below:",
                    color=discord.Color.blue()
                )
                confirm_view = self.cog.ConfirmView(self.cog, self.ctx, embed)
                await interaction.response.edit_message(embed=confirm_embed, view=confirm_view)
                confirm_view.message = interaction.message
                await confirm_view.wait()
            else:
                await interaction.response.edit_message(embed=embed, view=None)
            self.stop()

        @discord.ui.button(label="Discard", style=discord.ButtonStyle.red, emoji="🗑️", row=2)
        async def discard(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = self.cog.create_embed(
                "🖼️ Meme Creation Discarded",
                f"{interaction.user.mention}, your meme creation session has been discarded.",
                color=discord.Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()

        async def on_timeout(self):
            """Handle timeout by disabling buttons."""
            if self.message:
                for item in self.children:
                    item.disabled = True
                embed = self.cog.create_embed(
                    "⏳ Meme Generator Timed Out",
                    f"Session expired. Use `{BOT_PREFIX}creatememe` to start again!",
                    color=discord.Color.orange()
                )
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.NotFound:
                    pass

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user == self.ctx.author

    @commands.command(name="creatememe")
    async def create_meme(self, ctx, template: str = None):
        """Start the meme creation process with an optional template."""
        view = self.MemeView(self, ctx)
        if template:
            view.template = template.lower()
            view.template_index = self.popular_templates.index(template.lower()) if template.lower() in self.popular_templates else 0
        embed = self.create_embed(
            "🖼️ Meme Generator",
            f"**Template:** {view.template}\n"
            f"**Top Text:** {view.top_text or 'Not set'}\n"
            f"**Bottom Text:** {'None' if not view.bottom_text else view.bottom_text}\n"
            f"**Font:** {view.font.capitalize()}\n"
            f"**Preview:** {'Yes' if view.preview else 'No'}\n\n"
            "Click buttons below to customize your meme!",
            color=discord.Color.blue()
        )
        view.message = await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(MemeGen(bot))

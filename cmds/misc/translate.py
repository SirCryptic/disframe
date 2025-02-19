import discord
from discord.ext import commands
from googletrans import Translator
import config

class Translate(commands.Cog):
    """Translation commands."""

    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()  # Initialize the Google Translator

    @commands.command(name='translate')
    async def translate(self, ctx, lang: str = None, *, text: str = None):
        """Translate text into a specified language."""
        if not lang or not text:
            # Show help if no arguments are provided
            embed = discord.Embed(
                title="🌐 Translate Command Help",
                description="Translate text into a specified language.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🔎 Command Usage",
                value=f"Use `{config.BOT_PREFIX}translate <language_code> <text>` to translate.\nExample: `{config.BOT_PREFIX}translate es Hello, how are you?`",
                inline=False
            )
            embed.add_field(
                name="ℹ️ Language Codes",
                value="[Supported Languages](https://cloud.google.com/translate/docs/languages)",
                inline=False
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
            return

        try:
            # Perform the translation synchronously
            translation = self.translator.translate(text, dest=lang)

            # Create an embed for the translation result
            embed = discord.Embed(
                title="🌐 Translation Result",
                color=discord.Color.blue()
            )
            embed.add_field(name="📥 Original Text", value=text, inline=False)
            embed.add_field(name="📤 Translated Text", value=translation.text, inline=False)
            embed.add_field(name="🌍 Language", value=f"Translated to {lang.upper()}", inline=False)
            embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Result Powered by Google Translate",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

        except Exception as e:
            # Handle errors gracefully
            await ctx.send(f"Error: {e}")

async def setup(bot):
    await bot.add_cog(Translate(bot))

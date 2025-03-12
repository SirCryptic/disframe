import discord
from discord.ext import commands
import config
from config import BOT_PREFIX
import random
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
import os
import datetime
import base64

class GuessGame(commands.Cog):
    """A cog for a Guess the Number game with text feedback, supporting multiplayer in guilds and solo in DMs."""

    def __init__(self, bot):
        self.bot = bot
        self.base_image_path = os.path.join("assets", "images", "guess_base.jpg")
        self.font_path = os.path.join("assets", "fonts", "impact.ttf")
        self.games = {}  # Store active games: {(guild_id, channel_id/user_id): secret_number}
        self.easter_egg_encoded = "VGhlIEFuc3dlciBpcyA0MiEgLSBCeSBTaXJDcnlwdGlj"

    def _load_base_image(self):
        """Load the base image for guesses, with a fallback if missing."""
        try:
            if not os.path.exists(self.base_image_path):
                return Image.new("RGBA", (600, 400), (100, 100, 100, 255))  # Gray background
            return Image.open(self.base_image_path).convert("RGBA")
        except Exception:
            return Image.new("RGBA", (600, 400), (100, 100, 100, 255))

    def create_embed(self, title, description, color=discord.Color.blue(), image_file=None):
        """Helper method for clean embeds."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        if image_file:
            embed.set_image(url=f"attachment://{image_file.filename}")
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed

    async def generate_feedback_image(self, message):
        """Generate an image with a feedback message using impact.ttf."""
        try:
            img = self._load_base_image()
            draw = ImageDraw.Draw(img)

            # Use impact.ttf with fallback to default
            font_size = 60
            try:
                if not os.path.exists(self.font_path):
                    font = ImageFont.truetype("arial.ttf", font_size)
                else:
                    font = ImageFont.truetype(self.font_path, font_size)
            except Exception:
                font = ImageFont.load_default()
                font_size = 40

            text_color = (255, 255, 255)  # White text
            outline_color = (0, 0, 0)  # Black outline

            # Center the text
            text_bbox = draw.textbbox((0, 0), message, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_pos = (img.width // 2 - text_width // 2, img.height // 2 - text_height // 2)

            # Draw outline
            for dx, dy in [(-2, -2), (2, 2), (-2, 2), (2, -2)]:
                draw.text((text_pos[0] + dx, text_pos[1] + dy), message, font=font, fill=outline_color)
            # Draw main text
            draw.text(text_pos, message, font=font, fill=text_color)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return discord.File(buffer, filename="guess_feedback.png")
        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}")

    @commands.command(name="guess")
    async def guess_number(self, ctx, guess: int = None):
        """Play a Guess the Number game. Usage: <prefix>guess <number>"""
        guild_id = ctx.guild.id if ctx.guild else None
        channel_id = ctx.channel.id if ctx.guild else ctx.author.id  # Use user_id for DMs
        game_key = (guild_id, channel_id)

        if guess is None:
            # Start a new game if none exists for this context
            if game_key in self.games:
                if ctx.guild:
                    embed = self.create_embed(
                        "Game Already Started!",
                        f"A game is already running in this channel! Guess with `{BOT_PREFIX}guess <number>`."
                    )
                else:
                    embed = self.create_embed(
                        "Game Already Started!",
                        f"{ctx.author.mention}, you already have a game running! Guess with `{BOT_PREFIX}guess <number>`."
                    )
                await ctx.send(embed=embed)
                return
            self.games[game_key] = random.randint(1, 100)
            if ctx.guild:
                embed = self.create_embed(
                    "Guess the Number!",
                    f"{ctx.author.mention} started a game! I’ve picked a number between 1 and 100. Anyone can guess with `{BOT_PREFIX}guess <number>`!"
                )
            else:
                embed = self.create_embed(
                    "Guess the Number!",
                    f"{ctx.author.mention}, I’ve picked a number between 1 and 100 for you to guess. Start with `{BOT_PREFIX}guess <number>`!"
                )
            await ctx.send(embed=embed)
            return

        if game_key not in self.games:
            if ctx.guild:
                embed = self.create_embed(
                    "No Game Started!",
                    f"No game is running in this channel! Start one with `{BOT_PREFIX}guess`."
                )
            else:
                embed = self.create_embed(
                    "No Game Started!",
                    f"{ctx.author.mention}, you haven’t started a game yet! Use `{BOT_PREFIX}guess` to begin."
                )
            await ctx.send(embed=embed)
            return

        # In DMs, restrict guessing to the initiator
        if not ctx.guild and ctx.author.id != channel_id:
            embed = self.create_embed(
                "Not Your Game!",
                f"{ctx.author.mention}, this game is for someone else! Start your own with `{BOT_PREFIX}guess`."
            )
            await ctx.send(embed=embed)
            return

        secret_number = self.games[game_key]

        if guess < 1 or guess > 100:
            embed = self.create_embed(
                "Invalid Guess!",
                f"{ctx.author.mention}, please guess a number between 1 and 100!"
            )
            await ctx.send(embed=embed)
            return

        async with ctx.typing():
            if guess == 42:  # Easter egg trigger
                easter_egg_message = base64.b64decode(self.easter_egg_encoded).decode('utf-8')
                image = await self.generate_feedback_image("Easter Egg!")
                embed = self.create_embed(
                    "Easter Egg Found!",
                    f"{ctx.author.mention} guessed 42 and found a secret!\n*{easter_egg_message}*",
                    image_file=image
                )
                await ctx.send(embed=embed, file=image)
                if guess == secret_number:
                    image = await self.generate_feedback_image("Winner!")
                    del self.games[game_key]
                    if ctx.guild:
                        embed = self.create_embed(
                            "We Have a Winner!",
                            f"Congratulations, {ctx.author.mention}! You guessed the number {secret_number} correctly! Game over!"
                        )
                    else:
                        embed = self.create_embed(
                            "You Won!",
                            f"Congratulations, {ctx.author.mention}! You guessed the number {secret_number} correctly!"
                        )
                    await ctx.send(embed=embed, file=image)
            elif guess == secret_number:
                image = await self.generate_feedback_image("Winner!")
                del self.games[game_key]
                if ctx.guild:
                    embed = self.create_embed(
                        "We Have a Winner!",
                        f"Congratulations, {ctx.author.mention}! You guessed the number {secret_number} correctly! Game over!",
                        image_file=image
                    )
                else:
                    embed = self.create_embed(
                        "You Won!",
                        f"Congratulations, {ctx.author.mention}! You guessed the number {secret_number} correctly!",
                        image_file=image
                    )
                await ctx.send(embed=embed, file=image)
            elif guess < secret_number:
                image = await self.generate_feedback_image("Too Low!")
                if ctx.guild:
                    embed = self.create_embed(
                        "Too Low!",
                        f"{ctx.author.mention} guessed {guess}, which is too low. Keep guessing!",
                        image_file=image
                    )
                else:
                    embed = self.create_embed(
                        "Too Low!",
                        f"{ctx.author.mention}, your guess of {guess} is too low. Try again!",
                        image_file=image
                    )
                await ctx.send(embed=embed, file=image)
            else:
                image = await self.generate_feedback_image("Too High!")
                if ctx.guild:
                    embed = self.create_embed(
                        "Too High!",
                        f"{ctx.author.mention} guessed {guess}, which is too high. Keep guessing!",
                        image_file=image
                    )
                else:
                    embed = self.create_embed(
                        "Too High!",
                        f"{ctx.author.mention}, your guess of {guess} is too high. Try again!",
                        image_file=image
                    )
                await ctx.send(embed=embed, file=image)

    @guess_number.error
    async def guess_number_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            embed = self.create_embed(
                "❌ Error",
                "Something went wrong while processing your guess. Try again!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    await bot.add_cog(GuessGame(bot))
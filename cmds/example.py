import discord
from discord.ext import commands

class Example(commands.Cog):
    """Example commands for the bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="example")
    async def example_command(self, ctx):
        """An example command."""
        embed = discord.Embed(
            title="Example Command",
            description="This is an example command. Replace it with your own!",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Example(bot))

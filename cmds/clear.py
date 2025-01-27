import discord
from discord.ext import commands
import asyncio  # Required to use sleep for delaying deletion

class Clear(commands.Cog):
    """Commands for moderators."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clear")
    @commands.has_role("mod")  # Only users with the "mod" role can run this command
    async def clear_messages(self, ctx, amount: int = None):
        """
        Clear a specific number of messages (10-100).
        """
        # Delete the user's command message (the one that invoked the command)
        await ctx.message.delete()

        # If amount is not provided, send a usage message and delete after 5 seconds
        if amount is None:
            embed = discord.Embed(
                title="Missing Argument",
                description="Please specify the number of messages you would like to clear (between 10 and 100). Example: !clear 10",
                color=discord.Color.red(),
            )
            error_message = await ctx.send(embed=embed)
            await asyncio.sleep(5)  # Wait for 5 seconds before deleting the error message
            await error_message.delete()
            return

        # Ensure the amount is within the allowed range
        if not 10 <= amount <= 100:
            embed = discord.Embed(
                title="Invalid Amount",
                description="Please specify a number between 10 and 100.",
                color=discord.Color.red(),
            )
            error_message = await ctx.send(embed=embed)
            await asyncio.sleep(5)  # Wait for 5 seconds before deleting the error message
            await error_message.delete()
            return

        # Purge messages
        try:
            deleted = await ctx.channel.purge(limit=amount)
            embed = discord.Embed(
                title="Messages Cleared",
                description=f"{len(deleted)} messages have been deleted.",
                color=discord.Color.green(),
            )
            confirmation = await ctx.send(embed=embed)

            # Wait for 10 seconds before deleting the confirmation message
            await asyncio.sleep(10)
            await confirmation.delete()

        except discord.errors.Forbidden as e:
            # Handle lack of permissions
            embed = discord.Embed(
                title="Permission Denied",
                description="I do not have permission to manage messages in this channel.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

        except discord.errors.HTTPException as e:
            # Handle other HTTP errors
            embed = discord.Embed(
                title="Command Error",
                description="An error occurred while trying to clear messages.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            print(f"[ERROR] HTTP Error: {e}")

    # Error handling for missing role
    @clear_messages.error
    async def clear_messages_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            embed = discord.Embed(
                title="Permission Denied",
                description="You need the 'mod' role to use this command.",
                color=discord.Color.red(),
            )
            error_message = await ctx.send(embed=embed)
            await asyncio.sleep(5)  # Wait for 5 seconds before deleting the error message
            await error_message.delete()

# The setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(Clear(bot))

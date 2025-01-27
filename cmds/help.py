import discord
from discord.ext import commands
import config
from config import BOT_VERSION, BOT_NAME, BOT_PREFIX
import asyncio

class Help(commands.Cog):
    """Custom help command with organized sections for General, Mod, and Dev commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def custom_help(self, ctx):
        """Display the help menu with organized sections."""
        
        # Page 1: General Commands
        general_embed = discord.Embed(
            title="Help Menu (Page 1/3) - General Commands",
            description="The following commands are available for everyone:",
            color=discord.Color.blue(),
        )
        general_embed.add_field(name=f"```{BOT_PREFIX}example```", value="An example command.", inline=False)
        general_embed.add_field(name=f"```{BOT_PREFIX}info```", value="Displays Information About The Bot.", inline=False)
        general_embed.add_field(name=f"```{BOT_PREFIX}serverinfo```", value="Displays Information About The Server.", inline=False)
        general_embed.add_field(name=f"```{BOT_PREFIX}profile <@/ID>```", value="Fetch OSINT profile information of a Discord user (from the server or globally).", inline=False)

        # Page 2: Mod Commands
        mod_embed = discord.Embed(
            title="Help Menu (Page 2/3) - Mod Commands",
            description="The following commands are available for moderators:",
            color=discord.Color.blue(),
        )
        mod_embed.add_field(name=f"```{BOT_PREFIX}clear <amount>```", value="Clear messages (10-100). [Mod Only]", inline=False)

        # Page 3: Dev Commands
        dev_embed = discord.Embed(
            title="Help Menu (Page 3/3) - Dev Commands",
            description="The following commands are available for developers only:",
            color=discord.Color.blue(),
        )
        dev_embed.add_field(name=f"```{BOT_PREFIX}lock```", value="Lock the bot to dev users only.", inline=False)
        dev_embed.add_field(name=f"```{BOT_PREFIX}unlock```", value="Unlock the bot to all users.", inline=False)

        # Get the user from the OWNER_ID stored in config.py and fetch their Discord profile dynamically
        owner = await self.bot.fetch_user(config.OWNER_ID)  # Fetch user based on the stored ID
        
        # Set the footer dynamically using the BOT_NAME and BOT_VERSION
        footer_text = f"{BOT_NAME} - Beta v{BOT_VERSION} - developed by {owner.name}"

        # Set the footer for each embed
        general_embed.set_footer(text=footer_text)
        mod_embed.set_footer(text=footer_text)
        dev_embed.set_footer(text=footer_text)

        # Send the first embed (general commands) and allow navigation to other pages
        help_message = await ctx.send(embed=general_embed)

        # Add reactions to navigate between pages (using text-based emoji names)
        await help_message.add_reaction("◀️")  # Back (Left Arrow)
        await help_message.add_reaction("▶️")  # Next (Right Arrow)

        # Define a check for the reactions
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == help_message.id

        # Navigate through pages based on reactions
        current_page = 1
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)

                if str(reaction.emoji) == "▶️" and current_page < 3:
                    current_page += 1
                    if current_page == 2:
                        await help_message.edit(embed=mod_embed)
                    elif current_page == 3:
                        await help_message.edit(embed=dev_embed)
                    await help_message.remove_reaction("▶️", user)
                elif str(reaction.emoji) == "◀️" and current_page > 1:
                    current_page -= 1
                    if current_page == 1:
                        await help_message.edit(embed=general_embed)
                    elif current_page == 2:
                        await help_message.edit(embed=mod_embed)
                    await help_message.remove_reaction("◀️", user)

            except asyncio.TimeoutError:
                # Stop if the user doesn't react in time
                await help_message.clear_reactions()
                break

# Setup function to add the Help cog
async def setup(bot):
    await bot.add_cog(Help(bot))

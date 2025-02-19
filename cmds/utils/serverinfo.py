import discord
from discord.ext import commands
import config

class ServerInfo(commands.Cog):
    """Server information commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """Displays server information."""
        
        # Prevent the command from being used in DMs
        if isinstance(ctx.channel, discord.DMChannel):
            error_embed = discord.Embed(
                title="❌ Error",
                description="This command cannot be used in DMs. Please use it in a server I have access to.",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)
            return

        try:
            # Get the guild (server) information
            guild = ctx.guild

            # Attempt to get the owner directly from the guild
            owner_tag = "Owner not found"
            owner_id = "N/A"
            if guild.owner:  # If the bot has cached the owner info
                owner_tag = f"{guild.owner.name}#{guild.owner.discriminator}"
                owner_id = str(guild.owner.id)
            else:
                # Manually fetch the owner if it isn't cached
                try:
                    owner = await guild.fetch_member(guild.owner_id)
                    owner_tag = f"{owner.name}#{owner.discriminator}"
                    owner_id = str(owner.id)
                except discord.NotFound:
                    owner_tag = "Owner not found"
                    owner_id = "N/A"
                except discord.Forbidden:
                    owner_tag = "Owner accessible"
                    owner_id = "N/A"
                except Exception as e:
                    owner_tag = "Error fetching owner"
                    owner_id = "N/A"
                    print(f"Error fetching owner: {e}")

            # Gather member data
            members = guild.members

            # Create an embed with server information
            embed = discord.Embed(
                title="🏰 Server Info",
                color=discord.Color.blue()
            )

            # Owner Information (Name & ID)
            embed.add_field(name="👑 Owner Tag", value=owner_tag, inline=True)
            embed.add_field(name="🆔 Owner ID", value=owner_id, inline=True)

            # Basic Server Info
            embed.add_field(name="🏷 Server Name", value=f"{guild.name} | {guild.id}", inline=True)
            embed.add_field(name="🌐 Server Locale", value=guild.preferred_locale, inline=True)

            # Member and Channel Information
            embed.add_field(name="👥 Member Count", value=str(len(members)), inline=True)

            # Channel Count (text + voice channels)
            channel_count = len([c for c in guild.channels if isinstance(c, discord.TextChannel) or isinstance(c, discord.VoiceChannel)])
            embed.add_field(name="🔊 Channel Count", value=str(channel_count), inline=True)

            # Role Count (excluding @everyone role)
            role_count = len([r for r in guild.roles if r.name != "@everyone"])  # Exclude @everyone role
            embed.add_field(name="🔧 Role Count", value=str(role_count), inline=True)

            # Bots vs Humans
            embed.add_field(name="🧑 Humans", value=str(len([m for m in members if not m.bot])), inline=True)
            embed.add_field(name="🤖 Bots", value=str(len([m for m in members if m.bot])), inline=True)

            embed.add_field(name="📅 Server Created On", value=str(guild.created_at.strftime('%d.%m.%Y')), inline=True)

            # Verification Level
            embed.add_field(name="🔐 Server Verification Level", value=str(guild.verification_level), inline=True)

            embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )

            # Server Icon (with fallback for servers without an icon)
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            else:
                embed.set_thumbnail(url="https://user-images.githubusercontent.com/48811414/219992613-de266069-beaa-4071-ac2c-8b563fb441ac.png")

            # Send the embed
            await ctx.send(embed=embed)
            print(f"ServerInfo requested by {ctx.author} in {guild.name}")

        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ Error",
                description=f"An error occurred: {e}",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)
            print(f"Error executing serverinfo command: {e}")

# The setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
import discord
from discord.ext import commands
from typing import List
import config
from datetime import datetime

class ServerInfo(commands.Cog):
    """Enhanced server information commands with accurate member status breakdown."""

    def __init__(self, bot):
        self.bot = bot

    async def get_owner_info(self, guild: discord.Guild) -> tuple[str, str]:
        """Fetch server owner information with fallback."""
        owner_tag = "Unknown"
        owner_id = "N/A"
        if guild.owner:
            owner_tag = f"{guild.owner.name}#{guild.owner.discriminator}"
            owner_id = str(guild.owner.id)
        else:
            try:
                owner = await guild.fetch_member(guild.owner_id)
                owner_tag = f"{owner.name}#{owner.discriminator}"
                owner_id = str(owner.id)
            except (discord.NotFound, discord.Forbidden):
                owner_tag = "Unknown (Permissions Issue)"
            except Exception as e:
                owner_tag = f"Error: {str(e)}"
        return owner_tag, owner_id

    async def gather_member_stats(self, members: List[discord.Member]) -> dict[str, dict[str, int]]:
        """Calculate member statistics with detailed status breakdown."""
        stats = {
            "humans": {"total": 0, "online": 0, "idle": 0, "dnd": 0, "offline": 0},
            "bots": {"total": 0, "online": 0, "idle": 0, "dnd": 0, "offline": 0}
        }
        for member in members:
            if member.bot:
                stats["bots"]["total"] += 1
                if member.status == discord.Status.online:
                    stats["bots"]["online"] += 1
                elif member.status == discord.Status.idle:
                    stats["bots"]["idle"] += 1
                elif member.status == discord.Status.dnd:
                    stats["bots"]["dnd"] += 1
                elif member.status == discord.Status.offline:
                    stats["bots"]["offline"] += 1
            else:
                stats["humans"]["total"] += 1
                if member.status == discord.Status.online:
                    stats["humans"]["online"] += 1
                elif member.status == discord.Status.idle:
                    stats["humans"]["idle"] += 1
                elif member.status == discord.Status.dnd:
                    stats["humans"]["dnd"] += 1
                elif member.status == discord.Status.offline:
                    stats["humans"]["offline"] += 1
        return stats

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """Displays detailed server information with member status breakdown."""
        if isinstance(ctx.channel, discord.DMChannel):
            error_embed = discord.Embed(
                title="❌ Error",
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)
            return

        guild = ctx.guild
        embed = discord.Embed(
            title=f"🏰 {guild.name} Server Info",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        try:
            # Check for Presence Intent and member data
            if not self.bot.intents.presences:
                embed.add_field(
                    name="⚠️ Warning",
                    value="Presence Intent is disabled. All statuses will show as offline. Enable it in the bot’s code and Discord Developer Portal.",
                    inline=False
                )
            if not self.bot.intents.members:
                embed.add_field(
                    name="⚠️ Warning",
                    value="Server Members Intent is disabled. Member counts may be incomplete.",
                    inline=False
                )

            # Force chunking if intents are enabled but data is incomplete
            if self.bot.intents.members and len(guild.members) < guild.member_count:
                try:
                    await guild.chunk()  # Fetch all member data
                except discord.Forbidden:
                    embed.add_field(
                        name="⚠️ Note",
                        value="Could not fetch all members due to missing permissions.",
                        inline=False
                    )

            # Owner Info
            owner_tag, owner_id = await self.get_owner_info(guild)
            embed.add_field(name="👑 Owner", value=f"{owner_tag} (`{owner_id}`)", inline=False)

            # Server Stats
            embed.add_field(name="🆔 Server ID", value=str(guild.id), inline=True)
            embed.add_field(name="🌐 Locale", value=guild.preferred_locale or "Unknown", inline=True)
            embed.add_field(name="📅 Created", value=guild.created_at.strftime('%d.%m.%Y'), inline=True)
            embed.add_field(name="🔐 Verification", value=str(guild.verification_level), inline=True)

            # Boost Info
            boost_level = f"Tier {guild.premium_tier} ({guild.premium_subscription_count} Boosts)"
            embed.add_field(name="🚀 Boost Status", value=boost_level, inline=True)

            # Channel and Role Counts
            text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
            voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
            embed.add_field(name="📝 Text Channels", value=str(text_channels), inline=True)
            embed.add_field(name="🎙 Voice Channels", value=str(voice_channels), inline=True)
            embed.add_field(name="🔧 Roles", value=str(len(guild.roles) - 1), inline=True)  # Exclude @everyone

            # Member Stats with Status Breakdown
            member_stats = await self.gather_member_stats(guild.members)
            total_members = member_stats["humans"]["total"] + member_stats["bots"]["total"]
            embed.add_field(name="👥 Total Members", value=str(total_members), inline=True)
            embed.add_field(
                name="🧑 Humans",
                value=(
                    f"{member_stats['humans']['total']}\n"
                    f"🟢 {member_stats['humans']['online']} | 🟡 {member_stats['humans']['idle']} | 🔴 {member_stats['humans']['dnd']} | ⚫ {member_stats['humans']['offline']}"
                ),
                inline=True
            )
            embed.add_field(
                name="🤖 Bots",
                value=(
                    f"{member_stats['bots']['total']}\n"
                    f"🟢 {member_stats['bots']['online']} | 🟡 {member_stats['bots']['idle']} | 🔴 {member_stats['bots']['dnd']} | ⚫ {member_stats['bots']['offline']}"
                ),
                inline=True
            )

            # Vanity URL (if available)
            if guild.vanity_url_code:
                embed.add_field(name="🌐 Vanity URL", value=f"discord.gg/{guild.vanity_url_code}", inline=False)

            # Visuals
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            if guild.banner:
                embed.set_image(url=guild.banner.url)
            elif guild.splash:
                embed.set_image(url=guild.splash.url)

            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ Error",
                description=f"Failed to retrieve server info: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))

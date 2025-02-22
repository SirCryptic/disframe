import discord
from discord.ext import commands
from typing import List
import config
from datetime import datetime

class ServerInfo(commands.Cog):
    """Enhanced server information commands."""

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

    async def gather_member_stats(self, members: List[discord.Member]) -> dict[str, int]:
        """Calculate member statistics in a single pass."""
        stats = {
            "total": len(members),
            "humans": 0,
            "bots": 0,
            "online": 0,
            "offline": 0
        }
        for member in members:
            if member.bot:
                stats["bots"] += 1
            else:
                stats["humans"] += 1
                if member.status != discord.Status.offline:
                    stats["online"] += 1
                else:
                    stats["offline"] += 1
        return stats

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """Displays detailed server information."""
        if not ctx.guild or isinstance(ctx.channel, discord.DMChannel):
            error_embed = discord.Embed(
                title="❌ Error",
                description="This command can only be used in a server where I have access.",
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
            # Owner Info
            owner_tag, owner_id = await self.get_owner_info(guild)
            embed.add_field(
                name="👑 Owner",
                value=f"{owner_tag} (`{owner_id}`)",
                inline=False
            )

            # Server Stats Section
            embed.add_field(
                name="🆔 Server ID",
                value=str(guild.id),
                inline=True
            )
            embed.add_field(
                name="🌐 Locale",
                value=guild.preferred_locale or "Unknown",
                inline=True
            )
            embed.add_field(
                name="📅 Created",
                value=guild.created_at.strftime('%d.%m.%Y'),
                inline=True
            )
            embed.add_field(
                name="🔐 Verification",
                value=str(guild.verification_level).title(),
                inline=True
            )
            boost_level = f"Tier {guild.premium_tier} ({guild.premium_subscription_count} Boosts)"
            embed.add_field(
                name="🚀 Boost Status",
                value=boost_level,
                inline=True
            )
            features = ", ".join(guild.features) if guild.features else "None"
            embed.add_field(
                name="✨ Features",
                value=features,
                inline=True
            )

            # Channel and Role Counts
            text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
            voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
            embed.add_field(
                name="\n📊 Channel & Role Stats",
                value=f"📝 Text: {text_channels}\n🎙 Voice: {voice_channels}\n🔧 Roles: {len(guild.roles) - 1}",  # Exclude @everyone
                inline=False
            )

            # Member Stats
            member_stats = await self.gather_member_stats(guild.members)
            embed.add_field(
                name="👥 Member Stats",
                value=(
                    f"Total: {member_stats['total']}\n"
                    f"🧑 Humans: {member_stats['humans']} ({member_stats['online']} Online, {member_stats['offline']} Offline)\n"
                    f"🤖 Bots: {member_stats['bots']}"
                ),
                inline=False
            )

            # Additional Info
            if guild.vanity_url_code:
                embed.add_field(
                    name="🌐 Vanity URL",
                    value=f"[discord.gg/{guild.vanity_url_code}](https://discord.gg/{guild.vanity_url_code})",
                    inline=False
                )
            emoji_count = len(guild.emojis)
            if emoji_count > 0:
                embed.add_field(
                    name="😺 Custom Emojis",
                    value=str(emoji_count),
                    inline=True
                )

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

        except discord.Forbidden:
            error_embed = discord.Embed(
                title="⚠️ Permission Error",
                description="I lack the necessary permissions to retrieve full server info (e.g., fetch members).",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | By {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)
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

import discord
from discord.ext import commands
import config
from typing import List
import traceback

class BugReport(commands.Cog):
    """Handles bug report submissions with enable/disable functionality and error handling."""

    def __init__(self, bot):
        self.bot = bot
        self.enabled = True  # Default to enabled

    @commands.command(name="bugreport", aliases=["bug", "reportbug"])
    async def bug_report(self, ctx, *, description: str = None):
        """Submit a bug report with a description."""
        
        if not self.enabled:
            await self._disabled_notice(ctx)
            return
        
        if description is None:
            await self._explain_usage(ctx)
            return

        try:
            # Create an embed for the bug report
            report_embed = discord.Embed(
                title="🐛 Bug Report",
                color=discord.Color.red()
            )
            report_embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.avatar.url)
            report_embed.add_field(name="Description", value=description, inline=False)
            report_embed.add_field(name="Reported By", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)

            # Handle guild information or DM context
            if ctx.guild:
                report_embed.add_field(name="Server", value=ctx.guild.name, inline=False)
                report_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
            else:
                report_embed.add_field(name="Context", value="Direct Message", inline=False)

            report_embed.timestamp = discord.utils.utcnow()

            # Send the report to developers
            success_count = await self._send_to_developers(report_embed, ctx)

            # Confirmation message to the user
            if success_count > 0:
                confirmation_embed = discord.Embed(
                    title="Bug Report Submitted",
                    description=f"Your bug report has been sent to {success_count} developer(s). Thanks for helping us improve!",
                    color=discord.Color.green()
                )
            else:
                confirmation_embed = discord.Embed(
                    title="Error Submitting Bug Report",
                    description="There was an issue sending your bug report. Please try again later or contact a server admin.",
                    color=discord.Color.red()
                )
            await ctx.send(embed=confirmation_embed)

        except discord.errors.HTTPException as e:
            # Handle Discord API errors
            error_embed = discord.Embed(
                title="Error Sending Bug Report",
                description=f"An error occurred while submitting the bug report: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            # Handle all other exceptions
            print(f"Unexpected error in bug_report: {e}")
            print(traceback.format_exc())
            error_embed = discord.Embed(
                title="Unexpected Error",
                description="An unexpected error occurred while processing your bug report. Please try again later.",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=error_embed)

    @commands.command(name="bugreportenable")
    @commands.is_owner()
    async def bugreport_enable(self, ctx):
        """Enable bug reporting."""
        try:
            self.enabled = True
            embed = discord.Embed(
                title="Bug Reporting Enabled",
                description="Bug reporting has been enabled.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.errors.HTTPException as e:
            print(f"Error enabling bug reporting: {e}")

    @commands.command(name="bugreportdisable")
    @commands.is_owner()
    async def bugreport_disable(self, ctx):
        """Disable bug reporting."""
        try:
            self.enabled = False
            embed = discord.Embed(
                title="Bug Reporting Disabled",
                description="Bug reporting has been disabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.errors.HTTPException as e:
            print(f"Error disabling bug reporting: {e}")

    async def _send_to_developers(self, embed: discord.Embed, ctx: commands.Context) -> int:
        """Send the bug report to all developers and return the count of successful sends."""
        success_count = 0
        for dev_id in config.DEV_IDS:
            try:
                developer = await self.bot.fetch_user(dev_id)
                await developer.send(embed=embed)
                success_count += 1
            except discord.errors.HTTPException as e:
                print(f"Error sending bug report to developer {dev_id}: {e}")
            except discord.errors.NotFound:
                print(f"Developer with ID {dev_id} not found.")
        return success_count

    async def _explain_usage(self, ctx):
        """Explain how to use the bug report command."""
        try:
            embed = discord.Embed(
                title="🐛 Bug Report Help",
                description="**Bug Report Command** - Submit a bug report to the developers.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🔎 Command Usage",
                value=f"Use `{config.BOT_PREFIX}bugreport <description>` to submit a bug report.\nExample: `{config.BOT_PREFIX}bugreport The mute command isn't working in voice channels.`",
                inline=False
            )
            embed.add_field(
                name="📝 Description Tips",
                value="- Be specific about the issue you're encountering.\n- Include any error messages if visible.\n- Mention steps to reproduce if possible.\n- Keep the description concise but informative.",
                inline=False
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} - v{config.BOT_VERSION} - Developed by {self.bot.get_user(config.OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
        except discord.errors.HTTPException as e:
            print(f"Error sending usage help: {e}")

    async def _disabled_notice(self, ctx):
        """Notify users that bug reporting is disabled."""
        try:
            embed = discord.Embed(
                title="Bug Reporting Disabled",
                description="Bug reporting is currently disabled. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.errors.HTTPException as e:
            print(f"Error sending disabled notice: {e}")

async def setup(bot):
    await bot.add_cog(BugReport(bot))
import discord
from discord.ext import commands
import asyncio
import io
import sys
import traceback
import subprocess
import textwrap
from contextlib import redirect_stdout
from typing import Optional, Union
import os
import copy
import psutil
from datetime import datetime

from config import OWNER_ID, DEV_IDS, BOT_PREFIX, BOT_NAME, BOT_VERSION

class Admin(commands.Cog):
    """Enhanced admin-only commands for managing bot functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.allowed_user_ids = [OWNER_ID] + DEV_IDS
        self.start_time = datetime.utcnow()

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Check if the user is an allowed admin."""
        if ctx.author.id not in self.allowed_user_ids:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="This command is restricted to bot owner and developers.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed, delete_after=10)
            return False
        return True

    async def run_process(self, command: str) -> list[str]:
        """Run a shell command asynchronously and return output."""
        process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        return [stdout.decode(), stderr.decode()]

    def cleanup_code(self, content: str) -> str:
        """Clean up code for evaluation."""
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        return content.strip('` \n')

    @commands.command(hidden=True)
    async def load(self, ctx: commands.Context, *, module: str):
        """Load a cog/module."""
        try:
            await self.bot.load_extension(module)
            embed = discord.Embed(
                title="📦 Module Loaded",
                description=f"Successfully loaded `{module}`.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")  # New admin icon
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Load Failed",
                description=f"Failed to load `{module}`.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def unload(self, ctx: commands.Context, *, module: str):
        """Unload a cog/module."""
        try:
            await self.bot.unload_extension(module)
            embed = discord.Embed(
                title="🗑️ Module Unloaded",
                description=f"Successfully unloaded `{module}`.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Unload Failed",
                description=f"Failed to unload `{module}`.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def eval(self, ctx: commands.Context, *, body: str):
        """Evaluate Python code."""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            '_': None,
        }
        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        try:
            exec(to_compile, env)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Eval Error",
                description="Failed to compile code.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            return await ctx.send(embed=embed)

        func = env['func']
        try:
            with redirect_stdout(stdout):
                result = await func()
            value = stdout.getvalue()
            embed = discord.Embed(
                title="🧑‍💻 Eval Result",
                description="Evaluated Python code successfully.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Input", value=f"```py\n{body[:1000]}\n```", inline=False)
            output = value + (str(result) if result is not None else "")
            embed.add_field(name="Output", value=f"```py\n{output[:1000] or 'No output'}\n```", inline=False)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
        except Exception as e:
            value = stdout.getvalue()
            embed = discord.Embed(
                title="❌ Eval Error",
                description="Failed to execute code.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Error", value=f"```py\n{value}{traceback.format_exc()[:1000]}\n```", inline=False)
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def sh(self, ctx: commands.Context, *, command: str):
        """Run a shell command and send the output."""
        async with ctx.typing():
            stdout, stderr = await self.run_process(command)
        embed = discord.Embed(
            title="🖥️ Shell Command",
            description=f"Executed: `{command}`",
            color=discord.Color.green() if not stderr else discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Output", value=f"```bash\n{stdout[:1000] or 'No output'}\n```", inline=False)
        if stderr:
            embed.add_field(name="Error", value=f"```bash\n{stderr[:1000]}\n```", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def sudo(self, ctx: commands.Context, channel: Optional[discord.TextChannel], who: Union[discord.Member, discord.User], *, command: str):
        """Run a command as another user."""
        msg = copy.copy(ctx.message)
        msg.channel = channel or ctx.channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        try:
            await self.bot.invoke(new_ctx)
            embed = discord.Embed(
                title="👤 Sudo Executed",
                description=f"Ran `{command}` as {who.mention} in {new_ctx.channel.mention}.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Sudo Failed",
                description=f"Failed to run `{command}` as {who.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def restart(self, ctx: commands.Context):
        """Restart the bot."""
        embed = discord.Embed(
            title="🔄 Restarting",
            description="Bot is restarting now...",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        await ctx.send(embed=embed)
        await self.bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.command(hidden=True)
    async def reload_all(self, ctx: commands.Context):
        """Reload all modules."""
        embed = discord.Embed(
            title="🔄 Reloading All Modules",
            description="Reloading all cogs in `cmds/`...",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        message = await ctx.send(embed=embed)

        success_count = 0
        errors = []
        for filename in os.listdir('./cmds'):
            if filename.endswith('.py'):
                module = f'cmds.{filename[:-3]}'
                try:
                    await self.bot.reload_extension(module)
                    success_count += 1
                except Exception as e:
                    errors.append(f"`{module}`: {str(e)}")

        embed.description = f"Reloaded {success_count} modules."
        if errors:
            embed.add_field(name="Errors", value="\n".join(errors[:5]), inline=False)
            embed.color = discord.Color.red()
        else:
            embed.color = discord.Color.green()
        await message.edit(embed=embed)

    @commands.command(hidden=True)
    async def reload(self, ctx: commands.Context, *, module: str):
        """Reload a specific module."""
        try:
            await self.bot.reload_extension(module)
            embed = discord.Embed(
                title="🔄 Module Reloaded",
                description=f"Successfully reloaded `{module}`.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Failed to reload `{module}`.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def extensions(self, ctx: commands.Context):
        """List all loaded extensions."""
        embed = discord.Embed(
            title="📋 Loaded Extensions",
            description=f"Currently loaded cogs ({len(self.bot.extensions)}):",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="Extensions",
            value="\n".join([f"`{ext}`" for ext in self.bot.extensions.keys()]) or "None",
            inline=False
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def botstatus(self, ctx: commands.Context):
        """Show bot status including uptime and resource usage."""
        uptime = datetime.utcnow() - self.start_time
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 ** 2  # Convert to MB
        cpu_usage = psutil.cpu_percent(interval=0.5)

        embed = discord.Embed(
            title="📊 Bot Status",
            description=f"Current status of {BOT_NAME}:",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=True)
        embed.add_field(name="Memory Usage", value=f"{memory_usage:.2f} MB", inline=True)
        embed.add_field(name="CPU Usage", value=f"{cpu_usage:.1f}%", inline=True)
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(self.bot.users), inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f} ms", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        await ctx.send(embed=embed)

    @commands.group(name='adminhelp', invoke_without_command=True)
    async def admin_help_group(self, ctx: commands.Context):
        """Display help for admin commands."""
        embed = discord.Embed(
            title="🛡️ Admin Commands",
            description=f"Admin tools for managing {BOT_NAME}:",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name=f"📦 {BOT_PREFIX}load <module>", value="Load a cog/module.", inline=False)
        embed.add_field(name=f"🗑️ {BOT_PREFIX}unload <module>", value="Unload a cog/module.", inline=False)
        embed.add_field(name=f"🔄 {BOT_PREFIX}reload <module>", value="Reload a specific module.", inline=False)
        embed.add_field(name=f"🔄 {BOT_PREFIX}reload_all", value="Reload all modules in `cmds/`.", inline=False)
        embed.add_field(name=f"🧑‍💻 {BOT_PREFIX}eval <code>", value="Evaluate Python code.", inline=False)
        embed.add_field(name=f"🖥️ {BOT_PREFIX}sh <command>", value="Run a shell command.", inline=False)
        embed.add_field(name=f"👤 {BOT_PREFIX}sudo [channel] <user> <command>", value="Run a command as another user.", inline=False)
        embed.add_field(name=f"🔄 {BOT_PREFIX}restart", value="Restart the bot.", inline=False)
        embed.add_field(name=f"📋 {BOT_PREFIX}extensions", value="List all loaded extensions.", inline=False)
        embed.add_field(name=f"📊 {BOT_PREFIX}botstatus", value="Show bot status (uptime, resources).", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name}",
            icon_url=self.bot.user.avatar.url
        )
        try:
            await ctx.author.send(embed=embed)
            if ctx.guild:
                await ctx.message.delete()
        except discord.errors.Forbidden:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))

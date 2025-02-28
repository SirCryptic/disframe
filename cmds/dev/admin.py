import discord
from discord.ext import commands
from discord import ui
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

class PaginatedExtensions(ui.View):
    """A custom view for paginating the extensions list."""
    def __init__(self, extensions: list[str], per_page: int = 10, requester: discord.User = None):
        super().__init__(timeout=60)
        self.extensions = extensions
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(extensions) + per_page - 1) // per_page
        self.requester = requester  # Store the user who requested the UI

    def get_page_content(self) -> str:
        """Get the content for the current page."""
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.extensions[start:end]
        return "\n".join([f"`{ext}`" for ext in page_items]) or "None"

    def update_buttons(self):
        """Update the state of the buttons based on the current page."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed with the current page content."""
        embed = discord.Embed(
            title="📋 Loaded Extensions",
            description=f"Currently loaded cogs ({len(self.extensions)}):",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Extensions", value=self.get_page_content(), inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        owner = interaction.client.get_user(OWNER_ID)
        owner_name = owner.name if owner else "Unknown"
        embed.set_footer(
            text=f"Page {self.current_page + 1}/{self.total_pages} | {BOT_NAME} v{BOT_VERSION} | By {owner_name}",
            icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None
        )
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.requester:
            await interaction.response.send_message("Only the requester can use this UI.", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_embed(interaction)

    @ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.requester:
            await interaction.response.send_message("Only the requester can use this UI.", ephemeral=True)
            return
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_embed(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                embed = self.message.embeds[0]
                embed.set_footer(text=f"Interaction timed out | {BOT_NAME} v{BOT_VERSION}")
                await self.message.edit(embed=embed, view=self)
        except discord.errors.NotFound:
            print(f"Message not found during timeout (ID: {self.message.id if self.message else 'None'})")
        except discord.HTTPException as e:
            print(f"Failed to edit message on timeout: {e}")

class ModuleManager(ui.View):
    """A view for managing bot modules via a dropdown menu with a finish button, restricted to the requester."""
    def __init__(self, bot, ctx: commands.Context):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.requester = ctx.author

    def create_embed(self, title: str, description: str, color: discord.Color, fields: list[tuple[str, str, bool]] = None):
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        owner = self.bot.get_user(OWNER_ID)
        embed.set_footer(
            text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        return embed

    @ui.select(
        placeholder="Choose an action...",
        options=[
            discord.SelectOption(label="Load", description="Load a cog/module", emoji="📦"),
            discord.SelectOption(label="Unload", description="Unload a cog/module", emoji="🗑️"),
            discord.SelectOption(label="Reload", description="Reload a specific module", emoji="🔄"),
            discord.SelectOption(label="Reload All", description="Reload all modules in cmds/", emoji="🔄"),
            discord.SelectOption(label="List Extensions", description="List all loaded extensions", emoji="📋"),
        ]
    )
    async def module_select(self, interaction: discord.Interaction, select: ui.Select):
        if interaction.user != self.requester:
            await interaction.response.send_message("Only the requester can use this UI.", ephemeral=True)
            return
        action = select.values[0]
        await interaction.response.defer()

        if action in ["Load", "Unload", "Reload"]:
            await interaction.followup.send(f"Please provide the module name for '{action}' (e.g., `cmds.example` or `cmds.music.player`). Reply within 30 seconds.", ephemeral=True)
            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel,
                    timeout=30
                )
                module = msg.content.strip()
                if action == "Load":
                    await self.bot.load_extension(module)
                    embed = self.create_embed("📦 Module Loaded", f"Successfully loaded `{module}`.", discord.Color.green())
                elif action == "Unload":
                    await self.bot.unload_extension(module)
                    embed = self.create_embed("🗑️ Module Unloaded", f"Successfully unloaded `{module}`.", discord.Color.green())
                elif action == "Reload":
                    await self.bot.reload_extension(module)
                    embed = self.create_embed("🔄 Module Reloaded", f"Successfully reloaded `{module}`.", discord.Color.green())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Timed out waiting for module name.", ephemeral=True)
            except Exception as e:
                embed = self.create_embed(f"❌ {action} Failed", f"Failed to {action.lower()} `{module}`.", discord.Color.red(), [("Error", str(e), False)])
                await interaction.followup.send(embed=embed, ephemeral=True)

        elif action == "Reload All":
            embed = self.create_embed("🔄 Reloading All Modules", "Reloading all cogs in `cmds/` and subdirectories...", discord.Color.orange())
            message = await interaction.followup.send(embed=embed, ephemeral=True)
            success_count = 0
            errors = []
            cmds_dir = './cmds'
            for root, _, files in os.walk(cmds_dir):
                for filename in files:
                    if filename.endswith('.py') and filename != '__init__.py':
                        relative_path = os.path.relpath(os.path.join(root, filename), cmds_dir)
                        module = f"cmds.{relative_path[:-3].replace(os.sep, '.')}"
                        try:
                            if module in self.bot.extensions:
                                await self.bot.reload_extension(module)
                            else:
                                await self.bot.load_extension(module)
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

        elif action == "List Extensions":
            extensions_list = list(self.bot.extensions.keys())
            if not extensions_list:
                embed = self.create_embed("📋 Loaded Extensions", "No extensions are currently loaded.", discord.Color.blue())
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                view = PaginatedExtensions(extensions_list, per_page=10, requester=self.requester)
                embed = self.create_embed("📋 Loaded Extensions", f"Currently loaded cogs ({len(extensions_list)}):", discord.Color.blue(), [("Extensions", view.get_page_content(), False)])
                embed.set_footer(text=f"Page 1/{view.total_pages} | {BOT_NAME} v{BOT_VERSION} | By {self.bot.get_user(OWNER_ID).name if self.bot.get_user(OWNER_ID) else 'Unknown'}")
                view.message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @ui.button(label="Finish", style=discord.ButtonStyle.red)
    async def finish_button(self, interaction: discord.Interaction, button: ui.Button):
        """Close the module manager UI."""
        if interaction.user != self.requester:
            await interaction.response.send_message("Only the requester can use this UI.", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        embed = self.create_embed(
            "🛠️ Module Manager",
            "Module management session has ended.",
            discord.Color.greyple()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        try:
            if self.message:
                embed = self.message.embeds[0]
                embed.set_footer(text=f"Interaction timed out | {BOT_NAME} v{BOT_VERSION}")
                for item in self.children:
                    item.disabled = True
                await self.message.edit(embed=embed, view=self)
        except discord.errors.NotFound:
            print(f"Message not found during timeout (ID: {self.message.id if self.message else 'None'})")
        except discord.HTTPException as e:
            print(f"Failed to edit message on timeout: {e}")

class Admin(commands.Cog):
    """Enhanced admin-only commands for managing bot functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.allowed_user_ids = [OWNER_ID] + DEV_IDS
        self.start_time = datetime.utcnow()

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.author.id not in self.allowed_user_ids:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="This command is restricted to bot owner and developers.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            owner = self.bot.get_user(OWNER_ID)
            owner_name = owner.name if owner else "Unknown"
            embed.set_footer(
                text=f"{BOT_NAME} v{BOT_VERSION} | By {owner_name}",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )
            try:
                await ctx.send(embed=embed, delete_after=10, ephemeral=True)
            except discord.HTTPException as e:
                print(f"Failed to send access denied message: {e}")
            return False
        return True

    async def run_process(self, command: str) -> list[str]:
        process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        return [stdout.decode(), stderr.decode()]

    def cleanup_code(self, content: str) -> str:
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        return content.strip('` \n')

    @commands.command(hidden=True)
    async def modules(self, ctx: commands.Context):
        """Manage bot modules through an interactive UI."""
        view = ModuleManager(self.bot, ctx)
        embed = view.create_embed(
            "🛠️ Module Manager",
            "Select an action from the dropdown below to manage bot modules.",
            discord.Color.blue()
        )
        view.message = await ctx.send(embed=embed, view=view, ephemeral=True)

    @commands.command(hidden=True)
    async def eval(self, ctx: commands.Context, *, body: str):
        env = {'bot': self.bot, 'ctx': ctx, '_': None}
        body = self.cleanup_code(body)
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        try:
            exec(to_compile, env)
        except Exception as e:
            embed = discord.Embed(title="❌ Eval Error", description="Failed to compile code.", color=discord.Color.red(), timestamp=datetime.utcnow())
            embed.add_field(name="Error", value=str(e), inline=False)
            owner = self.bot.get_user(OWNER_ID)
            embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            return await ctx.send(embed=embed, ephemeral=True)
        func = env['func']
        try:
            with redirect_stdout(stdout):
                result = await func()
            value = stdout.getvalue()
            embed = discord.Embed(title="🧑‍💻 Eval Result", description="Evaluated Python code successfully.", color=discord.Color.green(), timestamp=datetime.utcnow())
            embed.add_field(name="Input", value=f"```py\n{body[:1000]}\n```", inline=False)
            embed.add_field(name="Output", value=f"```py\n{(value + (str(result) if result is not None else ''))[:1000] or 'No output'}\n```", inline=False)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            owner = self.bot.get_user(OWNER_ID)
            embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            await ctx.send(embed=embed, ephemeral=True)
        except Exception as e:
            value = stdout.getvalue()
            embed = discord.Embed(title="❌ Eval Error", description="Failed to execute code.", color=discord.Color.red(), timestamp=datetime.utcnow())
            embed.add_field(name="Error", value=f"```py\n{value}{traceback.format_exc()[:1000]}\n```", inline=False)
            owner = self.bot.get_user(OWNER_ID)
            embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            await ctx.send(embed=embed, ephemeral=True)

    @commands.command(hidden=True)
    async def sh(self, ctx: commands.Context, *, command: str):
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
        owner = self.bot.get_user(OWNER_ID)
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        await ctx.send(embed=embed, ephemeral=True)

    @commands.command(hidden=True)
    async def sudo(self, ctx: commands.Context, channel: Optional[discord.TextChannel], who: Union[discord.Member, discord.User], *, command: str):
        msg = copy.copy(ctx.message)
        msg.channel = channel or ctx.channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        try:
            await self.bot.invoke(new_ctx)
            embed = discord.Embed(title="👤 Sudo Executed", description=f"Ran `{command}` as {who.mention} in {new_ctx.channel.mention}.", color=discord.Color.green(), timestamp=datetime.utcnow())
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            owner = self.bot.get_user(OWNER_ID)
            embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            await ctx.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="❌ Sudo Failed", description=f"Failed to run `{command}` as {who.mention}.", color=discord.Color.red(), timestamp=datetime.utcnow())
            embed.add_field(name="Error", value=str(e), inline=False)
            owner = self.bot.get_user(OWNER_ID)
            embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            await ctx.send(embed=embed, ephemeral=True)

    @commands.command(hidden=True)
    async def restart(self, ctx: commands.Context):
        embed = discord.Embed(title="🔄 Restarting", description="Bot is restarting now...", color=discord.Color.orange(), timestamp=datetime.utcnow())
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        owner = self.bot.get_user(OWNER_ID)
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        await ctx.send(embed=embed, ephemeral=True)
        await self.bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.command(hidden=True)
    async def botstatus(self, ctx: commands.Context):
        uptime = datetime.utcnow() - self.start_time
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 ** 2
        cpu_usage = psutil.cpu_percent(interval=0.5)
        embed = discord.Embed(title="📊 Bot Status", description=f"Current status of {BOT_NAME}:", color=discord.Color.blue(), timestamp=datetime.utcnow())
        embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=True)
        embed.add_field(name="Memory Usage", value=f"{memory_usage:.2f} MB", inline=True)
        embed.add_field(name="CPU Usage", value=f"{cpu_usage:.1f}%", inline=True)
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(self.bot.users), inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f} ms", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        owner = self.bot.get_user(OWNER_ID)
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        await ctx.send(embed=embed, ephemeral=True)

    @commands.group(name='adminhelp', invoke_without_command=True)
    async def admin_help_group(self, ctx: commands.Context):
        embed = discord.Embed(title="🛡️ Admin Commands", description=f"Admin tools for managing {BOT_NAME}:", color=discord.Color.blue(), timestamp=datetime.utcnow())
        embed.add_field(name=f"🛠️ {BOT_PREFIX}modules", value="Manage modules via an interactive UI.", inline=False)
        embed.add_field(name=f"🧑‍💻 {BOT_PREFIX}eval <code>", value="Evaluate Python code.", inline=False)
        embed.add_field(name=f"🖥️ {BOT_PREFIX}sh <command>", value="Run a shell command.", inline=False)
        embed.add_field(name=f"👤 {BOT_PREFIX}sudo [channel] <user> <command>", value="Run a command as another user.", inline=False)
        embed.add_field(name=f"🔄 {BOT_PREFIX}restart", value="Restart the bot.", inline=False)
        embed.add_field(name=f"📊 {BOT_PREFIX}botstatus", value="Show bot status (uptime, resources).", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        owner = self.bot.get_user(OWNER_ID)
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | By {owner.name if owner else 'Unknown'}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        try:
            await ctx.author.send(embed=embed)
            if ctx.guild:
                await ctx.message.delete()
        except discord.errors.Forbidden:
            await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))

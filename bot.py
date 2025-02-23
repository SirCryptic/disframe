import os
import asyncio
import discord
import json
from discord.ext import commands, tasks
from datetime import datetime, UTC
import config
from config import TOKEN, BOT_PREFIX, DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SERVER_INVITE_LINK, ALLOWED_DM, OWNER_ID, DEV_IDS, SUBSCRIPTION_ROLE, BOT_NAME, BOT_VERSION

# Bot configuration with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True

bot = commands.AutoShardedBot(command_prefix=BOT_PREFIX, intents=intents)

# Global bot lock variable
bot_locked = False

# Subscription IDs
SUBSCRIPTION_IDS = []

def load_subscription_ids():
    """Load subscription IDs from data/subscription_ids.json."""
    global SUBSCRIPTION_IDS
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)  # Ensure data folder exists
    subscription_file = os.path.join(data_dir, "subscription_ids.json")
    if os.path.exists(subscription_file):
        with open(subscription_file, "r") as f:
            try:
                data = json.load(f)
                SUBSCRIPTION_IDS = data.get("SUBSCRIPTION_IDS", [])
            except json.JSONDecodeError:
                SUBSCRIPTION_IDS = []
    else:
        SUBSCRIPTION_IDS = []

def save_subscription_ids():
    """Save subscription IDs to data/subscription_ids.json."""
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)  # Ensure data folder exists
    subscription_file = os.path.join(data_dir, "subscription_ids.json")
    data = {"SUBSCRIPTION_IDS": SUBSCRIPTION_IDS}
    with open(subscription_file, "w") as f:
        json.dump(data, f, indent=4)

def get_total_member_count():
    """Calculate total member count across all guilds."""
    return sum(guild.member_count for guild in bot.guilds if guild.member_count is not None)

def get_statuses():
    """List of statuses with guild, member, shard counts, and dynamic DM/lock state."""
    if bot_locked:
        return ["Bot Locked 🔒"]
    guild_count = len(bot.guilds)
    member_count = get_total_member_count()
    shard_count = bot.shard_count or 1
    dm_status = "DMs enabled ✅" if ALLOWED_DM else "DMs disabled ❌"
    return [
        f"{BOT_PREFIX}help for commands! 🤖",
        f"Protecting {guild_count} Servers & {member_count} Users! 🛡️",
        f"Shards: {shard_count} active! ⚙️",
        f"{dm_status} | Serving {member_count} Users!"
    ]

@tasks.loop(minutes=1)
async def change_status():
    """Background task to rotate bot status based on lock and DM settings."""
    try:
        statuses = get_statuses()
        for status in statuses:
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=status))
            if bot_locked:
                await asyncio.sleep(60)
                break
            await asyncio.sleep(60)
    except Exception:
        pass

async def ensure_roles_exist(guild):
    """Ensure required roles exist in the guild."""
    required_roles = [DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SUBSCRIPTION_ROLE]
    existing_roles = {role.name for role in guild.roles}

    for role_name in required_roles:
        if role_name not in existing_roles:
            try:
                await guild.create_role(name=role_name, reason="Required role for bot functionality")
            except discord.Forbidden:
                pass

async def create_subscription_channel(guild):
    """Create a private subscription channel if it doesn’t exist."""
    existing_channel = discord.utils.get(guild.text_channels, name="🔒-subscriptions")
    if not existing_channel:
        emoji = "🔒"
        channel_name = f"{emoji}-subscriptions"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE): discord.PermissionOverwrite(read_messages=True),
        }
        try:
            channel = await guild.create_text_channel(channel_name, overwrites=overwrites, reason="Subscription channel")
            return channel
        except discord.Forbidden:
            return None
    return existing_channel

async def load_commands():
    """Recursively load command files from cmds/ and subdirectories."""
    loaded_cogs = 0
    for root, _, files in os.walk("cmds"):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_name = os.path.join(root, file).replace(os.sep, ".")[:-3]
                try:
                    load_task = bot.load_extension(module_name)
                    if load_task is not None:
                        await load_task
                    loaded_cogs += 1
                except Exception:
                    pass
    print(f"[INFO] Loaded {loaded_cogs} cog(s)")

@bot.event
async def on_ready():
    """Handle bot startup."""
    guilds = len(bot.guilds)
    members = get_total_member_count()
    shards = bot.shard_count or 1
    print(f"[INFO] Logged in as {bot.user} ({bot.user.id}) on {guilds} guild(s) with {shards} shard(s) and {members} members")
    for guild in bot.guilds:
        await ensure_roles_exist(guild)
        await create_subscription_channel(guild)

    bot.remove_command("help")
    await load_commands()
    load_subscription_ids()
    print(f"[INFO] {bot.user} is ready!")
    if not change_status.is_running():
        change_status.start()

@bot.event
async def on_message(message):
    """Handle incoming messages, including DM checks."""
    if message.author.bot:
        return

    # Handle DMs
    if not message.guild and not ALLOWED_DM:
        if message.author.id not in [OWNER_ID] + DEV_IDS + SUBSCRIPTION_IDS:
            embed = discord.Embed(
                title="❌ DMs Not Supported",
                description=f"I can’t process commands in DMs.\nJoin my server: [Click here]({SERVER_INVITE_LINK})\nUse `{BOT_PREFIX}help` there for commands.",
                color=discord.Color.red(),
                timestamp=datetime.now(UTC)
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
            embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
            try:
                await message.author.send(embed=embed)
            except discord.Forbidden:
                pass
            return

    # Process commands
    await bot.process_commands(message)

# Lock & Unlock Commands
@bot.command(name="lock")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def lock(ctx):
    global bot_locked
    if bot_locked:
        embed = discord.Embed(
            title="🔒 Bot Already Locked",
            description="The bot is already in a locked state.",
            color=discord.Color.orange(),
            timestamp=datetime.now(UTC)
        )
    else:
        bot_locked = True
        embed = discord.Embed(
            title="🔒 Bot Locked",
            description="The bot has been locked. Only owner/devs can use commands.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)
    if change_status.is_running():
        change_status.restart()

@bot.command(name="unlock")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def unlock(ctx):
    global bot_locked
    if not bot_locked:
        embed = discord.Embed(
            title="🔓 Bot Already Unlocked",
            description="The bot is already unlocked.",
            color=discord.Color.orange(),
            timestamp=datetime.now(UTC)
        )
    else:
        bot_locked = False
        embed = discord.Embed(
            title="🔓 Bot Unlocked",
            description="The bot has been unlocked. All users can now use commands.",
            color=discord.Color.green(),
            timestamp=datetime.now(UTC)
        )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)
    if change_status.is_running():
        change_status.restart()

@bot.command(name="status")
async def status(ctx):
    embed = discord.Embed(
        title="🔍 Bot Status",
        description=f"The bot is currently **{'locked' if bot_locked else 'unlocked'}**.",
        color=discord.Color.red() if bot_locked else discord.Color.green(),
        timestamp=datetime.now(UTC)
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)

@bot.check
async def global_check(ctx):
    if bot_locked and ctx.author.id not in [OWNER_ID] + DEV_IDS:
        embed = discord.Embed(
            title="🔒 Bot Locked",
            description="The bot is locked. Contact the owner or a dev to unlock it.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        await ctx.send(embed=embed)
        return False
    return True

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    embed = discord.Embed(
        color=discord.Color.red(),
        timestamp=datetime.now(UTC)
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")

    if isinstance(error, commands.MissingRole):
        embed.title = "❌ Missing Role"
        embed.description = f"You need the **{error.missing_role}** role to use this command."
    elif isinstance(error, commands.MissingRequiredArgument):
        embed.title = "❌ Missing Arguments"
        embed.description = f"Missing required argument: `{error.param.name}`"
        embed.add_field(name="Tip", value=f"Use `{BOT_PREFIX}help {ctx.command}` for details.", inline=False)
    elif isinstance(error, commands.CommandNotFound):
        embed.title = "❌ Command Not Found"
        embed.description = f"Command not recognized. Use `{BOT_PREFIX}help` for available commands."
        embed.color = discord.Color.orange()
    elif isinstance(error, commands.CommandInvokeError):
        embed.title = "❌ Command Error"
        embed.description = f"An error occurred while running `{ctx.command}`."
        embed.add_field(name="Details", value=str(error.original)[:1000], inline=False)
    elif isinstance(error, commands.CheckFailure):
        embed.title = "❌ Permission Denied"
        embed.description = "You lack permission to run this command."
    elif isinstance(error, commands.CommandOnCooldown):
        embed.title = "⏳ Cooldown"
        embed.description = f"Try again in `{error.retry_after:.2f}` seconds."
        embed.color = discord.Color.orange()
    else:
        embed.title = "❌ Unexpected Error"
        embed.description = f"An unexpected error occurred in `{ctx.command}`."
        embed.add_field(name="Details", value=str(error)[:1000], inline=False)

    error_message = await ctx.send(embed=embed)
    await asyncio.sleep(10)
    try:
        await error_message.delete()
    except discord.Forbidden:
        pass

# Subscription Role Management Commands
@bot.command(name="add_subscription")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def add_subscription(ctx, user_id: int = None):
    if user_id is None:
        embed = discord.Embed(
            title="📝 Add Subscription",
            description=f"Usage: `{BOT_PREFIX}add_subscription <user_id>`\nExample: `{BOT_PREFIX}add_subscription 1234567890`",
            color=discord.Color.blue(),
            timestamp=datetime.now(UTC)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        await ctx.send(embed=embed)
        return

    if user_id not in SUBSCRIPTION_IDS:
        SUBSCRIPTION_IDS.append(user_id)
        save_subscription_ids()
        assigned = False
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member:
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if role:
                    try:
                        await member.add_roles(role)
                        assigned = True
                        await create_subscription_channel(guild)
                        break
                    except discord.Forbidden:
                        embed = discord.Embed(
                            title="❌ Permission Error",
                            description=f"Cannot assign `{SUBSCRIPTION_ROLE}` in {guild.name}. Ensure I have 'Manage Roles' permission.",
                            color=discord.Color.red(),
                            timestamp=datetime.now(UTC)
                        )
                        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
                        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
                        await ctx.send(embed=embed)
                        return

        embed = discord.Embed(
            title="✅ Subscription Added",
            description=f"User ID `{user_id}` added to subscriptions{' and assigned ' + SUBSCRIPTION_ROLE if assigned else ', but not found in any guild'}.",
            color=discord.Color.green() if assigned else discord.Color.orange(),
            timestamp=datetime.now(UTC)
        )
    else:
        embed = discord.Embed(
            title="❌ Already Subscribed",
            description=f"User ID `{user_id}` is already subscribed.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)

@bot.command(name="remove_subscription")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def remove_subscription(ctx, user_id: str = None):
    if user_id is None:
        embed = discord.Embed(
            title="📝 Remove Subscription",
            description=f"Usage: `{BOT_PREFIX}remove_subscription <user_id>`\nExample: `{BOT_PREFIX}remove_subscription 1234567890`",
            color=discord.Color.blue(),
            timestamp=datetime.now(UTC)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        await ctx.send(embed=embed)
        return

    # Handle mentions or raw input
    try:
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1].replace('!', '')  # Extract ID from <@user_id> or <@!user_id>
        user_id_int = int(user_id)
    except ValueError:
        embed = discord.Embed(
            title="❌ Invalid User ID",
            description="Please provide a valid numeric user ID (e.g., `1234567890`) or a mention (e.g., `@user`).",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        await ctx.send(embed=embed)
        return

    if user_id_int in SUBSCRIPTION_IDS:
        SUBSCRIPTION_IDS.remove(user_id_int)
        save_subscription_ids()
        removed = False
        for guild in bot.guilds:
            member = guild.get_member(user_id_int)
            if member:
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if role:
                    try:
                        await member.remove_roles(role)
                        removed = True
                        break
                    except discord.Forbidden:
                        embed = discord.Embed(
                            title="❌ Permission Error",
                            description=f"Cannot remove `{SUBSCRIPTION_ROLE}` in {guild.name}. Ensure I have 'Manage Roles' permission.",
                            color=discord.Color.red(),
                            timestamp=datetime.now(UTC)
                        )
                        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
                        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
                        await ctx.send(embed=embed)
                        return

        embed = discord.Embed(
            title="✅ Subscription Removed",
            description=f"User ID `{user_id_int}` removed from subscriptions{' and ' + SUBSCRIPTION_ROLE + ' role removed' if removed else ', but not found in any guild'}.",
            color=discord.Color.green() if removed else discord.Color.orange(),
            timestamp=datetime.now(UTC)
        )
    else:
        embed = discord.Embed(
            title="❌ Not Subscribed",
            description=f"User ID `{user_id_int}` is not in the subscription list.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)

@bot.command(name="check_subscription")
async def check_subscription(ctx, user_id: int = None):
    user_id = user_id or ctx.author.id
    embed = discord.Embed(
        title="📋 Subscription Status",
        description=f"User ID `{user_id}` is **{'subscribed' if user_id in SUBSCRIPTION_IDS else 'not subscribed'}**.",
        color=discord.Color.green() if user_id in SUBSCRIPTION_IDS else discord.Color.red(),
        timestamp=datetime.now(UTC)
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)

# Run the bot
bot.run(TOKEN)

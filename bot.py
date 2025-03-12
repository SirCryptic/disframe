import os
import asyncio
import discord
import json
import logging
from discord.ext import commands, tasks
from datetime import datetime, UTC
from dotenv import load_dotenv
import config
from config import BOT_PREFIX, DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SERVER_INVITE_LINK, OWNER_ID, DEV_IDS, SUBSCRIPTION_ROLE, BOT_NAME, BOT_VERSION, ROLE_COLORS

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("No TOKEN found in .env file. Please set it up.")
    exit(1)

# Bot configuration with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True
intents.voice_states = False  # Disable voice intent to avoid PyNaCl warning

bot = commands.AutoShardedBot(command_prefix=BOT_PREFIX, intents=intents, case_insensitive=True)

# Global bot settings with defaults
bot_locked = False
ALLOWED_DM = True
SETTINGS_FILE = "data/bot_settings.json"

# Store SubscriptionManager instance globally
bot.subscribers = None

def load_settings():
    """Load bot settings from JSON file, create it if not present."""
    global bot_locked, ALLOWED_DM
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                bot_locked = data.get("locked", False)
                ALLOWED_DM = data.get("allowed_dm", True)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load settings: {e}")
            bot_locked = False
            ALLOWED_DM = True
            save_settings()
    else:
        bot_locked = False
        ALLOWED_DM = True
        save_settings()
        logger.info(f"Created new settings file with defaults: locked={bot_locked}, allowed_dm={ALLOWED_DM}")

def save_settings():
    """Save bot settings to JSON file."""
    settings = {
        "locked": bot_locked,
        "allowed_dm": ALLOWED_DM
    }
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        logger.error(f"Failed to save settings: {e}")

def get_total_member_count():
    """Calculate total member count across all guilds."""
    return sum(guild.member_count or 0 for guild in bot.guilds)

async def get_statuses():
    """Async generator for bot statuses."""
    if bot_locked:
        yield "Bot Locked 🔒"
    else:
        guild_count = len(bot.guilds)
        member_count = get_total_member_count()
        shard_count = bot.shard_count or 1
        dm_status = "DMs enabled ✅" if ALLOWED_DM else "DMs disabled ❌"
        statuses = [
            f"{BOT_PREFIX}help for commands! 🤖",
            f"Protecting {guild_count} Servers & {member_count} Users! 🛡️",
            f"Shards: {shard_count} active! ⚙️",
            f"{dm_status} | Serving {member_count} Users!"
        ]
        for status in statuses:
            yield status

@tasks.loop(minutes=1)
async def change_status():
    """Background task to rotate bot status."""
    try:
        async for status in get_statuses():
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=status))
            if bot_locked:
                await asyncio.sleep(60)
                break
            await asyncio.sleep(15)
    except Exception as e:
        logger.error(f"Status change failed: {e}")

async def load_all_cogs():
    """Load all cogs from the cmds/ directory at startup."""
    loaded_cogs = 0
    for root, _, files in os.walk("cmds"):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_name = os.path.join(root, file).replace(os.sep, ".")[:-3]
                try:
                    await bot.load_extension(module_name)
                    loaded_cogs += 1
                    logger.info(f"Loaded cog: {module_name}")
                except commands.ExtensionNotFound:
                    logger.error(f"Cog {module_name} not found.")
                except commands.ExtensionFailed as e:
                    logger.error(f"Cog {module_name} failed to load: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error loading cog {module_name}: {e}")
    logger.info(f"Successfully loaded {loaded_cogs} cog(s)")

@bot.event
async def on_ready():
    """Handle bot startup with all cogs preloaded."""
    load_settings()
    guilds = len(bot.guilds)
    members = get_total_member_count()
    shards = bot.shard_count or 1
    logger.info(f"Logged in as {bot.user} ({bot.user.id}) on {guilds} guild(s) with {shards} shard(s) and {members} members")
    logger.info(f"Bot lock status: {'locked' if bot_locked else 'unlocked'}")
    logger.info(f"DM status: {'enabled' if ALLOWED_DM else 'disabled'}")
    bot.remove_command("help")  # Remove default help to use custom one
    await load_all_cogs()  # Preload all cogs
    logger.info(f"{bot.user} is ready!")
    if not change_status.is_running():
        change_status.start()

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a new guild."""
    logger.info(f"Joined new guild: {guild.name} ({guild.id})")
    embed = discord.Embed(
        title="🤖 Bot Joined!",
        description=f"Hello! I’ve joined **{guild.name}**. Any admin can set up roles by granting me **Manage Roles** permissions and running `{BOT_PREFIX}setup`.",
        color=discord.Color.blue(),
        timestamp=datetime.now(UTC)
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")

    owner = guild.owner
    if owner:
        try:
            await owner.send(embed=embed)
            logger.info(f"DM sent to {owner.name}#{owner.discriminator} for {guild.name}")
        except discord.Forbidden:
            logger.warning(f"Could not DM {owner.name}#{owner.discriminator} - falling back to guild")
            target_channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
            if target_channel:
                try:
                    await target_channel.send(embed=embed)
                    logger.info(f"Notified {guild.name} in {target_channel.name}")
                except discord.Forbidden:
                    logger.warning(f"Could not send message in {guild.name} - insufficient permissions")

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    """Set up roles, with additional roles for devs/owner."""
    if not ctx.guild:
        await ctx.send(embed=discord.Embed(
            title="❌ Guild-Only Feature",
            description=f"`{BOT_PREFIX}setup` can only be used in a server.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))
        return

    roles_to_configure = {
        "BOT_USER_ROLE": (BOT_USER_ROLE, ROLE_COLORS.get(BOT_USER_ROLE)),
        "MOD_ROLE": (MOD_ROLE, ROLE_COLORS.get(MOD_ROLE))
    }
    if ctx.author.id in {OWNER_ID, *DEV_IDS}:
        roles_to_configure.update({
            "DEV_ROLE": (DEV_ROLE, ROLE_COLORS.get(DEV_ROLE)),
            "SUBSCRIPTION_ROLE": (SUBSCRIPTION_ROLE, ROLE_COLORS.get(SUBSCRIPTION_ROLE))
        })

    existing_roles = {role.name: role for role in ctx.guild.roles}
    created_or_updated = []

    for role_key, (role_name, role_color) in roles_to_configure.items():
        if role_name not in existing_roles:
            try:
                await ctx.guild.create_role(name=role_name, color=role_color, reason=f"Setup {role_key} by {ctx.author}")
                created_or_updated.append(f"`{role_name}` (created)")
            except discord.Forbidden as e:
                await ctx.send(embed=discord.Embed(
                    title="❌ Setup Failed",
                    description=f"Cannot create `{role_name}`. Ensure I have **Manage Roles** permission. Error: {str(e)}",
                    color=discord.Color.red(),
                    timestamp=datetime.now(UTC)
                ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))
                return
        else:
            role = existing_roles[role_name]
            if role.color != role_color:
                try:
                    await role.edit(color=role_color, reason=f"Updated {role_key} color by {ctx.author}")
                    created_or_updated.append(f"`{role_name}` (color updated)")
                except discord.Forbidden as e:
                    await ctx.send(embed=discord.Embed(
                        title="❌ Setup Failed",
                        description=f"Cannot edit `{role_name}`. Ensure my role is above `{role_name}`. Error: {str(e)}",
                        color=discord.Color.red(),
                        timestamp=datetime.now(UTC)
                    ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))
                    return
            else:
                created_or_updated.append(f"`{role_name}` (unchanged)")

    if ctx.author.id in {OWNER_ID, *DEV_IDS}:
        existing_channel = discord.utils.get(ctx.guild.text_channels, name="🔒-subscriptions")
        if not existing_channel:
            emoji = "🔒"
            channel_name = f"{emoji}-subscriptions"
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                discord.utils.get(ctx.guild.roles, name=SUBSCRIPTION_ROLE): discord.PermissionOverwrite(read_messages=True),
            }
            try:
                await ctx.guild.create_text_channel(channel_name, overwrites=overwrites, reason="Subscription channel")
                created_or_updated.append(f"`{channel_name}` (created)")
            except discord.Forbidden as e:
                await ctx.send(embed=discord.Embed(
                    title="❌ Setup Failed",
                    description=f"Cannot create `{channel_name}` channel. Ensure I have **Manage Channels**. Error: {str(e)}",
                    color=discord.Color.red(),
                    timestamp=datetime.now(UTC)
                ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))
                return

    await ctx.send(embed=discord.Embed(
        title="✅ Setup Complete",
        description=f"Setup completed in **{ctx.guild.name}**:\n- " + "\n- ".join(created_or_updated),
        color=discord.Color.green(),
        timestamp=datetime.now(UTC)
    ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))

@bot.event
async def on_message(message):
    """Handle incoming messages, allowing subscribers to bypass DM lock via ID check."""
    if message.author.bot:
        return

    # Check if user is a subscriber by ID in the database
    is_subscriber = False
    if bot.subscribers and not ALLOWED_DM:  # Only check if DMs are disabled
        is_subscriber = bot.subscribers.contains(message.author.id)

    # Allow DMs for owner, devs, and subscribers even if ALLOWED_DM is False
    if not message.guild and not ALLOWED_DM and message.author.id not in {OWNER_ID, *DEV_IDS} and not is_subscriber:
        await message.author.send(embed=discord.Embed(
            title="❌ DMs Not Supported",
            description=f"I can’t process commands in DMs unless you’re a subscriber.\nJoin my server: [Click here]({SERVER_INVITE_LINK})\nUse `{BOT_PREFIX}help` there.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))
        return

    await bot.process_commands(message)

@bot.command(name="lock")
@commands.check(lambda ctx: ctx.author.id in {OWNER_ID, *DEV_IDS})
async def lock(ctx):
    """Lock the bot for owner/dev use only."""
    global bot_locked
    embed = discord.Embed(timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    if bot_locked:
        embed.title, embed.description, embed.color = "🔒 Bot Already Locked", "The bot is already locked.", discord.Color.orange()
    else:
        bot_locked = True
        save_settings()
        embed.title, embed.description, embed.color = "🔒 Bot Locked", "The bot is now locked. Only owner/devs can use commands.", discord.Color.red()
        if change_status.is_running():
            change_status.restart()
    await ctx.send(embed=embed)

@bot.command(name="unlock")
@commands.check(lambda ctx: ctx.author.id in {OWNER_ID, *DEV_IDS})
async def unlock(ctx):
    """Unlock the bot for all users."""
    global bot_locked
    embed = discord.Embed(timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    if not bot_locked:
        embed.title, embed.description, embed.color = "🔓 Bot Already Unlocked", "The bot is already unlocked.", discord.Color.orange()
    else:
        bot_locked = False
        save_settings()
        embed.title, embed.description, embed.color = "🔓 Bot Unlocked", "The bot is now unlocked for all users.", discord.Color.green()
        if change_status.is_running():
            change_status.restart()
    await ctx.send(embed=embed)

@bot.command(name="toggle_dm")
@commands.check(lambda ctx: ctx.author.id in {OWNER_ID, *DEV_IDS})
async def toggle_dm(ctx):
    """Toggle DM allowance for non-privileged users."""
    global ALLOWED_DM
    ALLOWED_DM = not ALLOWED_DM
    save_settings()
    embed = discord.Embed(
        title="✅ DM Setting Updated",
        description=f"DMs are now **{'enabled' if ALLOWED_DM else 'disabled'}** for non-privileged users. Subscribers can still DM me.",
        color=discord.Color.green(),
        timestamp=datetime.now(UTC)
    ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)
    if change_status.is_running():
        change_status.restart()

@bot.command(name="status")
async def status(ctx):
    """Display the bot's lock and DM status."""
    await ctx.send(embed=discord.Embed(
        title="🔍 Bot Status",
        description=f"The bot is currently **{'locked' if bot_locked else 'unlocked'}**.\nDMs are **{'enabled' if ALLOWED_DM else 'disabled'}** for non-privileged users (subscribers exempt).",
        color=discord.Color.red() if bot_locked else discord.Color.green(),
        timestamp=datetime.now(UTC)
    ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))

@bot.check
async def global_check(ctx):
    """Global command check for bot lock."""
    if bot_locked and ctx.author.id not in {OWNER_ID, *DEV_IDS}:
        await ctx.send(embed=discord.Embed(
            title="🔒 Bot Locked",
            description="The bot is locked. Contact the owner or a dev to unlock it.",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC)
        ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))
        return False
    return True

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    embed = discord.Embed(color=discord.Color.red(), timestamp=datetime.now(UTC))
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png")
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")

    if isinstance(error, commands.MissingPermissions):
        embed.title, embed.description = "❌ Permission Denied", f"You need **Administrator** permissions to use `{ctx.command}`."
    elif isinstance(error, commands.MissingRequiredArgument):
        embed.title, embed.description = "❌ Missing Arguments", f"Missing required argument: `{error.param.name}`"
        embed.add_field(name="Tip", value=f"Use `{BOT_PREFIX}help {ctx.command}` for details.", inline=False)
    elif isinstance(error, commands.CommandNotFound):
        embed.title, embed.description, embed.color = "❌ Command Not Found", f"Command not recognized. Use `{BOT_PREFIX}help`.", discord.Color.orange()
    elif isinstance(error, commands.CommandOnCooldown):
        embed.title, embed.description, embed.color = "⏳ Command on Cooldown", f"You are on cooldown. Try again in {int(error.retry_after)} seconds.", discord.Color.orange()
    elif isinstance(error, commands.CommandInvokeError):
        embed.title, embed.description = "❌ Command Error", f"An error occurred while running `{ctx.command}`."
        embed.add_field(name="Details", value=str(error.original)[:1000], inline=False)
        logger.error(f"Command error in {ctx.command}: {error.original}")
    else:
        embed.title, embed.description = "❌ Unexpected Error", f"An unexpected error occurred in `{ctx.command}`."
        embed.add_field(name="Details", value=str(error)[:1000], inline=False)
        logger.error(f"Unexpected error in {ctx.command}: {error}")

    error_message = await ctx.send(embed=embed)
    await asyncio.sleep(10)
    try:
        await error_message.delete()
    except discord.Forbidden:
        pass

async def start_bot():
    """Start the bot with rate limit handling."""
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            await bot.start(TOKEN)
            break
        except discord.HTTPException as e:
            if e.status == 429: 
                wait_time = 2 ** retries + 1 
                logger.warning(f"Rate limited (429). Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to start bot: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error starting bot: {e}")
            raise

# Run the bot with asyncio
if __name__ == "__main__":
    asyncio.run(start_bot())

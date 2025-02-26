import os
import asyncio
import discord
import json
import logging
from discord.ext import commands, tasks
from datetime import datetime, UTC
from dotenv import load_dotenv
import config
from config import BOT_PREFIX, DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SERVER_INVITE_LINK, OWNER_ID, DEV_IDS, SUBSCRIPTION_ROLE, BOT_NAME, BOT_VERSION

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
ALLOWED_DM = True  # Default value if JSON file doesn't exist
SETTINGS_FILE = "data/bot_settings.json"

def load_settings():
    """Load bot settings from JSON file, create it if not present."""
    global bot_locked, ALLOWED_DM
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                bot_locked = data.get("locked", False)
                ALLOWED_DM = data.get("allowed_dm", True)  # Default to True if not in JSON
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load settings: {e}")
            bot_locked = False
            ALLOWED_DM = True  # Fallback to defaults on error
            save_settings()  # Create a new file with defaults
    else:
        # File doesn't exist, create it with defaults
        bot_locked = False
        ALLOWED_DM = True
        save_settings()
        logger.info(f"[INFO] Created new settings file with defaults: locked={bot_locked}, allowed_dm={ALLOWED_DM}")

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

# Subscription IDs
class SubscriptionManager:
    def __init__(self, file_path="data/subscription_ids.json"):
        self.file_path = file_path
        self.subscribers = self._load()

    def _load(self):
        """Load subscription IDs from JSON file."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    return set(data.get("SUBSCRIPTION_IDS", []))  # Use set for O(1) lookups
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load subscription IDs: {e}")
                return set()
        return set()

    def save(self):
        """Save subscription IDs to JSON file."""
        try:
            with open(self.file_path, "w") as f:
                json.dump({"SUBSCRIPTION_IDS": list(self.subscribers)}, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save subscription IDs: {e}")

    def add(self, user_id):
        """Add a subscriber."""
        self.subscribers.add(user_id)
        self.save()

    def remove(self, user_id):
        """Remove a subscriber."""
        self.subscribers.discard(user_id)  # discard avoids KeyError
        self.save()

    def contains(self, user_id):
        """Check if a user is subscribed."""
        return user_id in self.subscribers

subscriptions = SubscriptionManager()

# Role colors
ROLE_COLORS = {
    DEV_ROLE: discord.Color.gold(),
    SUBSCRIPTION_ROLE: discord.Color.purple(),
    BOT_USER_ROLE: discord.Color.blue(),
    MOD_ROLE: discord.Color.green()
}

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
            await asyncio.sleep(15)  # Shorter interval for smoother rotation
    except Exception as e:
        logger.error(f"Status change failed: {e}")

async def load_commands():
    """Recursively load command files from cmds/ directory."""
    loaded_cogs = 0
    for root, _, files in os.walk("cmds"):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_name = os.path.join(root, file).replace(os.sep, ".")[:-3]
                try:
                    await bot.load_extension(module_name)
                    loaded_cogs += 1
                except Exception as e:
                    logger.error(f"Failed to load cog {module_name}: {e}")
    logger.info(f"[INFO] Loaded {loaded_cogs} cog(s)")  # Only log total count

@bot.event
async def on_ready():
    """Handle bot startup."""
    load_settings()  # Load lock and DM settings on startup
    guilds = len(bot.guilds)
    members = get_total_member_count()
    shards = bot.shard_count or 1
    logger.info(f"[INFO] Logged in as {bot.user} ({bot.user.id}) on {guilds} guild(s) with {shards} shard(s) and {members} members")
    logger.info(f"[INFO] Bot lock status: {'locked' if bot_locked else 'unlocked'}")
    logger.info(f"[INFO] DM status: {'enabled' if ALLOWED_DM else 'disabled'}")
    bot.remove_command("help")
    await load_commands()
    logger.info(f"[INFO] {bot.user} is ready!")
    if not change_status.is_running():
        change_status.start()

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a new guild."""
    logger.info(f"[INFO] Joined new guild: {guild.name} ({guild.id})")
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
            logger.info(f"[INFO] DM sent to {owner.name}#{owner.discriminator} for {guild.name}")
        except discord.Forbidden:
            logger.warning(f"Could not DM {owner.name}#{owner.discriminator} - falling back to guild")
            target_channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
            if target_channel:
                try:
                    await target_channel.send(embed=embed)
                    logger.info(f"[INFO] Notified {guild.name} in {target_channel.name}")
                except discord.Forbidden:
                    logger.warning(f"Could not send message in {guild.name} - insufficient permissions")
            else:
                logger.warning(f"No suitable channel in {guild.name} to send notification")

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
    if ctx.author.id in {OWNER_ID, *DEV_IDS}:  # More concise check
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
                    description=f"Cannot create `{role_name}`. Ensure I have **Manage Roles** permission and my role is above others. Error: {str(e)}",
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
                        description=f"Cannot edit `{role_name}`. My role must be above `{role_name}` and have **Manage Roles**. Error: {str(e)}",
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
    """Handle incoming messages, including DM checks."""
    if message.author.bot:
        return

    if not message.guild and not ALLOWED_DM and message.author.id not in {OWNER_ID, *DEV_IDS, *subscriptions.subscribers}:
        await message.author.send(embed=discord.Embed(
            title="❌ DMs Not Supported",
            description=f"I can’t process commands in DMs.\nJoin my server: [Click here]({SERVER_INVITE_LINK})\nUse `{BOT_PREFIX}help` there.",
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
        save_settings()  # Save updated settings
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
        save_settings()  # Save updated settings
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
    save_settings()  # Save updated settings
    embed = discord.Embed(
        title="✅ DM Setting Updated",
        description=f"DMs are now **{'enabled' if ALLOWED_DM else 'disabled'}** for non-privileged users.",
        color=discord.Color.green(),
        timestamp=datetime.now(UTC)
    ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    await ctx.send(embed=embed)
    if change_status.is_running():
        change_status.restart()  # Reflect DM status change immediately

@bot.command(name="status")
async def status(ctx):
    """Display the bot's lock and DM status."""
    await ctx.send(embed=discord.Embed(
        title="🔍 Bot Status",
        description=f"The bot is currently **{'locked' if bot_locked else 'unlocked'}**.\nDMs are **{'enabled' if ALLOWED_DM else 'disabled'}** for non-privileged users.",
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

@bot.command(name="add_subscription")
@commands.check(lambda ctx: ctx.author.id in {OWNER_ID, *DEV_IDS})
async def add_subscription(ctx, user_id: int = None):
    """Add a user to the subscription list."""
    embed = discord.Embed(timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    if user_id is None:
        embed.title, embed.description, embed.color = "📝 Add Subscription", f"Usage: `{BOT_PREFIX}add_subscription <user_id>`\nExample: `{BOT_PREFIX}add_subscription 1234567890`", discord.Color.blue()
    elif subscriptions.contains(user_id):
        embed.title, embed.description, embed.color = "❌ Already Subscribed", f"User ID `{user_id}` is already subscribed.", discord.Color.red()
    else:
        subscriptions.add(user_id)
        assigned = False
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member:
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if not role and (ctx.author.id in {OWNER_ID, *DEV_IDS}):
                    try:
                        role = await guild.create_role(name=SUBSCRIPTION_ROLE, color=ROLE_COLORS[SUBSCRIPTION_ROLE], reason=f"Subscription by {ctx.author}")
                    except discord.Forbidden as e:
                        embed.title, embed.description, embed.color = "❌ Permission Error", f"Cannot create `{SUBSCRIPTION_ROLE}` in {guild.name}. Error: {str(e)}", discord.Color.red()
                        await ctx.send(embed=embed)
                        return
                if role:
                    try:
                        await member.add_roles(role)
                        assigned = True
                        break
                    except discord.Forbidden as e:
                        embed.title, embed.description, embed.color = "❌ Permission Error", f"Cannot assign `{SUBSCRIPTION_ROLE}` in {guild.name}. Error: {str(e)}", discord.Color.red()
                        await ctx.send(embed=embed)
                        return
        embed.title, embed.description, embed.color = "✅ Subscription Added", f"User ID `{user_id}` added{' and assigned ' + SUBSCRIPTION_ROLE if assigned else ', but not found in any guild'}.", discord.Color.green() if assigned else discord.Color.orange()
    await ctx.send(embed=embed)

@bot.command(name="remove_subscription")
@commands.check(lambda ctx: ctx.author.id in {OWNER_ID, *DEV_IDS})
async def remove_subscription(ctx, user_id: str = None):
    """Remove a user from the subscription list."""
    embed = discord.Embed(timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    if user_id is None:
        embed.title, embed.description, embed.color = "📝 Remove Subscription", f"Usage: `{BOT_PREFIX}remove_subscription <user_id>`\nExample: `{BOT_PREFIX}remove_subscription 1234567890`", discord.Color.blue()
    else:
        try:
            user_id_int = int(user_id.strip('<@!>'))
            if not subscriptions.contains(user_id_int):
                embed.title, embed.description, embed.color = "❌ Not Subscribed", f"User ID `{user_id_int}` is not subscribed.", discord.Color.red()
            else:
                subscriptions.remove(user_id_int)
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
                            except discord.Forbidden as e:
                                embed.title, embed.description, embed.color = "❌ Permission Error", f"Cannot remove `{SUBSCRIPTION_ROLE}` in {guild.name}. Error: {str(e)}", discord.Color.red()
                                await ctx.send(embed=embed)
                                return
                embed.title, embed.description, embed.color = "✅ Subscription Removed", f"User ID `{user_id_int}` removed{' and ' + SUBSCRIPTION_ROLE + ' removed' if removed else ', but not found in any guild'}.", discord.Color.green() if removed else discord.Color.orange()
        except ValueError:
            embed.title, embed.description, embed.color = "❌ Invalid User ID", "Please provide a valid numeric user ID or mention.", discord.Color.red()
    await ctx.send(embed=embed)

@bot.command(name="check_subscription")
async def check_subscription(ctx, user_id: int = None):
    """Check subscription status of a user."""
    user_id = user_id or ctx.author.id
    is_subscribed = subscriptions.contains(user_id)
    await ctx.send(embed=discord.Embed(
        title="📋 Subscription Status",
        description=f"User ID `{user_id}` is **{'subscribed' if is_subscribed else 'not subscribed'}**.",
        color=discord.Color.green() if is_subscribed else discord.Color.red(),
        timestamp=datetime.now(UTC)
    ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}"))

# Run the bot
bot.run(TOKEN)

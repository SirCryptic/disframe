import os
import asyncio
import discord
import json
from discord.ext import commands, tasks
import config
from config import TOKEN, BOT_PREFIX, DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SERVER_INVITE_LINK, ALLOWED_DM, OWNER_ID, DEV_IDS, SUBSCRIPTION_ROLE

# Bot configuration with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.AutoShardedBot(command_prefix=BOT_PREFIX, intents=intents)

# Global bot lock variable
bot_locked = False

# Load subscription IDs from config.json
SUBSCRIPTION_IDS = []

# Load subscription IDs from a JSON file
def load_subscription_ids():
    """Load subscription IDs from config.json."""
    global SUBSCRIPTION_IDS
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            SUBSCRIPTION_IDS = data.get("SUBSCRIPTION_IDS", [])
    else:
        SUBSCRIPTION_IDS = []

# Save subscription IDs to a JSON file
def save_subscription_ids():
    """Save subscription IDs to config.json."""
    data = {"SUBSCRIPTION_IDS": SUBSCRIPTION_IDS}
    with open("config.json", "w") as f:
        json.dump(data, f, indent=4)

# List of statuses to rotate
statuses = [
    f"Use {BOT_PREFIX}help for commands! 🤖",
    "Protecting servers!",
    f"Shards active: {bot.shard_count}",
    "DMs are Disabled! 🚫"
]

# Background task to change bot status
@tasks.loop(seconds=60)
async def change_status():
    for status in statuses:
        await bot.change_presence(activity=discord.Game(name=status))
        await asyncio.sleep(60)

async def ensure_roles_exist(guild):
    """Ensure required roles exist in the guild."""
    required_roles = [DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SUBSCRIPTION_ROLE]
    existing_roles = {role.name for role in guild.roles}

    for role_name in required_roles:
        if role_name not in existing_roles:
            await guild.create_role(name=role_name)
            print(f"[INFO] Created role: {role_name}")

# Function to create subscription channel with emoji
async def create_subscription_channel(guild):
    """Create a private subscription channel if it doesn't exist."""
    existing_channel = discord.utils.get(guild.text_channels, name="🔒-subscriptions")
    
    if not existing_channel:
        # Create the 'subscriptions' private text channel with an emoji in the name
        emoji = "🔒"  # Example emoji for private channels
        channel_name = f"{emoji}-subscriptions"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Deny access to @everyone
            discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE): discord.PermissionOverwrite(read_messages=True),  # Allow access to subscribers
        }
        
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        print(f"[INFO] Created private 'subscriptions' channel with emoji in {guild.name}")
        return channel
    return existing_channel

async def load_commands():
    """Recursively load command files from cmds/ and its subdirectories."""
    for root, _, files in os.walk("cmds"):  
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_name = os.path.join(root, file).replace(os.sep, ".")[:-3]  # Convert path to module format
                try:
                    await bot.load_extension(module_name)
                    print(f"[INFO] Loaded: {module_name}")
                except Exception as e:
                    print(f"[ERROR] Failed to load {module_name}: {e}")

@bot.event
async def on_ready():
    """Handle bot startup."""
    print(f"Logged in as {bot.user} ({bot.user.id}) on {len(bot.guilds)} guild(s) with {bot.shard_count} shard(s).")
    print("Initializing roles and commands...")

    for guild in bot.guilds:
        await ensure_roles_exist(guild)
        await create_subscription_channel(guild)  # Ensure the subscription channel exists

    bot.remove_command("help")
    print("Loading commands...")
    await load_commands()

    # Load subscription data
    load_subscription_ids()
    
    print("[INFO] Bot is ready!")
    change_status.start()

# Lock & Unlock Commands
@bot.command(name="lock")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def lock(ctx):
    global bot_locked
    if bot_locked:
        embed = discord.Embed(
            title="Bot Already Locked",
            description="The bot is already in a locked state.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    bot_locked = True
    embed = discord.Embed(
        title="Bot Locked",
        description="The bot has been locked. Please contact the bot owner or a developer to unlock it.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name="unlock")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def unlock(ctx):
    global bot_locked
    if not bot_locked:
        embed = discord.Embed(
            title="Bot Already Unlocked",
            description="The bot is already unlocked.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    bot_locked = False
    embed = discord.Embed(
        title="Bot Unlocked",
        description="The bot has been unlocked. All users can now use commands.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="status")
async def status(ctx):
    if bot_locked:
        embed = discord.Embed(
            title="Bot Status",
            description="The bot is currently **locked**. Please contact the bot owner or a developer to unlock it.",
            color=discord.Color.red()
        )
    else:
        embed = discord.Embed(
            title="Bot Status",
            description="The bot is **unlocked** and functional.",
            color=discord.Color.green()
        )
    await ctx.send(embed=embed)

@bot.check
async def global_check(ctx):
    if bot_locked:
        if ctx.author.id != OWNER_ID and ctx.author.id not in DEV_IDS:
            embed = discord.Embed(
                title="Bot Locked",
                description="The bot is currently locked. Please contact the bot owner or a developer to unlock it.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return False
    return True

@bot.event
async def on_message(message):
    """Handle all incoming messages, including DM checks."""

    # Ignore bot messages (prevents infinite loops)
    if message.author.bot:
        return

    # Check if the message is from a DM and ALLOWED_DM is False
    if not message.guild and not ALLOWED_DM:
        # Allow the bot owner, devs, or users in SUBSCRIPTION_IDS to bypass DM restrictions
        if message.author.id == OWNER_ID or message.author.id in DEV_IDS or message.author.id in SUBSCRIPTION_IDS:
            await bot.process_commands(message)  # Allow owner, devs, or subscription users to use DM commands
            return
        
        # Send an embedded message if the user is not allowed to DM
        embed = discord.Embed(
            title="❌ Direct Messages Not Supported",
            description=( 
                "I cannot process commands in direct messages.\n"
                f"Please join my server to use commands: [Click here to join]({SERVER_INVITE_LINK})\n"
                f"Once in, use `{BOT_PREFIX}help` for a list of commands."
            ),
            color=discord.Color.red(),
        )
        try:
            await message.author.send(embed=embed)
        except discord.errors.Forbidden:
            print(f"[WARNING] Could not send DM to {message.author} (DMs disabled).")

        return  # Prevent further processing of the message

    # Process commands normally if the message is from a server
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    if isinstance(error, commands.MissingRole):
        embed = discord.Embed(
            title="Missing Role",
            description=f"You need the **{error.missing_role}** role to use this command.",
            color=discord.Color.red(),
        )
        error_message = await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="Missing Arguments",
            description=f"You're missing required arguments: {error.param.name}",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="Tip",
            value=f"Use `{BOT_PREFIX}help {ctx.command}` for more details.",
            inline=False,
        )
        error_message = await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Command Not Found",
            description=f"That command does not exist. Use `{BOT_PREFIX}help` to see available commands.",
            color=discord.Color.orange(),
        )
        error_message = await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandInvokeError):
        embed = discord.Embed(
            title="Command Error",
            description="An error occurred while running this command. Please try again later.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Details", value=str(error.original), inline=False)
        error_message = await ctx.send(embed=embed)

    elif isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to run this command.",
            color=discord.Color.red(),
        )
        error_message = await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandOnCooldown):
        # Handle the cooldown error separately
        embed = discord.Embed(
            title="Cooldown",
            description=f"❌ You are on cooldown. Try again in `{error.retry_after:.2f}` seconds.",
            color=discord.Color.orange(),
        )
        error_message = await ctx.send(embed=embed)

    else:
        embed = discord.Embed(
            title="Unexpected Error",
            description="An unexpected error occurred. Please contact the bot administrator.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Error Details", value=str(error), inline=False)
        error_message = await ctx.send(embed=embed)

    # Cleanup the error message after 5 seconds
    await asyncio.sleep(5)
    try:
        await error_message.delete()
    except discord.errors.NotFound:
        pass  # Ignore if the message is already deleted

    print(f"[ERROR] Command error: {error}")

# Subscription Role Management Commands
@bot.command(name="add_subscription")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def add_subscription(ctx, user_id: int = None):
    """Add a user ID to the Subscription role and assign the role to the user in the guild."""
    if user_id is None:
        # Send help message if no user ID is provided
        embed = discord.Embed(
            title="How to Use add_subscription",
            description=f"Usage: `{BOT_PREFIX}add_subscription <user_id>`\n"
                        "Adds a user to the subscription role.\n"
                        f"Example: `{BOT_PREFIX}add_subscription 1234567890`",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)
        return

    if user_id not in SUBSCRIPTION_IDS:
        SUBSCRIPTION_IDS.append(user_id)
        save_subscription_ids()

        # Now assign the role to the user in the same guild
        assigned = False
        for guild in bot.guilds:
            # Look for the user in the guild
            member = guild.get_member(user_id)
            if member:
                # Check if the role exists
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if role:
                    try:
                        # Assign the role
                        await member.add_roles(role)
                        assigned = True
                        
                        # Create the subscription channel if it doesn't exist
                        await create_subscription_channel(guild)
                        
                        break
                    except discord.Forbidden:
                        # If the bot doesn't have permissions
                        embed = discord.Embed(
                            title="Permission Error",
                            description=f"The bot doesn't have the required permissions to assign roles in {guild.name}. Please ensure the bot has the 'Manage Roles' permission and its role is above {role.name}.",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return

        if assigned:
            embed = discord.Embed(
                title="Subscription Updated",
                description=f"User ID {user_id} has been added to the subscription list and given the `{SUBSCRIPTION_ROLE}` role.",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="Subscription Updated",
                description=f"User ID {user_id} has been added to the subscription list, but they are not in any of the connected guilds.",
                color=discord.Color.orange(),
            )

        await ctx.send(embed=embed)

    else:
        embed = discord.Embed(
            title="Subscription Error",
            description=f"User ID {user_id} is already in the subscription list.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

@bot.command(name="remove_subscription")
@commands.check(lambda ctx: ctx.author.id == OWNER_ID or ctx.author.id in DEV_IDS)
async def remove_subscription(ctx, user_id: int = None):
    """Remove a user ID from the Subscription role and remove the role from the user in the guild."""
    if user_id is None:
        # Send help message if no user ID is provided
        embed = discord.Embed(
            title="How to Use remove_subscription",
            description=f"Usage: `{BOT_PREFIX}remove_subscription <user_id>`\n"
                        "Removes a user from the subscription role.\n"
                        f"Example: `{BOT_PREFIX}remove_subscription 1234567890`",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)
        return

    if user_id in SUBSCRIPTION_IDS:
        SUBSCRIPTION_IDS.remove(user_id)
        save_subscription_ids()

        # Remove the role from the user in the same guild
        removed = False
        for guild in bot.guilds:
            # Look for the user in the guild
            member = guild.get_member(user_id)
            if member:
                # Check if the role exists
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if role:
                    try:
                        # Remove the role
                        await member.remove_roles(role)
                        removed = True
                        break
                    except discord.Forbidden:
                        # If the bot doesn't have permissions
                        embed = discord.Embed(
                            title="Permission Error",
                            description=f"The bot doesn't have the required permissions to remove roles in {guild.name}. Please ensure the bot has the 'Manage Roles' permission and its role is above {role.name}.",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return

        if removed:
            embed = discord.Embed(
                title="Subscription Updated",
                description=f"User ID {user_id} has been removed from the subscription list and their `{SUBSCRIPTION_ROLE}` role has been removed.",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="Subscription Updated",
                description=f"User ID {user_id} has been removed from the subscription list, but they are not in any of the connected guilds.",
                color=discord.Color.orange(),
            )

        await ctx.send(embed=embed)

    else:
        embed = discord.Embed(
            title="Subscription Error",
            description=f"User ID {user_id} is not in the subscription list.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

@bot.command(name="check_subscription")
async def check_subscription(ctx, user_id: int = None):
    """Check if a user is in the subscription list."""
    if user_id is None:
        user_id = ctx.author.id  # Default to checking the author's subscription status

    if user_id in SUBSCRIPTION_IDS:
        embed = discord.Embed(
            title="Subscription Status",
            description=f"User ID {user_id} is **subscribed**.",
            color=discord.Color.green(),
        )
    else:
        embed = discord.Embed(
            title="Subscription Status",
            description=f"User ID {user_id} is **not subscribed**.",
            color=discord.Color.red(),
        )
    
    await ctx.send(embed=embed)

# Run the bot
bot.run(TOKEN)

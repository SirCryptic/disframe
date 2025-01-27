import os
import asyncio
import discord
from discord.ext import commands, tasks
from config import TOKEN, BOT_PREFIX, DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SERVER_INVITE_LINK, ALLOWED_DM

# Bot configuration with intents to access member data (including presence, status, etc.)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  # Enable access to member-related data (presence, member list)

# Create sharded bot instance with the updated intents
bot = commands.AutoShardedBot(command_prefix=BOT_PREFIX, intents=intents)

# Global bot lock variable
bot_locked = False

# List of statuses to rotate
statuses = [
    f"Use {BOT_PREFIX}help for commands!",
    "Protecting servers!",
    f"Shards active: {bot.shard_count}",
    "DMs are not supported!"
]

# Background task to change bot status
@tasks.loop(seconds=30)  # Change status every 30 seconds
async def change_status():
    for status in statuses:
        await bot.change_presence(activity=discord.Game(name=status))
        await asyncio.sleep(30)  # Wait 30 seconds before updating again

async def ensure_roles_exist(guild):
    """Ensure required roles exist in the guild."""
    required_roles = [DEV_ROLE, BOT_USER_ROLE, MOD_ROLE]
    existing_roles = {role.name for role in guild.roles}

    for role_name in required_roles:
        if role_name not in existing_roles:
            await guild.create_role(name=role_name)
            print(f"[INFO] Created role: {role_name}")

@bot.event
async def on_ready():
    """Handle bot startup."""
    print(f"Logged in as {bot.user} ({bot.user.id}) on {len(bot.guilds)} guild(s) with {bot.shard_count} shard(s).")
    print("Initializing roles and commands...")

    # Ensure roles exist for all guilds
    for guild in bot.guilds:
        await ensure_roles_exist(guild)

    # Remove default help command
    bot.remove_command("help")

    # Dynamically load commands from the cmds folder
    print("Loading commands...")
    for file in os.listdir("cmds"):
        if file.endswith(".py") and not file.startswith("__"):
            try:
                await bot.load_extension(f"cmds.{file[:-3]}")
                print(f"[INFO] Loaded: {file}")
            except Exception as e:
                print(f"[ERROR] Failed to load {file}: {e}")
    
    print("[INFO] Bot is ready!")

    # Start the background task for changing statuses
    change_status.start()

# Lock and Unlock commands
@bot.command(name="lock")
@commands.has_role(DEV_ROLE)  # Only allow users with the role specified in config.py to lock the bot
async def lock(ctx):
    global bot_locked
    if bot_locked:  # Avoid redundant messages if already locked
        await ctx.send("The bot is already locked.")
        return
    bot_locked = True
    await ctx.send(f"The bot is now locked. Only users with the `{DEV_ROLE}` role can use commands.")

@bot.command(name="unlock")
@commands.has_role(DEV_ROLE)  # Only allow users with the role specified in config.py to unlock the bot
async def unlock(ctx):
    global bot_locked
    if not bot_locked:  # Avoid redundant messages if already unlocked
        await ctx.send("The bot is already unlocked.")
        return
    bot_locked = False
    await ctx.send("The bot is now unlocked. All users can use commands.")

# Command to check if the bot is locked
@bot.command(name="status")
async def status(ctx):
    if bot_locked:
        await ctx.send(f"The bot is currently locked. Only users with the `{DEV_ROLE}` role can use commands.")
    else:
        await ctx.send("The bot is unlocked and functional.")

# A decorator to check if the bot is locked before processing commands
@bot.check
async def global_check(ctx):
    if bot_locked:
        # If the bot is locked and the user doesn't have the required role, reject the command
        if not any(role.name == DEV_ROLE for role in ctx.author.roles):
            await ctx.send(f"The bot is locked! You must have the `{DEV_ROLE}` role to use commands.")
            return False  # This will stop the command from being processed
    return True  # Allow the command to be processed if the check passes

@bot.event
async def on_message(message):
    """Handle all incoming messages."""
    # Check if DMs are allowed and if the message is from a DM (no guild)
    if not message.guild and not ALLOWED_DM:
        embed = discord.Embed(
            title="Direct Messages Not Supported",
            description=( 
                f"I cannot process commands in direct messages.\n"
                f"Please join my server to use commands: [Click here to join]({SERVER_INVITE_LINK})\n"
                f"Once in, use `{BOT_PREFIX}help` to get a list of commands."
            ),
            color=discord.Color.red(),
        )
        try:
            await message.author.send(embed=embed)  # Send DM explaining this
        except discord.errors.HTTPException as e:
            # Log the error with a custom message
            print(f"[ERROR] Could not send message to {message.author} (Bot DMs disabled): {e}")
        return  # Prevent further processing of the message

    # If the message is from a server (guild), process the commands as normal
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    if isinstance(error, commands.MissingRole):
        # User lacks a required role
        embed = discord.Embed(
            title="Missing Role",
            description=f"You need the **{error.missing_role}** role to use this command.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument):
        # Command is missing required arguments
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
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandNotFound):
        # Command does not exist
        embed = discord.Embed(
            title="Command Not Found",
            description=f"That command does not exist. Use `{BOT_PREFIX}help` to see a list of available commands.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandInvokeError):
        # Error during command execution
        embed = discord.Embed(
            title="Command Error",
            description="An error occurred while running this command. Please try again later.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Details", value=str(error.original), inline=False)
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CheckFailure):
        # Check (e.g., permissions) failed
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to run this command.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    else:
        # Generic error
        embed = discord.Embed(
            title="Unexpected Error",
            description="An unexpected error occurred. Please contact the bot administrator.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Error Details", value=str(error), inline=False)
        await ctx.send(embed=embed)

    # Log the error in the console
    print(f"[ERROR] Command error: {error}")

if __name__ == "__main__":
    # Run the bot with the TOKEN from config.py
    bot.run(TOKEN)

import os
import asyncio
import discord
from discord.ext import commands, tasks
from config import TOKEN, BOT_PREFIX, DEV_ROLE, BOT_USER_ROLE, MOD_ROLE, SERVER_INVITE_LINK, ALLOWED_DM, OWNER_ID

# Bot configuration with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

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
@tasks.loop(seconds=30)
async def change_status():
    for status in statuses:
        await bot.change_presence(activity=discord.Game(name=status))
        await asyncio.sleep(30)

async def ensure_roles_exist(guild):
    """Ensure required roles exist in the guild."""
    required_roles = [DEV_ROLE, BOT_USER_ROLE, MOD_ROLE]
    existing_roles = {role.name for role in guild.roles}

    for role_name in required_roles:
        if role_name not in existing_roles:
            await guild.create_role(name=role_name)
            print(f"[INFO] Created role: {role_name}")

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

    bot.remove_command("help")
    print("Loading commands...")
    await load_commands()
    
    print("[INFO] Bot is ready!")
    change_status.start()

# Lock & Unlock Commands
@bot.command(name="lock")
@commands.has_role(DEV_ROLE)
async def lock(ctx):
    global bot_locked
    if bot_locked:
        await ctx.send("The bot is already locked.")
        return
    bot_locked = True
    await ctx.send(f"The bot is now locked. Only users with the `{DEV_ROLE}` role can use commands.")

@bot.command(name="unlock")
@commands.has_role(DEV_ROLE)
async def unlock(ctx):
    global bot_locked
    if not bot_locked:
        await ctx.send("The bot is already unlocked.")
        return
    bot_locked = False
    await ctx.send("The bot is now unlocked. All users can use commands.")

@bot.command(name="status")
async def status(ctx):
    if bot_locked:
        await ctx.send(f"The bot is currently locked. Only users with the `{DEV_ROLE}` role can use commands.")
    else:
        await ctx.send("The bot is unlocked and functional.")

@bot.check
async def global_check(ctx):
    if bot_locked:
        if not any(role.name == DEV_ROLE for role in ctx.author.roles):
            await ctx.send(f"The bot is locked! You must have the `{DEV_ROLE}` role to use commands.")
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
        # Allow the bot owner to use DMs for testing
        if message.author.id == OWNER_ID:
            await bot.process_commands(message)  # Allow the owner to use DM commands
            return
        
        # Send an embedded message if the user is not the owner
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
        await ctx.send(embed=embed)

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
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Command Not Found",
            description=f"That command does not exist. Use `{BOT_PREFIX}help` to see available commands.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandInvokeError):
        embed = discord.Embed(
            title="Command Error",
            description="An error occurred while running this command. Please try again later.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Details", value=str(error.original), inline=False)
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to run this command.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    else:
        embed = discord.Embed(
            title="Unexpected Error",
            description="An unexpected error occurred. Please contact the bot administrator.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Error Details", value=str(error), inline=False)
        await ctx.send(embed=embed)

    print(f"[ERROR] Command error: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)

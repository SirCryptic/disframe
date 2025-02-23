<p align="center">
  <a href="https://github.com/sircryptic/DisFrame">
    <img src="https://github.com/user-attachments/assets/3b0d136e-7992-4b37-a8ab-de8051308f4f" alt="DisFrame" width="500">
  </a>
</p>

<p align="center">
  <a href="https://github.com/sircryptic/disframe/stargazers"><img src="https://img.shields.io/github/stars/sircryptic/disframe.svg" alt="GitHub stars"></a>
  <a href="https://github.com/sircryptic/disframe/network"><img src="https://img.shields.io/github/forks/sircryptic/disframe.svg" alt="GitHub forks"></a>
  <a href="https://github.com/sircryptic/disframe/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-unlicense-green.svg" alt="License"></a>
</p>

## DisFrame: A Modular Discord Bot Framework

DisFrame is a flexible, extensible Discord bot built with Python and `discord.py`, designed for easy customization via modular cogs. It provides robust moderation, administration, and user engagement features.

### Key Features

- **Modular Design**: Add commands via Python cogs in the `cmds` directory.
- **Role-Based Access**: Permissions for `owner`, `dev`, `mod`, `bot user`, and `subscriber` roles.
- **Dynamic Management**: Load, unload, and reload commands without restarts.
- **Moderation Tools**: Kick, ban, mute, warn,automod and log server events.
- **User Engagement**: Memes, Meme Creation, translations, profiles, and role reaction.
- **Subscription System**: Manage private channels and DM access for subscribers (beta).
- **Multi-Guild**: Features can now be setup across multiple discord guilds eg: enabling/disabling nsfw memes and auto-moderation.

### Requirements

- Python 3.8+
- `discord.py==2.4.0`, `psutil==6.1.1`, `googletrans==4.0.0-rc1` (see `requirements.txt`)
- Discord bot token

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sircryptic/disframe.git
cd disframe
```

### 2. Install dependencies
It’s recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Set up your bot token
Edit the `config.py` file in the root directory and add your Discord bot token etc:

Replace the placeholders with your actual values.

### 4. Run the bot
Once everything is set up, run the bot using:

```bash
python3 bot.py
```
The bot will log in and start processing commands.

### Adding Commands
Create a new cog in cmds/ (e.g., mycommand.py) and load it dynamically with -load cmds.mycommand. Role names must match those in config.py (e.g., MOD_ROLE = "mod"). See below for Examples.

<details> <summary>Command Examples</summary>

### Basic Command
```python
import discord
from discord.ext import commands

class MyCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mycommand")
    async def my_command(self, ctx):
        await ctx.send("Hello from a custom command!")

async def setup(bot):
    await bot.add_cog(MyCommand(bot))
```

### Role-Restricted Command
* Restrict a command to users with the mod role:
```python
import discord
from discord.ext import commands

class ModCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="modonly")
    @commands.has_role("mod")
    async def mod_only(self, ctx):
        await ctx.send("This command is for moderators only!")

async def setup(bot):
    await bot.add_cog(ModCommand(bot))

```
### Multi-Role Command Example with DM Support
* Restrict to mod or dev roles in guilds, allow in DMs:
```python
import discord
from discord.ext import commands
import config

class MultiRoleCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="multirole")
    @commands.check(lambda ctx: ctx.guild is None or any(role.name in [config.MOD_ROLE, config.DEV_ROLE] for role in ctx.author.roles))
    async def multi_role_command(self, ctx):
        """A command restricted to mod/dev roles in guilds or allowed in DMs."""
        if ctx.guild is None:
            await ctx.send("This command is running in DMs!")
        else:
            await ctx.send(f"Welcome, {ctx.author.mention}! You have the '{config.MOD_ROLE}' or '{config.DEV_ROLE}' role.")

async def setup(bot):
    await bot.add_cog(MultiRoleCommand(bot))

```

</details>

### Loading and Managing Commands  

DisFrame automatically loads any new commands placed in the `cmds` folder when it starts. Simply add a new file, restart the bot, and it’s ready to use!  

Additionally, you can now **dynamically load, unload, and reload modules** without restarting the bot.  

#### Load a New Command Manually  
```bash
-load cmds.new_command
```
This will load `cmds/new_command.py` dynamically.

#### Unload a Command
```bash
-unload cmds.new_command
```
This removes the command from memory until it’s loaded again.

#### Reload all Commands in `cmds` folder except `mod` & `dev` or any folder
```bash
-reload_all
```

#### Reload a command
```bash
-reload
```

## Bot Permissions

### **Owner**
- **Access**: The owner can DM the bot directly for any queries or requests, including management tasks eg reloading cmds.
- **Important**: To set the owner of the bot, you need to update the `OWNER_ID` in the `config.py` file.
  - **How to set**: Open your `config.py` file and locate the `OWNER_ID` variable. Set this value to the Discord User ID of the bot owner.
```python
OWNER_ID = your_discord_user_id_here
```

### **dev**
- **Access**: Unrestricted access to most commands (e.g., lock and unlock the bot).
- **Exclusions**: **NONE**
- **Usage**: This role is typically granted to trusted users who need to manage and configure the bot.

### **mod**
- **Access**: Moderators with this role have access to certain commands that help manage the server, such as clearing messages or enforcing server rules.
- **Usage**: Ideal for users who need to help moderate the server.

### **bot user**
- **Access**: Limited access to a set of basic commands that are non-admin and non-moderator in nature.
- **Usage**: This role is typically assigned to bots or users that need minimal interaction with the bot.

### **everyone**
- **Access**: This role has the most limited access, with only basic commands allowed.
- **Usage**: This role is assigned to every server member who should not have special privileges or advanced access.

### **subscriber**
- **Access**: Subscribers have access to exclusive channels and can use DMs even if they are disabled globally.
- **Usage**: This role is assigned to users who have subscribed to the bot's services.

### Commands
* General: -info, -serverinfo, -profile, -translate, -meme
* Moderation: -kick, -ban, -mute, -warn, -automod , -setuprolereaction + More!
* Admin: -lock, -unlock, -load, -reload, -eval (dev/owner only) + More!
* Fun: -meme (use memehelp to setup guild features),-creatememe,
* Help: -help for a paginated menu

### Contributing
Fork the repository, add features or fixes, and submit a pull request. Suggestions are welcome via issues.

## License
see the [LICENSE](https://github.com/SirCryptic/disframe/blob/main/LICENSE) file for details.

## Support
If you encounter any issues or need help, feel free to open an issue on this repository.

Feel free to update the `README.md` with your project-specific details, such as the specific information regarding the bot's functionality.

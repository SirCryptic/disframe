<p align="center">
  <a href="https://github.com/sircryptic/DisFrame">
    <img src="https://github.com/user-attachments/assets/3b0d136e-7992-4b37-a8ab-de8051308f4f" alt="DisFrame" width="500" 
    onmouseover="this.style.transform='scale(1.05)'; this.style.opacity='0.8';" 
    onmouseout="this.style.transform='scale(1)'; this.style.opacity='1';">
  </a>
  
#
A modular and extensible Discord bot framework that allows easy customization by adding new commands through Python cogs.

<div align="center">
    <a href="https://github.com/sircryptic/disframe/stargazers"><img src="https://img.shields.io/github/stars/sircryptic/disframe.svg" alt="GitHub stars"></a>
    <a href="https://github.com/sircryptic/disframe/network"><img src="https://img.shields.io/github/forks/sircryptic/disframe.svg" alt="GitHub forks"></a>
    <a href="https://github.com/sircryptic/disframe/watchers"><img src="https://img.shields.io/github/watchers/sircryptic/disframe.svg?style=social" alt="GitHub watchers"></a>
    <br>
    <a href="https://github.com/SirCryptic/disframe/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-unlicense-green.svg" alt="License"></a>
</div>

## Features

- **Modular Command Structure**: Add new commands by creating Python files in the `cmds` directory.
- **Role-based Permissions**: Commands can be restricted to specific roles like `mod`, `dev`, or `bot user`.
- **Automatic Role Creation**: The bot will automatically create `dev`, `mod`, and `bot user` roles if they do not exist.
- **Help System with Pagination**: A clean and organized help command with interactive buttons for navigation.
- **Developer & Mod Commands**: Exclusive commands for bot admins and moderators.
- **DM Restrictions**: Commands are primarily executed in servers, ensuring the bot functions securely within guilds.
- **Dynamic Command Management**: Load, unload, and reload commands without restarting the bot.
- **Subscription Management**: Manage subscription roles and private channels for subscribers.

## Requirements

- Python 3.8+
- Discord.py (installed via `pip install discord.py`)
- A Discord bot token

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
Change the `config.py` file in the root directory and add your Discord bot token etc:

Replace the placeholders with your actual values.

### 4. Run the bot
Once everything is set up, run the bot using:

```bash
python3 bot.py
```
The bot will log in and start processing commands.

## Adding Commands
To add new commands, simply follow these steps:

1. Create a Python file in the `cmds` folder (e.g., `new_command.py`).
2. Define a class inheriting from `commands.Cog` and add the new commands inside that class.
3. Use the `@commands.command()` decorator to define the command.
4. Implement any logic or checks for role-based permissions.

Example of a custom command (`cmds/new_command.py`):

```python
import discord
from discord.ext import commands

class NewCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="newcommand")
    @commands.has_role("mod")
    async def new_command(self, ctx):
        await ctx.send("This is a new command for moderators.")

async def setup(bot):
    await bot.add_cog(NewCommand(bot))
```

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
- **Exclusions**: Users with this role are **excluded** from accessing the `adminhelp` page or any admin-specific commands.
- **Usage**: This role is typically granted to trusted users who need to manage and configure the bot, but without the ability to access sensitive administrative help commands.

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

## Contributing
If you'd like to contribute to this bot, feel free to fork the repository and submit a pull request. Here are some ways you can contribute:

- Add new commands to the bot.
- Improve the error handling and messages.
- Fix bugs or improve code efficiency.
- Suggest new features.

## License
see the [LICENSE](https://github.com/SirCryptic/disframe/blob/main/LICENSE) file for details.

## Support
If you encounter any issues or need help, feel free to open an issue on this repository.

Feel free to update the `README.md` with your project-specific details, such as the specific information regarding the bot's functionality.

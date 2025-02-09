# DisFrame
A modular and extensible Discord bot framework that allows easy customization by adding new commands through Python cogs.

## Features

- **Modular Command Structure**: Add new commands by creating Python files in the `cmds` directory.
- **Role-based Permissions**: Commands can be restricted to specific roles like `mod`, `dev`, or `bot user`.
- **Automatic Role Creation**: The bot will automatically create `dev`, `mod`, and `bot user` roles if they do not exist.
- **Help System with Pagination**: A clean and organized help command with interactive buttons for navigation.
- **Developer & Mod Commands**: Exclusive commands for bot admins and moderators.
- **DM Restrictions**: Commands are primarily executed in servers, ensuring the bot functions securely within guilds.

## Requirements

- Python 3.8+
- Discord.py (installed via `pip install discord.py`)
- A Discord bot token

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/discord-bot.git
cd discord-bot
```
### 2. Install dependencies
It’s recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Set up your bot token
Create a config.py file in the root directory and add your Discord bot token(you will also find a example with everything you need in the repo.):

```python
# config.py
TOKEN = "YOUR_BOT_TOKEN"
```
Replace "YOUR_BOT_TOKEN" with your actual Discord bot token.

### 4. Run the bot
Once everything is set up, run the bot using:

```bash
python bot.py
```
The bot will log in and start processing commands.

# Adding Commands
To add new commands, simply follow these steps:

Create a Python file in the cmds folder (e.g., `new_command.py`).
Define a class inheriting from `commands.Cog` and add the new commands inside that class.
Use the `@commands.command()` decorator to define the command.
Implement any logic or checks for role-based permissions.
Example of where i would place my custom command (`cmds/new_command.py`):

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

####  Load a New Command Manually  
```bash
-load cmds.new_command
```
This will load cmds/new_command.py dynamically.

 Unload a Command
```bash
-unload cmds.new_command
```
This removes the command from memory until it’s loaded again.

 Reload all Commands in cmds folder execpt mod & dev
```
-reload_all
```
#### Bot Permissions
`dev Role`: This role has unrestricted access to most commands (eg they can lock and unlock the bot) except from anything to do with `adminhelp` page.

`mod Role`: This role has access to specific commands such as clearing messages.

`bot user`: This role has limited access to certain commands or what you wish to choose.

`everyone`: This role has limited access to certain commands or what you wish to choose.

### Contributing
If you'd like to contribute to this bot, feel free to fork the repository and submit a pull request. Here are some ways you can contribute:

Add new commands to the bot.

Improve the error handling and messages.

Fix bugs or improve code efficiency.

Suggest new features.

### License
This project is licensed under the MIT License - see the LICENSE file for details.

### Support
If you encounter any issues or need help, feel free to open an issue on this repository.

Feel free to update the `README.md` with your project-specific details, such as the specific information regarding the bot's functionality.


<p align="center">
  <a href="https://github.com/sircryptic/DisFrame">
    <img src="https://github.com/user-attachments/assets/3b0d136e-7992-4b37-a8ab-de8051308f4f" alt="DisFrame" width="500">
  </a>
</p>

<p align="center">
  <a href="https://github.com/sircryptic/disframe/stargazers"><img src="https://img.shields.io/github/stars/sircryptic/disframe.svg" alt="GitHub stars"></a>
  <a href="https://github.com/sircryptic/disframe/network"><img src="https://img.shields.io/github/forks/sircryptic/disframe.svg" alt="GitHub forks"></a>
</p>

# DisFrame: A Modular Discord Bot Framework

DisFrame is a versatile, extensible Discord bot built with Python and `discord.py`, designed to enhance community management and user engagement. Its modular cog system enables effortless customization, making it adaptable for moderation, administration, and interactive fun across multiple guilds.

## Key Features

- **Modular Design**: Extend functionality by adding Python cogs to the `cmds` directory.
- **Role-Based Permissions**: Granular access control for `owner`, `dev`, `mod`, `bot user`, `subscriber`, and `everyone` roles.
- **Dynamic Command Management**: Load, unload, and reload commands without restarting the bot.
- **Comprehensive Moderation**: Tools like kick, ban, mute, warn, auto-moderation, and event logging.
- **Engaging Interactions**: Features including memes, custom meme creation, translations, and user profiles.
- **Subscription System**: Exclusive channel access and DM privileges for subscribers (beta).
- **Multi-Guild Flexibility**: Configure settings (e.g., NSFW memes, auto-moderation) per guild.
- **Persistent Settings**: Bot lock and DM allowance states saved to JSON for continuity across restarts.

## Requirements

- Python 3.8 or higher
- Required libraries: See `requirements.txt`
- A valid Discord bot token

## Installation

### 1. Clone the Repository
Clone the DisFrame repository to your local machine and navigate into the project directory.

### 2. Install Dependencies
Set up a virtual environment (recommended) and install the required dependencies listed in `requirements.txt`.

### 3. Create a `.env` File
Create a `.env` file in the root directory to securely store your Discord bot token. DisFrame uses this file to load sensitive information.

Add the following line to `.env`, replacing `your_bot_token_here` with your actual Discord bot token:
```
TOKEN=your_bot_token_here
```
### 4. Configure Bot Settings
Edit the `config.py` file in the root directory to define role names, owner ID, and other settings (e.g., `MOD_ROLE`, `OWNER_ID`). Replace placeholders with your specific values. The bot token is managed via `.env`, not `config.py`.

### 5. Run the Bot
Launch the bot with Python. It will read the token from `.env`, log in, and begin processing commands.

## Adding Commands

Add new commands by creating Python files (cogs) in the `cmds` directory. DisFrame automatically loads these on startup. Use role-based checks to restrict access, ensuring role names match those in `config.py` (e.g., `MOD_ROLE = "mod"`). Dynamically manage commands using built-in load, unload, and reload features.

## Bot Permissions

### Owner
- **Access**: Full control, including direct DM interaction for management tasks (e.g., reloading commands).
- **Setup**: Set `OWNER_ID` in `config.py` to your Discord User ID.

### Dev
- **Access**: Near-unrestricted command access (e.g., locking/unlocking, subscription management).
- **Usage**: For trusted developers configuring the bot.

### Mod
- **Access**: Moderation commands (e.g., kick, ban) and guild setup tools (e.g., `-setup`).
- **Usage**: For server moderators and administrators.

### Bot User
- **Access**: Basic, non-administrative commands.
- **Usage**: For bots or users with minimal privileges.

### Everyone
- **Access**: Limited to essential, public-facing commands.
- **Usage**: Default role for all server members without special permissions.

### Subscriber
- **Access**: Exclusive channel access and DM privileges, even when globally disabled.
- **Usage**: For users subscribed to premium features (beta).

## Commands

- **General**: `-info`, `-serverinfo`, `-profile`, `-translate`, `-status`
- **Moderation**: `-kick`, `-ban`, `-mute`, `-warn`, `-automod`, `-setuprolereaction`, `-setup`
- **Admin/Dev**: `-lock`, `-unlock`, `-toggle_dm`, `-load`, `-reload`, `-add_subscription`, `-remove_subscription`
- **Fun**: `-meme`, `-creatememe`
- **Games**: Explore examples in the [community cog repo](https://github.com/SirCryptic/disframe-cogs/tree/main) (e.g., CoinRush, Space Miner, Guess)
- **Help**: `-help` for an interactive, paginated menu

## Contributing

Contributions are welcome! Fork the repository, implement features or fixes, and submit a pull request. For suggestions or bug reports, open an issue on the GitHub repository.

## License

See the [LICENSE](https://github.com/SirCryptic/disframe/blob/main/LICENSE) file for details.

## Support

Need help or found an issue? Open an issue on the [GitHub repository](https://github.com/sircryptic/disframe/issues) for assistance from the community or maintainers.

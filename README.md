<p align="center">
  <a href="https://sircryptic.github.io/DisWeb">
    <img src="https://github.com/user-attachments/assets/3b0d136e-7992-4b37-a8ab-de8051308f4f" alt="DisFrame" width="500">
  </a>
</p>

<p align="center">
  <a href="https://github.com/sircryptic/disframe/stargazers"><img src="https://img.shields.io/github/stars/sircryptic/disframe.svg" alt="GitHub stars"></a>
  <a href="https://github.com/sircryptic/disframe/network"><img src="https://img.shields.io/github/forks/sircryptic/disframe.svg" alt="GitHub forks"></a>
  <a href="https://github.com/sircryptic/disframe/watchers"><img src="https://img.shields.io/github/watchers/sircryptic/disframe.svg" alt="GitHub watchers"></a>
      <br>
    <a href="https://github.com/SirCryptic/disframe/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
</p>

# DisFrame: A Modular Discord Bot Framework

DisFrame is a versatile, extensible Discord bot framework built with Python and `discord.py`, designed to streamline community management and enhance user engagement. Its modular cog system allows for effortless customization, making it ideal for moderation, administration, and interactive fun across multiple guilds.

## Key Features

- **Modular Design**: Extend functionality by adding Python cogs to the `cmds` directory.
- **Role-Based Permissions**: Granular access for `owner`, `dev`, `mod`, `bot user`, `subscriber`, and `everyone` roles.
- **Dynamic Command Management**: Load, unload, and reload commands without restarting the bot.
- **Comprehensive Moderation**: Tools including kick, ban, mute, warn, auto-moderation, and guild setup.
- **Engaging Interactions**: Features like memes, custom meme creation, translations, and user profiles.
- **Subscription System**: Exclusive channel access and DM privileges for subscribers (beta).
- **Multi-Guild Flexibility**: Per-guild settings for features like NSFW memes or moderation rules.
- **Persistent Settings**: Bot lock and DM allowance states preserved via JSON across restarts.

## Requirements

- Python 3.11 or higher
- Required libraries: See `requirements.txt` for details
- A valid Discord bot token

## Installation

### 1. Clone the Repository
Clone the DisFrame repository to your local machine and navigate into the project directory.

### 2. Install Dependencies
Set up a virtual environment (recommended) and install the dependencies listed in `requirements.txt`.

### 3. Create a `.env` File
Create a `.env` file in the root directory to securely store your Discord bot token, obtained from the [Discord Developer Portal](https://discord.com/developers/applications).

### 4. Configure Bot Settings
Edit `config.py` to set role names (e.g., `MOD_ROLE`), owner ID (`OWNER_ID`), and other configurations. The token is handled via `.env`.

### 5. Run the Bot
Launch the bot with Python. It will load the token from `.env`, log in, and begin processing commands.

## Adding Commands

Add new commands by placing Python cog files in the `cmds` directory. DisFrame loads these automatically on startup. Use role-based checks to restrict access, matching role names in `config.py` (e.g., `MOD_ROLE = "mod"`). Manage commands dynamically with `-load`, `-unload`, and `-reload`.

## Bot Permissions

### Owner
- **Access**: Full control, including DM management tasks (e.g., reloading commands).
- **Setup**: Define `OWNER_ID` in `config.py` with your Discord User ID.

### Dev
- **Access**: Near-unrestricted command access (e.g., locking, subscription management).
- **Usage**: For trusted developers configuring the bot.

### Mod
- **Access**: Moderation tools (e.g., kick, ban) and guild setup (e.g., `-setup`).
- **Usage**: For server moderators and administrators.

### Bot User
- **Access**: Basic, non-administrative commands.
- **Usage**: For bots or users with minimal privileges.

### Everyone
- **Access**: Essential, public-facing commands only.
- **Usage**: Default for all server members without special roles.

### Subscriber
- **Access**: Exclusive channels and DM privileges, even when globally disabled.
- **Usage**: For premium subscribers (beta).

## Commands

- **General**: `-info`, `-serverinfo`, `-profile`, `-translate`, `-status`
- **Moderation**: `-kick`, `-ban`, `-mute`, `-warn`, `-automod`, `-setuprolereaction`, `-setup`
- **Admin/Dev**: `-lock`, `-unlock`, `-toggle_dm`, `-load`, `-reload`, `-add_subscription`, `-remove_subscription`
- **Fun**: `-meme`, `-creatememe`
- **Games**: See examples in the [community cogs repo](https://github.com/SirCryptic/disframe-cogs) (e.g., CoinRush, Space Miner)
- **Help**: `-help` for an interactive, paginated menu

## Contributing

I welcome contributions! Fork the repository, add features or fixes, and submit a pull request. For ideas or issues, open a ticket on the [GitHub repository](https://github.com/sircryptic/disframe/issues).

## License

DisFrame is licensed under the [MIT License](LICENSE) (Copyright © 2025 SirCryptic), allowing free use, modification, and distribution with attribution.

## Support

Need assistance or found a bug? Visit the [GitHub issues page](https://github.com/sircryptic/disframe/issues) or join our [DisFrame Discord](https://discord.gg/48JH3UkerX).

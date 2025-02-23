# config.py

# Bot Token (how the token is stored will eventually change after development purposes , the update will not affect any of your functions/cogs)  
TOKEN = "YOUR_BOT_TOKEN"

# Command Prefix
BOT_PREFIX = "-"

# Role Names (change these to your actual role names eg. DEV_ROLE = "admin" )
DEV_ROLE = "dev"
BOT_USER_ROLE = "bot user"
MOD_ROLE = "mod"
SUBSCRIPTION_ROLE = "Subscription"
TIMEOUT_ROLE_NAME = "Muted"

# Server link (change this to your own server's invite link)
SERVER_INVITE_LINK = "https://discord.gg/invite"

# Set to True if you want to allow anyone to DM the bot, False if you don't ( the bots activity status will update accordingly based on this setting eg dms enabled & dms disabled same with locking the bot)
ALLOWED_DM = False

# Bot Version (you can change this to the version of your bot).
BOT_VERSION = "1.0.6"  # Example version.
BOT_NAME = "DisFrame"  # Replace this with your actual bot name.

OWNER_ID = 1231241232312345  # Replace this with your actual Discord User ID.
DEV_IDS = [123124234123123, 2123231234]  # List of developer IDs / Trusted Users.

# note ( had to use reddit api itself for meme cog the api key is free / you can remove this and the cog itself if you wish not to use it )
REDDIT_CLIENT_ID = "your_client_id"
REDDIT_CLIENT_SECRET = "your_secret_key"
REDDIT_USER_AGENT = "discord:DisFrame:1.6 by SirCryptic"

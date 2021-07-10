import os

DISCORD_DOMAIN = "discord.com"
DISCORD_CDN_DOMAIN = "cdn.discordapp.com"
DISCORD_CDN_AVATAR = f"https://{DISCORD_CDN_DOMAIN}/avatars/{{}}/{{}}.webp?size={{}}"
DISCORD_OAUTH2_TOKEN = f"https://{DISCORD_DOMAIN}/api/oauth2/token"
DISCORD_USER = f"https://{DISCORD_DOMAIN}/api/users/@me"

# Authorization and cookies
SECURE_KEY: str = os.getenv("SECURE_KEY")
BOT_AUTH: str = os.getenv("BOT_AUTH")

CLIENT_ID: int = int(os.getenv("CLIENT_ID"))
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET")

DEBUG: bool = bool(os.getenv("DEBUG", True))

REDIRECT_URL = os.getenv("REDIRECT_URI")
BASE_URL = os.getenv("BASE_URL")

SEARCH_ENGINE_URI: str = os.getenv("SEARCH_ENGINE_URI")
POSTGRES_URI: str = os.getenv("DATABASE_URL")



import os

discord_domain = "discord.com"
discord_cdn_domain = "cdn.discordapp.com"
discord_cdn_avatar = f"https://{discord_cdn_domain}/avatars/{{}}/{{}}.webp?size={{}}"
discord_oauth2_token = f"https://{discord_domain}/api/oauth2/token"
discord_user = f"https://{discord_domain}/api/users/@me"

# Authorization and cookies
secure_key: str = os.getenv("SECURE_KEY")
bot_auth: str = os.getenv("BOT_AUTH")

client_id: int = int(os.getenv("CLIENT_ID"))
client_secret: str = os.getenv("CLIENT_SECRET")

debug: bool = bool(os.getenv("DEBUG", True))
secure_sessions = not debug

search_engine_domain: str = os.getenv("SEARCH_DOMAIN")
redirect_url = os.getenv("REDIRECT_URI")
base_url = os.getenv("BASE_URL")




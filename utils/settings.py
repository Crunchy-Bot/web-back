import os


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




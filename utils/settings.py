import os


# Changeable
secure_sessions = bool(os.getenv("SECURE"))

# Authorization and cookies
secure_key: str = os.getenv("SECURE_KEY")
bot_auth: str = os.getenv("BOT_KEY")

client_id: int = int(os.getenv("CLIENT_ID"))
client_secret: str = os.getenv("CLIENT_SECRET")

debug: bool = bool(os.getenv("DEBUG", True))

search_engine_domain: str = os.getenv("SEARCH_DOMAIN")


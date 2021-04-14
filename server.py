from fastapi import FastAPI

from utils import settings
from sessions import SessionCollection


class Backend(FastAPI):
    def __init__(
            self,
            **extra,
    ):
        super().__init__(**extra)

        self.secure_key = settings.secure_key
        self.bot_token = settings.bot_auth

        self.sessions = SessionCollection()
        self.sessions.mount_middleware(self)


from typing import Optional

from fastapi import FastAPI
from asyncpg import create_pool, Pool

from utils import settings


class Backend(FastAPI):
    def __init__(
            self,
            **extra,
    ):
        super().__init__(**extra)

        self.secure_key = settings.SECURE_KEY
        self.bot_token = settings.BOT_AUTH
        self._pool: Optional[Pool] = None

        self.on_event("startup")(self.startup)
        self.on_event("shutdown")(self.shutdown)

    @property
    def pool(self) -> Pool:
        assert self._pool is not None, "pg pool was not initialised"
        return self._pool

    async def startup(self):
        self._pool = await create_pool(settings.POSTGRES_URI)

        await self.create_tables()

    async def shutdown(self):
        if self._pool is not None:
            await self._pool.close()

    async def create_tables(self):
        await self.pool.execute("""
        CREATE TABLE IF NOT EXISTS user_tracking_tags (
            user_id BIGINT,
            tag_id VARCHAR(32),
            description VARCHAR(300) NOT NULL DEFAULT '',
            CONSTRAINT COMP_KEY PRIMARY KEY (user_id, tag_id)
        );        
        CREATE TABLE IF NOT EXISTS user_tracking_items (
            _id UUID PRIMARY KEY,
            user_id BIGINT NOT NULL,
            tag_id VARCHAR(32) NOT NULL,
            title VARCHAR(128) NOT NULL,
            url VARCHAR(256) NOT NULL DEFAULT '',
            referer BIGINT,
            description VARCHAR(300) NOT NULL DEFAULT '',
            FOREIGN KEY (user_id, tag_id) 
            REFERENCES user_tracking_tags (user_id, tag_id)           
            ON DELETE CASCADE
        );   
        CREATE TABLE IF NOT EXISTS commands (
            command_id VARCHAR(32) PRIMARY KEY, 
            name VARCHAR(32) UNIQUE,
            category VARCHAR(32) NOT NULL,
            about TEXT NOT NULL,
            running TEXT NOT NULL,
            user_required_permissions BIGINT NOT NULL DEFAULT 0,
            bot_required_permissions BIGINT NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS user_command_aliases (
            user_id BIGINT,
            command_id VARCHAR(32),
            alias VARCHAR(32),
            PRIMARY KEY (user_id, command_id, alias),
            FOREIGN KEY (command_id)
            REFERENCES commands (command_id)
            ON DELETE CASCADE                         
        );
        CREATE TABLE IF NOT EXISTS guild_command_aliases (
            guild_id BIGINT,
            command_id VARCHAR(32),
            alias VARCHAR(32),
            PRIMARY KEY (guild_id, command_id, alias),
            FOREIGN KEY (command_id)
            REFERENCES commands (command_id)
            ON DELETE CASCADE                         
        );
        CREATE TABLE IF NOT EXISTS guild_events_hooks_release (
            guild_id BIGINT PRIMARY KEY,
            webhook_url TEXT NOT NULL,
            border_colour TEXT,
            text_colour TEXT,
            background_colour TEXT
        );
        CREATE TABLE IF NOT EXISTS guild_events_hooks_news (
            guild_id BIGINT PRIMARY KEY,
            webhook_url TEXT NOT NULL,
            border_colour TEXT,
            text_colour TEXT,
            background_colour TEXT        
        );
        """)






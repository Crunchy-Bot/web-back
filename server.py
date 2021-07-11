import meilisearch
from typing import Optional

from fastapi import FastAPI
from asyncpg import create_pool, Pool

from utils import settings


class MeiliEngine:
    def __init__(self):
        self.meili = meilisearch.Client(settings.SEARCH_ENGINE_URI)
        self._anime = self.meili.index("anime")
        self._manga = self.meili.index("manga")

        try:
            self._anime.delete_all_documents()
        except meilisearch.client.MeiliSearchApiError:
            pass
        try:
            self._manga.delete_all_documents()
        except meilisearch.client.MeiliSearchApiError:
            pass

        self._anime.update_settings({
            "searchableAttributes": ["title_english", "title", "title_japanese", "description", "genres"],
        })

        self._manga.update_settings({
            "searchableAttributes": ["title", "description", "genres"],
        })

    @property
    def anime(self):
        return self._anime

    @property
    def manga(self):
        return self._manga

    async def update_indexes(self, app: "Backend"):
        rows = await app.pool.fetch("""
        SELECT 
            title, 
            title_english,
            title_japanese,
            description, 
            rating, 
            img_url, 
            link, 
            array(SELECT name FROM api_genres WHERE id & api_anime_data.genres != 0) as genres, 
            id 
        FROM api_anime_data;
        """)

        if len(rows) > 0:
            rows = [dict(row) for row in rows]
            self.anime.add_documents(rows, primary_key="id")

        rows = await app.pool.fetch("""
        SELECT 
            title, 
            description, 
            rating, 
            img_url, 
            link, 
            array(SELECT name FROM api_genres WHERE id & api_manga_data.genres != 0) as genres, 
            id 
        FROM api_manga_data;
        """)

        if len(rows) > 0:
            rows = [dict(row) for row in rows]
            self.manga.add_documents(rows, primary_key="id")


class Backend(FastAPI):
    def __init__(
            self,
            **extra,
    ):
        super().__init__(**extra)

        self.secure_key = settings.SECURE_KEY
        self.bot_token = settings.BOT_AUTH
        self._pool: Optional[Pool] = None
        self._search_client = MeiliEngine()

        self.on_event("startup")(self.startup)
        self.on_event("shutdown")(self.shutdown)

    @property
    def meili(self):
        return self._search_client

    @property
    def pool(self) -> Pool:
        assert self._pool is not None, "pg pool was not initialised"
        return self._pool

    async def startup(self):
        self._pool = await create_pool(settings.POSTGRES_URI)
        await self.create_tables()

        await self.meili.update_indexes(self)

    async def shutdown(self):
        if self._pool is not None:
            await self._pool.close()

    async def create_tables(self):
        await self.pool.execute("""
        Create or replace function random_string(length integer) returns text as
        $$
        declare
          chars text[] := '{0,1,2,3,4,5,6,7,8,9,A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z}';
          result text := '';
          i integer := 0;
        begin
          if length < 0 then
            raise exception 'Given length cannot be less than 0';
          end if;
          for i in 1..length loop
            result := result || chars[1+random()*(array_length(chars, 1)-1)];
          end loop;
          return result;
        end;
        $$ language plpgsql;
        
        CREATE TABLE IF NOT EXISTS api_genres (
            id BIGINT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_anime_data (
            id TEXT PRIMARY KEY,
            title TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            rating FLOAT NOT NULL DEFAULT 1.0,
            img_url TEXT,
            link TEXT,
            genres BIGINT NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS api_manga_data (
            id TEXT PRIMARY KEY,
            title TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            rating FLOAT NOT NULL DEFAULT 1.0,
            img_url TEXT,
            link TEXT,
            genres BIGINT NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS user_tracking_tags (
            user_id BIGINT,
            tag_id VARCHAR(32),
            description VARCHAR(300) NOT NULL DEFAULT '',
            CONSTRAINT user_tracking_tags_comp_key PRIMARY KEY (user_id, tag_id)
        );        
        CREATE TABLE IF NOT EXISTS user_tracking_items (
            id UUID PRIMARY KEY,
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
        CREATE TABLE IF NOT EXISTS bot_commands (
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
            REFERENCES bot_commands (command_id)
            ON DELETE CASCADE                         
        );
        CREATE TABLE IF NOT EXISTS guild_command_aliases (
            guild_id BIGINT,
            command_id VARCHAR(32),
            alias VARCHAR(32),
            PRIMARY KEY (guild_id, command_id, alias),
            FOREIGN KEY (command_id)
            REFERENCES bot_commands (command_id)
            ON DELETE CASCADE                         
        );
        CREATE TABLE IF NOT EXISTS guild_events_hooks_release (
            guild_id BIGINT PRIMARY KEY,
            webhook_url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS guild_events_hooks_filter (
            guild_id BIGINT NOT NULL,
            anime_id TEXT NOT NULL,
            FOREIGN KEY (anime_id)
            REFERENCES api_anime_data (id)
            ON DELETE CASCADE,
            FOREIGN KEY (guild_id)
            REFERENCES guild_events_hooks_release (guild_id)
            ON DELETE CASCADE,
            CONSTRAINT guild_events_hooks_filter_comp_key PRIMARY KEY (guild_id, anime_id)    
        );
        CREATE TABLE IF NOT EXISTS guild_events_hooks_news (
            guild_id BIGINT PRIMARY KEY,
            webhook_url TEXT NOT NULL          
        );
        """)






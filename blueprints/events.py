import router

from typing import List
from pydantic import BaseModel

from server import Backend
from utils.responders import StandardResponse


class EventHook(BaseModel):
    guild_id: str
    webhook_url: str


class EventsResults(StandardResponse):
    data: List[EventHook]


class ReleaseEventsBlueprint(router.Blueprint):
    __base_route__ = "/events"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/releases",
        endpoint_name="Get Release Hooks",
        methods=["GET"],
        response_model=EventsResults,
        tags=["Events"]
    )
    async def get_release_hooks(self, page: int = 1, limit: int = -1, anime_id: str = None):
        # todo auth

        args = []
        limit_section = ""
        if limit > 0:
            limit_section = "LIMIT ${} OFFSET ${}"
            args = [limit, page * limit]

        if anime_id is None:
            qry = f"""
            SELECT 
                guild_id,
                webhook_url
            FROM guild_events_hooks_release 
            {limit_section.format(1, 2)}
            """
        else:
            qry = f"""
            SELECT 
                guild_id,
                webhook_url
            FROM guild_events_hooks_release 
            WHERE guild_id NOT IN (SELECT guild_id FROM guild_events_hooks_filter WHERE anime_id = $1)
            {limit_section.format(2, 3)};
            """
            args.insert(0, anime_id)
        results = await self.app.pool.fetch(qry, *args)

        return EventsResults(status=200, data=[dict(row) for row in results])  # noqa

    @router.endpoint(
        "/releases/{guild_id:int}",
        endpoint_name="Get Guild Release Hook",
        methods=["GET"],
        response_model=EventHook,
        responses={
            404: {
                "model": StandardResponse,
                "description": "No event hook exists for the given id"
            }
        },
        tags=["Events"],
    )
    async def get_release_hook(self, guild_id: int):
        # todo auth

        row = await self.app.pool.fetchrow("""
            SELECT
                webhook_url
            FROM guild_events_hooks_release
            WHERE guild_id = $1;
        """, guild_id)

        if row is None:
            return StandardResponse(
                status=404,
                data=f"no release hooks exist for {guild_id}",
            ).into_response()

        return EventHook(**row)

    @router.endpoint(
        "/releases/add",
        endpoint_name="Add Release Hook",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Events"]
    )
    async def add_release_hook(self, payload: EventHook):
        # todo auth

        await self.app.pool.execute(
            """
            INSERT INTO guild_events_hooks_release (
                guild_id, 
                webhook_url
            ) VALUES ($1, $2);
            """,
            payload.guild_id, payload.webhook_url
        )
        return StandardResponse(status=200, data="successfully added hook")

    @router.endpoint(
        "/releases/{guild_id:int}",
        endpoint_name="Remove Release Hook",
        methods=["DELETE"],
        tags=["Events"]
    )
    async def remove_release_hook(self, guild_id: int):
        # todo auth

        await self.app.pool.execute("""
            DELETE FROM guild_events_hooks_release
            WHERE guild_id = $1;
        """, guild_id)

        return StandardResponse(status=200, data="successfully removed hook")


class NewsEventsBlueprint(router.Blueprint):
    __base_route__ = "/events"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/news",
        endpoint_name="Get News Hooks",
        methods=["GET"],
        tags=["Events"]
    )
    async def get_news(self, page: int = 1, limit: int = -1):
        args = []
        limit_section = ""
        if limit > 0:
            limit_section = f"LIMIT $1 OFFSET $2"
            args = [limit, page * limit]

        results = await self.app.pool.fetch(f"""
            SELECT 
                guild_id,
                webhook_url
            FROM guild_events_hooks_news {limit_section};            
        """, *args)

        return EventsResults(status=200, data=[dict(row) for row in results])  # noqa

    @router.endpoint(
        "/news/{guild_id:int}",
        endpoint_name="Get Guild Release News",
        methods=["GET"],
        tags=["Events"]
    )
    async def get_news_hook(self, guild_id: int):
        row = await self.app.pool.fetchrow("""
            SELECT
                webhook_url
            FROM guild_events_hooks_news
            WHERE guild_id = $1;
        """, guild_id)

        if row is None:
            return StandardResponse(
                status=404,
                data=f"no news hooks exist for {guild_id}",
            ).into_response()

        return EventHook(**row)

    @router.endpoint(
        "/news/add",
        endpoint_name="Add News Hook",
        methods=["POST"],
        tags=["Events"]
    )
    async def add_news_hook(self, payload: EventHook):
        # todo auth

        await self.app.pool.execute(
            """
            INSERT INTO guild_events_hooks_news (
                guild_id, 
                webhook_url
            ) VALUES ($1, $2);
            """,
            payload.guild_id, payload.webhook_url,
        )

        return StandardResponse(status=200, data="successfully added hook")

    @router.endpoint(
        "/news/{guild_id:int}",
        endpoint_name="Remove News Hook",
        methods=["DELETE"],
        tags=["Events"]
    )
    async def remove_news_hook(self, guild_id: int):
        # todo auth

        await self.app.pool.execute("""
            DELETE FROM guild_events_hooks_news
            WHERE guild_id = $1;
        """, guild_id)

        return StandardResponse(status=200, data="successfully removed hook")


def setup(app):
    app.add_blueprint(ReleaseEventsBlueprint(app))
    app.add_blueprint(NewsEventsBlueprint(app))

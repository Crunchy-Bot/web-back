import router

from typing import Optional, Tuple, List
from pydantic import BaseModel, conint

from server import Backend
from utils.responders import StandardResponse

Int255 = conint(ge=0, le=255)
RGBA = Tuple[Int255, Int255, Int255, Int255]


def to_hex(colour: RGBA) -> str:
    return '#%02x%02x%02x' % colour[:3]


def from_hex(colour: str) -> RGBA:
    r, g, b = colour[1:3], colour[3:5], colour[5:7]
    return int(r, base=16), int(g, base=16), int(b, base=16), 255


class EventHook(BaseModel):
    webhook_url: str
    border_colour: Optional[RGBA]
    background_colour: Optional[RGBA]
    text_colour: Optional[RGBA]


class EventsResults(StandardResponse):
    data: List[EventHook]


def convert_row(row):
    row = dict(row)
    border_colour = row['border_colour']
    text_colour = row['text_colour']
    background_colour = row['background_colour']

    row['border_colour'] = border_colour and from_hex(border_colour)
    row['text_colour'] = text_colour and from_hex(text_colour)
    row['background_colour'] = background_colour and from_hex(background_colour)
    return row


class EventsBlueprint(router.Blueprint):
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
    async def get_release_hooks(self, page: int = 1, limit: int = -1):
        # todo auth

        args = []
        limit_section = ""
        if limit > 0:
            limit_section = "LIMIT $1 OFFSET $2"
            args = [limit, page * limit]

        results = await self.app.pool.fetch(f"""
            SELECT 
                webhook_url, 
                border_colour, 
                text_colour, 
                background_colour 
            FROM guild_events_hooks_release {limit_section};
        """, *args)

        return EventsResults(status=200, data=list(map(convert_row, results)))  # noqa

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

        result = await self.app.pool.fetchrow("""
            SELECT
                webhook_url, 
                border_colour, 
                text_colour, 
                background_colour
            FROM guild_events_hooks_release
            WHERE guild_id = $1;
        """, guild_id)

        if result is None:
            return StandardResponse(
                status=404,
                data=f"no release hooks exist for {guild_id}",
            ).into_response()

        row = convert_row(result)
        return EventHook(**row)

    @router.endpoint(
        "/releases/{guild_id:int}/edit",
        endpoint_name="Add Release Hook",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Events"]
    )
    async def add_release_hook(self, guild_id: int, payload: EventHook):
        # todo auth

        await self.app.pool.execute(
            """
            INSERT INTO guild_events_hooks_release (
                guild_id, 
                webhook_url, 
                border_colour, 
                text_colour, 
                background_colour
            ) VALUES ($1, $2, $3, $4, $5);
            """,
            guild_id, payload.webhook_url,
            payload.border_colour, payload.text_colour,
            payload.background_colour,
        )
        return StandardResponse(status=200, data="successfully added hook")

    @router.endpoint(
        "/releases/{guild_id:int}/edit",
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
            limit_section = "LIMIT $1 OFFSET $2"
            args = [limit, page * limit]

        results = await self.app.pool.fetch(f"""
            SELECT 
                webhook_url, 
                border_colour, 
                text_colour, 
                background_colour 
            FROM guild_events_hooks_news {limit_section};
        """, *args)

        return EventsResults(status=200, data=list(map(convert_row, results)))  # noqa

    @router.endpoint(
        "/news/{guild_id:int}",
        endpoint_name="Get Guild Release News",
        methods=["GET"],
        tags=["Events"]
    )
    async def get_news_hook(self, guild_id: int):
        result = await self.app.pool.fetchrow("""
            SELECT
                webhook_url, 
                border_colour, 
                text_colour, 
                background_colour
            FROM guild_events_hooks_news
            WHERE guild_id = $1;
        """, guild_id)

        if result is None:
            return StandardResponse(
                status=404,
                data=f"no news hooks exist for {guild_id}",
            ).into_response()

        row = convert_row(result)
        return EventHook(**row)

    @router.endpoint(
        "/news/{guild_id:int}/edit",
        endpoint_name="Add News Hook",
        methods=["POST"],
        tags=["Events"]
    )
    async def add_news_hook(self, guild_id: int, payload: EventHook):
        # todo auth

        await self.app.pool.execute(
            """
            INSERT INTO guild_events_hooks_news (
                guild_id, 
                webhook_url, 
                border_colour, 
                text_colour, 
                background_colour
            ) VALUES ($1, $2, $3, $4, $5);
            """,
            guild_id, payload.webhook_url,
            payload.border_colour, payload.text_colour,
            payload.background_colour,
        )

        return StandardResponse(status=200, data="successfully added hook")

    @router.endpoint(
        "/news/{guild_id:int}/edit",
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
    app.add_blueprint(EventsBlueprint(app))
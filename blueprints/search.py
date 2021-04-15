import aiohttp
import urllib.parse

import router
import pydantic

from typing import List, Optional
from shared import GeneralMessage
from server import Backend
from utils import settings


search_url = (
    f"http://{settings.search_engine_domain}/search"
    f"?engine={{engine}}"
    f"&query={{query}}"
    f"&fuzzy={{fuzzy}}"
    f"&limit={{limit}}"
)


ORDER_BY_OPTIONS = {
    "default",
    "rating-asc",
    "rating-desc",
}


class FilterByOptions:
    trending = 1 << 0
    recommended = 1 << 1
    popular = 1 << 2
    no_favourites = 1 << 3
    no_watchlist = 1 << 4
    no_recommended = 1 << 5

    all = (
        trending |
        recommended |
        popular |
        no_recommended |
        no_watchlist |
        no_recommended
    )


class SearchTypes:
    anime = "anime"
    manga = "manga"


class SearchPayload(pydantic.BaseModel):
    query: str
    type: str = SearchTypes.anime
    limit: int = 10
    chunk: int = -1
    fuzzy: bool = False
    order_by: str = "default"
    filter_by: int = 1

    @pydantic.validator("type")
    def type_limits(cls, v):
        if v in ("anime", "manga"):
            return v

        raise ValueError("must be either 'anime' or 'manga'")

    @pydantic.validator("limit")
    def check_limit(cls, v):
        if v < 1:
            raise ValueError("must greater than 0")
        elif v > 500:
            raise ValueError("must be bellow 500")

        return v

    @pydantic.validator("limit")
    def check_chunk(cls, v):
        if v == -1:
            return v
        elif v < 1:
            raise ValueError("must greater than 0 or -1")
        elif v > 50:
            raise ValueError("must be bellow 50")

        return v

    @pydantic.validator("query")
    def check_query(cls, v):
        if len(v) > 200:
            raise ValueError("query too long")
        elif len(v) < 1:
            raise ValueError("query too short")

        return urllib.parse.quote(v)

    @pydantic.validator("order_by")
    def check_order(cls, v):
        if v.lower() in ORDER_BY_OPTIONS:
            return v.lower()

        raise ValueError(f"not a valid order. Options: {ORDER_BY_OPTIONS}")

    @pydantic.validator("filter_by")
    def check_order(cls, v):
        if FilterByOptions.all & v != 0:
            return v

        raise ValueError("not a valid bit flag")


class SearchResult(pydantic.BaseModel):
    id: int
    parent: Optional[int]
    title: str
    url: str
    description: str
    thumbnail: str
    tags: int
    rating: float


class SearchResults(pydantic.BaseModel):
    status: int
    results: List[SearchResult]


class SearchAPI(router.Blueprint):
    def __init__(self, app: Backend):
        self.app = app
        self.app.on_event("startup")(self.start)
        self.app.on_event("shutdown")(self.shutdown)
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def shutdown(self):
        if self.session is not None:
            await self.session.close()

    @router.endpoint(
        "/search",
        endpoint_name="Search Content",
        description=(
            "Search for content with a given query and content type."
        ),
        methods=["GET"],
        response_model=SearchResults,
        tags=["Content API"],
    )
    async def search(self, payload: SearchPayload):
        url = search_url.format(
            engine=payload.type,
            query=payload.query,
            limit=payload.limit,
            fuzzy=payload.fuzzy,
        )

        async with self.session.get(url) as resp:
            resp.raise_for_status()

            data = await resp.json()



def setup(app):
    app.add_blueprint(SearchAPI(app))
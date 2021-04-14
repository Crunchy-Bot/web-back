import aiohttp

import router
import pydantic

from typing import List, Optional
from shared import GeneralMessage
from server import Backend





class SearchTypes:
    anime = "anime"
    manga = "manga"


class SearchPayload(pydantic.BaseModel):
    query: str
    type: str = SearchTypes.anime
    limit: int = 10
    chunk: int = -1

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
    def check_limit(cls, v):
        if v == -1:
            return v
        elif v < 1:
            raise ValueError("must greater than 0 or -1")
        elif v > 50:
            raise ValueError("must be bellow 50")

        return v

    @pydantic.validator("query")
    def check_limit(cls, v):
        if len(v) > 200:
            raise ValueError("query too long")
        elif len(v) < 1:
            raise ValueError("query too short")

        return v


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
        ...


def setup(app):
    app.add_blueprint(SearchAPI(app))
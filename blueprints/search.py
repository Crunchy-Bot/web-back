import aiohttp

import router
import pydantic

from pprint import pprint
from typing import List, Optional, Union
from server import Backend
from utils import settings, chunk_n
from utils.list_helpers import expand_out_of_lists

search_url = f"http://{settings.search_engine_domain}/search"


class FilterPayload(pydantic.BaseModel):
    """ A given filter to filter documents. """
    field_name: str
    filter_type: str
    filter_field_type: str
    filter_val: Union[int, List[str]]


class SearchQueryPayload(pydantic.BaseModel):
    """ The search query sent to the search engine Kratos. """
    engine: str
    query: str
    fuzzy: bool = False
    limit: int = 5
    filters: List[FilterPayload]
    sort_by: Optional[str]


ORDER_BY_OPTIONS = {
    "default",
    "rating-asc",
    "rating-desc",
}


class Tags:
    TAGS = dict(
        action=1 << 0,
        adventure=1 << 1,
        drama=1 << 2,
        comedy=1 << 3,
        fantasy=1 << 4,
        school=1 << 5,
        game=1 << 6,
        supernatural=1 << 7,
        thriller=1 << 8,
        yuri=1 << 9,
        shounen=1 << 10,
        mystery=1 << 11,
        magic=1 << 12,
        harem=1 << 13,
        sci_fi=1 << 14,
        yaoi=1 << 15,
        sports=1 << 16,
        romance=1 << 17,
        music=1 << 18,
        tournaments=1 << 19,
        school_club=1 << 20,
        horror=1 << 21,
        war=1 << 22,
    )

    ALL_TAGS = 0
    for v in TAGS.values():
        ALL_TAGS = ALL_TAGS | v


class FilterByOptions:
    """
    A set of filtering bitflags, useful for determining what
    results to remove and what not to remove.

    Unlike the Kratos filters the api uses these will remove results from
    the overall return rather than trying to reach the limit.
    """
    no_favourites = 1 << 0
    no_watchlist = 1 << 1
    no_recommended = 1 << 2

    all = (
        no_recommended |
        no_watchlist |
        no_recommended
    )


class SearchTypes:
    anime = "anime"
    manga = "manga"


class SearchPayload(pydantic.BaseModel):
    """
    The payload that should be sent to the API search endpoint.

    Attrs:
        query:
            The query string, this can follow a Tantivy Query.

        type:
            The type of search / where to search (anime or manga)

        limit:
            How many results to limit.

        chunk:
            If set to anything >= 1 it will split the returned results
            into even chunks making a two dimensional array of results.

        fuzzy:
            If the query should use fuzzy searching as well for more
            result matches.

        order_by:
            The field / value to order results by.

        filter_by:
            A set of bitflag filters that can be used to alter the results
            being returned.
    """
    query: str
    type: str = SearchTypes.anime
    limit: int = 10
    chunk: int = -1
    fuzzy: bool = False
    tags: int = 0
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

        return v

    @pydantic.validator("tags")
    def check_tags(cls, v):
        if Tags.ALL_TAGS & v != 0:
            return v

        raise ValueError("must be a valid tag bitflag")

    @pydantic.validator("order_by")
    def check_order(cls, v):
        if v.lower() in ORDER_BY_OPTIONS:
            return v.lower()

        raise ValueError(f"not a valid order. Options: {ORDER_BY_OPTIONS}")

    @pydantic.validator("filter_by")
    def check_filter(cls, v):
        if FilterByOptions.all & v != 0:
            return v

        raise ValueError("not a valid bit flag")


class SearchResult(pydantic.BaseModel):
    """ A single document response """
    id: int
    parent: Optional[int]
    title: str
    url: str
    description: str
    thumbnail: str
    tags: int
    rating: float


class SearchResults(pydantic.BaseModel):
    """ The results of the query search query. """
    status: int
    results: List[Union[SearchResult, List[SearchResult]]]


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
        methods=["POST"],
        response_model=SearchResults,
        tags=["Content API"],
    )
    async def search(self, payload: SearchPayload):
        if payload.tags != 0:
            filters = [FilterPayload(
                field_name="tags",
                filter_type="include",
                filter_field_type="bitfield",
                filter_val=payload.tags,
            )]
        else:
            filters = []

        if payload.order_by == "default":
            sort_by = None
        else:
            sort_by = "rating"

        to_engine = SearchQueryPayload(
            engine=payload.type,
            query=payload.query,
            fuzzy=payload.fuzzy,
            limit=payload.limit,
            filters=filters,
            sort_by=sort_by,
        )

        async with self.session.post(url=search_url, json=to_engine.dict()) as resp:
            if resp.status != 200:
                pprint(await resp.json())
                resp.raise_for_status()
            response = await resp.json()

        if payload.order_by == "rating-desc":
            response['data']['results'] = response['data']['results'][::-1]

        if payload.filter_by:
            # todo finish
            ...

        out = [expand_out_of_lists(item['doc']) for item in response['data']['results']]

        if payload.chunk != -1:
            out = list(chunk_n(
                out,
                payload.chunk,
            ))

        return SearchResults(
            status=200,
            results=out
        )


def setup(app):
    app.add_blueprint(SearchAPI(app))
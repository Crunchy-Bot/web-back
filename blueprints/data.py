from functools import reduce
from operator import or_

import asyncpg
import router

from pydantic import BaseModel, validator, conint
from typing import List, Optional

from server import Backend
from utils.responders import StandardResponse


class PayloadData(BaseModel):
    id: str = None
    title: str
    description: str
    rating: float
    img_url: str
    link: Optional[str] = None
    genres: int = 0

    @validator("rating")
    def convert_rating(cls, v):
        return round(v, 1)


class DataResponse(StandardResponse):
    data: PayloadData


class AnimeSearchResults(BaseModel):
    hits: List[dict]
    offset: int
    limit: int
    query: str


class AnimeSearchResponse(StandardResponse):
    data: AnimeSearchResults


class AnimeEndpoints(router.Blueprint):
    __base_route__ = "/data/anime"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/search",
        endpoint_name="Search Anime",
        methods=["GET"],
        response_model=AnimeSearchResponse,
        tags=["Anime"]
    )
    def search_anime(
        self,
        query: str,
        offset: conint(ge=0) = 0,
        limit: conint(gt=0, le=50) = 10,
    ):
        results = self.app.meili.anime.search(
            query,
            {
                'offset': offset,
                'limit': limit,
            },
        )

        return AnimeSearchResponse(status=200, data=dict(results))  # noqa

    @router.endpoint(
        "/{anime_id:str}",
        endpoint_name="Get Anime With Id",
        methods=["GET"],
        response_model=DataResponse,
        responses={
            404: {
                "model": StandardResponse
            }
        },
        tags=["Anime"]
    )
    async def get_anime_with_id(self, anime_id: str):
        row = await self.app.pool.fetchrow("""
            SELECT 
                id,
                title, 
                description, 
                rating, 
                img_url, 
                link, 
                genres
            FROM api_anime_data
            WHERE id = $1;
            """, anime_id)

        if row is None:
            return StandardResponse(
                status=404,
                data=f"no anime found with id: {anime_id!r}",
            ).into_response()

        return DataResponse(status=200, data=dict(row))  # noqa

    @router.endpoint(
        "/",
        endpoint_name="Add Anime",
        methods=["POST"],
        response_model=StandardResponse,
        responses={
            400: {
                "model": StandardResponse,
                "description": "The anime already exists with that title."
            }
        },
        tags=["Anime"]
    )
    async def add_anime(self, payload: PayloadData):
        fut = self.app.pool.fetchrow(
            """
            INSERT INTO api_anime_data (            
                id,
                title,
                description, 
                rating, 
                img_url, 
                link, 
                genres
            ) VALUES (random_string(18), $1, $2, $3, $4, $5, $6)
            RETURNING id;
            """,
            payload.title, payload.description,
            payload.rating, payload.img_url,
            payload.link, payload.genres,
        )

        try:
            row = await fut
        except asyncpg.UniqueViolationError:
            return StandardResponse(
                status=400,
                data=f"anime already exists with title: {payload.title!r}",
            )

        return StandardResponse(status=200, data=f"anime added with id: {row['id']!r}")


class MangaEndpoints(router.Blueprint):
    __base_route__ = "/data/manga"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/{manga_id:str}",
        endpoint_name="Get Manga With Id",
        methods=["GET"],
        response_model=DataResponse,
        responses={
            404: {
                "model": StandardResponse
            }
        },
        tags=["Anime"]
    )
    async def get_manga_with_id(self, manga_id: str):
        row = await self.app.pool.fetchrow("""
            SELECT 
                id,
                title, 
                description, 
                rating, 
                img_url, 
                link, 
                genres
            FROM api_manga_data
            WHERE id = $1;
            """, manga_id)

        if row is None:
            return StandardResponse(
                status=404,
                data=f"no manga found with id: {manga_id!r}",
            ).into_response()

        return DataResponse(status=200, data=dict(row))  # noqa


class GenreData(BaseModel):
    id: str
    name: str


class GenreResponse(StandardResponse):
    data: GenreData


class GenreFlagsResponse(StandardResponse):
    data: List[GenreData]


class FlagsResponse(StandardResponse):
    data: str


class GenreEndpoints(router.Blueprint):
    __base_route__ = "/data/genres"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/raw/{genre_id:int}",
        endpoint_name="Get Genre With Id",
        methods=["GET"],
        response_model=GenreResponse,
        responses={
            404: {
                "model": StandardResponse
            }
        },
        tags=["Genres"],
    )
    async def get_genre_with_id(self, genre_id: int):
        row = await self.app.pool.fetchrow("""
        SELECT id, name FROM api_genres WHERE id = $1;
        """, genre_id)

        if row is None:
            return StandardResponse(
                status=404,
                data=f"genre does not exist with id {genre_id!r}",
            ).into_response()

        return GenreResponse(status=200, data=dict(row))  # noqa

    @router.endpoint(
        "/raw/{genre_name:str}",
        endpoint_name="Get Genre With Name",
        methods=["GET"],
        response_model=GenreResponse,
        responses={
            404: {
                "model": StandardResponse
            }
        },
        tags=["Genres"],
    )
    async def get_genre_with_name(self, genre_name: str):
        row = await self.app.pool.fetchrow("""
        SELECT id, name FROM api_genres WHERE name = $1;
        """, genre_name)

        if row is None:
            return StandardResponse(
                status=404,
                data=f"genre does not exist with name {genre_name!r}",
            ).into_response()

        return GenreResponse(status=200, data=dict(row))  # noqa

    @router.endpoint(
        "/flags/{flags:int}",
        endpoint_name="Get Genres From Flags",
        methods=["GET"],
        response_model=GenreFlagsResponse,
        responses={
            404: {
                "model": StandardResponse
            }
        },
        tags=["Genres"],
    )
    async def get_genre_from_flags(self, flags: int):

        rows = await self.app.pool.fetch("""
        SELECT name FROM api_genres WHERE id & $1 != 0;
        """, flags)

        return GenreFlagsResponse(status=200, data=[row['name'] for row in rows])  # noqa

    @router.endpoint(
        "/flags",
        endpoint_name="Get Flags From Genres",
        methods=["GET"],
        response_model=GenreFlagsResponse,
        responses={
            404: {
                "model": StandardResponse
            }
        },
        tags=["Genres"],
    )
    async def flags_from_genres(self, genres: List[str]):
        if len(genres) == 0:
            return FlagsResponse(status=200, data='0')

        rows = await self.app.pool.fetch("""
        SELECT id FROM postgres.public.api_genres WHERE name = any($1::text[]);
        """, genres)

        mapper = [row['id'] for row in rows]

        flags = reduce(or_, mapper) if genres else 0
        return FlagsResponse(status=200, data=str(flags))


def setup(app):
    app.add_blueprint(AnimeEndpoints(app))
    app.add_blueprint(MangaEndpoints(app))
    app.add_blueprint(GenreEndpoints(app))







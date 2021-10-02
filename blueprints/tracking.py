import uuid
import asyncpg

import router

from typing import List, Optional
from pydantic import BaseModel, constr, AnyHttpUrl, UUID4
from fastapi.responses import ORJSONResponse

from server import Backend
from utils.responders import StandardResponse


class TagItem(BaseModel):
    title: constr(max_length=128, strip_whitespace=True)
    url: AnyHttpUrl = ""
    referer: Optional[int]
    description: constr(max_length=300, strip_whitespace=True) = ""


class TagItemsResponse(StandardResponse):
    data: List[TagItem]


class ItemInsertResponse(StandardResponse):
    data: str


class TagCreationPayload(BaseModel):
    tag_name: constr(min_length=1, max_length=32)
    description: constr(max_length=300) = ""


class UserTag(TagCreationPayload):
    tag_id: str


class UserTags(StandardResponse):
    data: List[UserTag]


class ItemCopy(BaseModel):
    title: str
    url: str


class ItemCopyResponse(StandardResponse):
    data: List[ItemCopy]


class TrackingBlueprint(router.Blueprint):
    __base_route__ = "/tracking"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}",
        endpoint_name="Create Tracking Tag",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Content Tracking"]
    )
    async def create_tag(
            self,
            user_id: int,
            tag_id: str,
            payload: TagCreationPayload,
    ):
        """ Creates a tag for a given user. """
        # todo auth

        await self.app.pool.execute("""
            INSERT INTO user_tracking_tags (user_id, tag_id, tag_name, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, tag_id)
            DO UPDATE SET description = EXCLUDED.description;
        """, user_id, tag_id, payload.tag_name, payload.description)

        return StandardResponse(status=200, data="successfully updated / created tag")

    @router.endpoint(
        "/{user_id:int}/tags",
        endpoint_name="Get All User Tags",
        methods=["GET"],
        response_model=UserTags,
        tags=["Content Tracking"]
    )
    async def get_all_user_tags(self, user_id: int):
        results = await self.app.pool.fetch("""
            SELECT tag_name, tag_id, description
            FROM user_tracking_tags
            WHERE user_id = $1;
        """, user_id)

        return UserTags(status=200, data=list(map(dict, results)))  # noqa

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}",
        endpoint_name="Delete Tracking Tag",
        methods=["DELETE"],
        response_model=StandardResponse,
        tags=["Content Tracking"],
    )
    async def delete_tag(self, user_id: int, tag_id: str):
        """ Deletes a given tag for a given user. """
        # todo auth

        await self.app.pool.execute("""
            DELETE FROM user_tracking_tags 
            WHERE user_id = $1 AND tag_id = $2;
        """, user_id, tag_id)

        return StandardResponse(status=200, data="successfully deleted tag")

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}",
        endpoint_name="Get Tag Items",
        methods=["GET"],
        response_model=TagItemsResponse,
        tags=["Content Tracking"],
    )
    async def list_items(self, user_id: int, tag_id: str):
        """ Lists the items in the given tag id for the given user id. """

        results = await self.app.pool.fetch("""
            SELECT title, url, referer, description
            FROM user_tracking_items
            WHERE user_id = $1 AND tag_id = $2
        """, user_id, tag_id)

        return TagItemsResponse(status=200, data=list(map(dict, results)))  # noqa

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}/edit",
        endpoint_name="Add Tag Item",
        methods=["POST"],
        response_model=ItemInsertResponse,
        responses={
            404: {"model": StandardResponse}
        },
        tags=["Content Tracking"],
    )
    async def add_item(
        self,
        user_id: int,
        tag_id: str,
        payload: TagItem,
    ):
        """ Adds an item to the given tag for the given user. """
        # todo auth

        count = await self.app.pool.fetchrow(
            """
            SELECT COUNT(id) AS total
            FROM user_tracking_items 
            WHERE user_id = $1 AND tag_id = $2;
            """,
            user_id, tag_id
        )

        if count['total'] >= 20:
            return ORJSONResponse(StandardResponse(status=400, data="Max items already exists"))

        fut = self.app.pool.fetchrow(
            """
            INSERT INTO user_tracking_items (
                id,
                user_id, 
                tag_id, 
                title, 
                url,
                referer, 
                description
            ) VALUES ($1, $2, $3, $4, $5, $6, $7) 
            RETURNING id;
            """,
            uuid.uuid4(), user_id, tag_id, payload.title,
            payload.url, payload.referer, payload.description
        )

        try:
            res = await fut
        except asyncpg.ForeignKeyViolationError:
            msg = StandardResponse(
                status=404,
                data=f"no tag exists with id: {tag_id} for user: {user_id}",
            )
            return ORJSONResponse(msg.dict(), status_code=404)

        return ItemInsertResponse(status=200, data=str(res['id']))

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}/edit",
        endpoint_name="Delete Tag Item",
        methods=["DELETE"],
        response_model=StandardResponse,
        tags=["Content Tracking"],
    )
    async def remove_item(self, user_id: int, tag_id: str, tracking_id: UUID4):
        """ Remove an item from a given tag for the given user. """

        await self.app.pool.execute("""
            DELETE FROM user_tracking_items 
            WHERE 
                user_id = $1 AND 
                tag_id = $2 AND
                id = $3;
        """, user_id, tag_id, tracking_id)

        return StandardResponse(status=200, data="item deleted if exists")

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}/copy",
        endpoint_name="Copy Tag items",
        methods=["POST"],
        response_model=ItemCopyResponse,
        tags=["Content Tracking"]
    )
    async def copy_items(self, user_id: int, tag_id: str, copy_to: int):
        """
        Copies the items in a given tag for a given
        user to another user id.

        **This does not copy referer ids**
        """

        await self.app.pool.execute("""
            INSERT INTO user_tracking_tags (user_id, tag_id, description) 
            SELECT $3, tag_id, description
            FROM user_tracking_tags 
            WHERE user_id = $1 AND tag_id = $2;
        """, user_id, tag_id, copy_to)

        existing_rows = await self.app.pool.fetch("""
            SELECT tag_id, title, url, description
            FROM user_tracking_items 
            WHERE user_id = $1 AND tag_id = $2;
        """, user_id, tag_id)

        def alter(row):
            return (
                uuid.uuid4(),
                copy_to,
                row['tag_id'],
                row['title'],
                row['url'],
                row['description'],
            )

        new_results = map(alter, existing_rows)
        transferred = map(dict, existing_rows)

        await self.app.pool.executemany("""
            INSERT INTO user_tracking_items (
                id, 
                user_id, 
                tag_id, 
                title, 
                url, 
                description
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """, new_results)

        return ItemCopyResponse(status=200, data=transferred)  # noqa


def setup(app):
    app.add_blueprint(TrackingBlueprint(app))

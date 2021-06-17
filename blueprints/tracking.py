from typing import List

import asyncpg
import uuid

import router

from pydantic import BaseModel, constr, AnyHttpUrl, UUID4
from fastapi.responses import ORJSONResponse

from server import Backend
from utils.responders import (
    StandardResponse,
    TagItemsResponse,
    ItemInsertResponse,
)


class TagCreationPayload(BaseModel):
    description: constr(max_length=300)


TAG_DEFAULT = TagCreationPayload(description="")


class ItemCreationPayload(BaseModel):
    title: constr(max_length=128, strip_whitespace=True)
    url: AnyHttpUrl
    referer: int
    description: constr(max_length=300, strip_whitespace=True)


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
        endpoint_name="Create / Edit Tracking Tag",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Content Tracking"]
    )
    async def create_tag(
        self,
        user_id: int,
        tag_id: str,
        payload: TagCreationPayload = TAG_DEFAULT,
    ):
        """ Creates a tag for a given user. """
        # todo auth

        await self.app.pool.execute("""
            INSERT INTO user_tracking_tags (user_id, tag_id, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, tag_id)
            DO UPDATE SET description = EXCLUDED.description;
        """, user_id, tag_id, payload.description)

        return StandardResponse(status=200, data="successfully updated / created tag")

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
        payload: ItemCreationPayload,
    ):
        """ Adds an item to the given tag for the given user. """
        # todo auth

        fut = self.app.pool.fetchrow(
            """
            INSERT INTO user_tracking_items (
                _id,
                user_id, 
                tag_id, 
                title, 
                url,
                referer, 
                description
            ) VALUES ($1, $2, $3, $4, $5, $6, $7) 
            RETURNING _id;
            """,
            uuid.uuid4(), user_id, tag_id, payload.title,
            payload.url, int(payload.referer), payload.description
        )

        try:
            res = await fut
        except asyncpg.ForeignKeyViolationError:
            msg = StandardResponse(
                status=404,
                data=f"no tag exists with id: {tag_id} for user: {user_id}",
            )
            return ORJSONResponse(msg.dict(), status_code=404)

        return ItemInsertResponse(status=200, data=str(res['_id']))

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}/edit",
        endpoint_name="Delete Tag Item",
        methods=["DELETE"],
        response_model=StandardResponse,
        tags=["Content Tracking"],
    )
    async def remove_item(self, user_id: int, tag_id: str, tracking_id: UUID4):
        """ Remove an item from a given tag for the given user. """

        # todo auth

        await self.app.pool.execute("""
            DELETE FROM user_tracking_items 
            WHERE 
                user_id = $1 AND 
                tag_id = $2 AND
                _id = $3;
        """, user_id, tag_id, tracking_id)

        return StandardResponse(status=200, data="item deleted if exists")

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}/copy",
        endpoint_name="Copy Tag items",
        methods=["POST"],
        response_model=ItemCopyResponse,
        tags=["Content Tracking"]
    )
    async def copy_items(self, user_id: int):
        """
        Copies the items in a given tag for a given
        user to another user id.
        """


def setup(app):
    app.add_blueprint(TrackingBlueprint(app))

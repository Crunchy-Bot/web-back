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


class TrackingBlueprint(router.Blueprint):
    __base_route__ = "/tracking"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}",
        endpoint_name="Create / Edit Tracking Tag",
        methods=["POST"],
    )
    async def create_tag(
        self,
        user_id: int,
        tag_id: str,
        payload: TagCreationPayload = TAG_DEFAULT,
    ):
        # todo auth

        await self.app.pool.execute("""
            INSERT INTO tracking_tags (user_id, tag_id, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, tag_id)
            DO UPDATE SET description = EXCLUDED.description;
        """, user_id, tag_id, payload.description)

        return StandardResponse(status=200, data="successfully updated / created tag")

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}",
        endpoint_name="Delete Tracking Tag",
        methods=["DELETE"],
    )
    async def delete_tag(self, user_id: int, tag_id: str):
        # todo auth

        await self.app.pool.execute("""
            DELETE FROM tracking_tags 
            WHERE user_id = $1 AND tag_id = $2;
        """, user_id, tag_id)

        return StandardResponse(status=200, data="successfully deleted tag")

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}",
        endpoint_name="Get Tag Items",
        methods=["GET"],
    )
    async def list_items(self, user_id: int, tag_id: str):
        results = await self.app.pool.fetch("""
            SELECT title, url, referer, description
            FROM tracking_items
            WHERE user_id = $1 AND tag_id = $2
        """, user_id, tag_id)

        return TagItemsResponse(status=200, data=list(map(dict, results)))  # noqa

    @router.endpoint(
        "/{user_id:int}/{tag_id:str}/edit",
        endpoint_name="Add Tag Item",
        methods=["POST"],
    )
    async def add_item(
        self,
        user_id: int,
        tag_id: str,
        payload: ItemCreationPayload,
    ):
        # todo auth

        fut = self.app.pool.fetchrow(
            """
            INSERT INTO tracking_items (
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
        endpoint_name="DELETE Tag Item",
        methods=["DELETE"],
    )
    async def delete_item(self, user_id: int, tag_id: str, tracking_id: UUID4):
        # todo auth

        await self.app.pool.execute("""
            DELETE FROM tracking_items 
            WHERE 
                user_id = $1 AND 
                tag_id = $2 AND
                _id = $3;
        """, user_id, tag_id, tracking_id)

        return StandardResponse(status=200, data="item deleted if exists")

def setup(app):
    app.add_blueprint(TrackingBlueprint(app))
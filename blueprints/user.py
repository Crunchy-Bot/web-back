import aiohttp
import pydantic
import router
import logging

from typing import Optional
from fastapi import Request
from fastapi.responses import ORJSONResponse
from server import Backend
from utils.settings import (
    discord_cdn_avatar,
    discord_user,
    discord_oauth2_token,
    client_id,
    client_secret,
    redirect_url,
)

logger = logging.getLogger("api-users")


class User(pydantic.BaseModel):
    id: int
    username: str
    avatar: str

    def avatar_url(self, size=128):
        return discord_cdn_avatar.format(self.id, self.avatar, size)


class UserAPI(router.Blueprint):
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
        "/me",
        endpoint_name="Who Am I",
        description=(
            "Returns any data representing you the user."
        ),
        methods=["GET"],
        tags=["User API"],
    )
    async def me(self, request: Request):
        maybe_user = request.session.get("user")

        if maybe_user is None:
            return {"isAuthed": False}

        user = User(*maybe_user)

        return {
            "isAuthed": True,
            "name": user.username,
            "avatar": user.avatar_url()
        }

    @router.endpoint(
        "/authorize",
        endpoint_name="Authorize Me",
        description=(
            "Attempts to authorize a user of a given code."
        ),
        methods=["POST"],
        tags=["User API"],
    )
    async def authorize(self, request: Request, code: str):
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_url,
            'scope': 'identify'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with self.session.post(
            discord_oauth2_token,
            data=data,
            headers=headers,
        ) as resp:

            if resp.status >= 400:
                logger.critical(
                    f"Discord API gave none 200 response on token request:"
                    f" {resp.status} payload: {resp}")
                return ORJSONResponse({
                    "status": 500,
                    "message": "failed to request token information from discord"
                }, status_code=500)

            access_token = (await resp.json())['access_token']

        async with self.session.get(
            discord_user,
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:

            if resp.status >= 400:
                logger.critical(
                    f"Discord API gave none 200 response on user request: "
                    f"{resp.status} payload: {resp}")
                return ORJSONResponse({
                    "status": 500,
                    "message": "failed to request user information from discord"
                }, status_code=500)

            user = await resp.json()
            user = User(**user)
            request.session['user'] = user.dict()
            return ORJSONResponse({
                "status": 200,
                "message": "successful authorization!"
            }, status_code=200)


def setup(app):
    app.add_blueprint(UserAPI(app))
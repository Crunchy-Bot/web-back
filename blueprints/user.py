import aiohttp

import router
from typing import Optional
from server import Backend


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
        endpoint_name="Me Endpoints",
        description=(
            "Returns any data representing you the user."
        ),
        methods=["GET"],
        tags=["User API"],
    )
    async def me(self):
        return {"isAuthed": False}


def setup(app):
    app.add_blueprint(UserAPI(app))
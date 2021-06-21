import typing as t
import os
import router
import utils

from fastapi import Request, Response
from fastapi.responses import ORJSONResponse
from server import Backend

BASE_PATH = "/v0"

APP_FILES = [
    f"blueprints.{name[:-3]}"
    for name in os.listdir("./blueprints")
    if not name.startswith("__")
]

ORIGINS = {
    "http://127.0.0.1:9990",
    "http://127.0.0.1:3000",
    "https://api.crunchy.gg",
    "https://crunchy.gg",
}


def import_callback(app_: Backend, endpoint: t.Union[router.Endpoint, router.Websocket]):
    if isinstance(endpoint, router.Endpoint):
        app_.add_api_route(
            f"{BASE_PATH}{endpoint.route}",
            endpoint.callback,
            name=endpoint.name,
            methods=endpoint.methods,
            **endpoint.extra)
    else:
        raise NotImplementedError()


tags_metadata = [
    {
        "name": "Getting Started",
        "description": utils.read_md("./docs/getting_started.md"),
    },
    {
        "name": "Rate Limits",
        "description": utils.read_md("./docs/rate_limits.md"),
    },
]


app = Backend(
    title="Crunchy.gg API",
    description=utils.read_md("./docs/welcome.md"),
    version="0.0.1",
    docs_url=None,
    redoc_url="/v0",
    openapi_url="/v0/openapi.json",
    openapi_tags=tags_metadata,
)


@app.on_event("startup")
async def start():
    ...


if __name__ != '__main__':
    router = router.Router(app, APP_FILES, import_callback)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app")

import typing as t
import os
import uvicorn
import router
import utils

from server import Backend
from fastapi.middleware.cors import CORSMiddleware


BASE_PATH = "/v0"

APP_FILES = [
    f"blueprints.{name[:-3]}"
    for name in os.listdir("./blueprints")
    if not name.startswith("__")
]

ORIGINS = [
    "http://127.0.0.1:8080",
    "https://api.crunchy.gg",
    "https://crunchy.gg",
]


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
    redoc_url="/v0/docs",
    openapi_url="/v0/openapi.json",
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start():
    ...

if __name__ != '__main__':
    router = router.Router(app, APP_FILES, import_callback)

if __name__ == '__main__':
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        # workers=mp.cpu_count()
    )
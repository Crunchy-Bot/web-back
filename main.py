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
    redoc_url="/v0/docs",
    openapi_url="/v0/openapi.json",
    openapi_tags=tags_metadata,
)


def check_routes(request: Request):
    # Using FastAPI instance
    url_list = [
        route.path
        for route in request.app.routes
        if "rest_of_path" not in route.path
    ]
    if request.url.path not in url_list:
        return ORJSONResponse({"detail": "Not Found"}, 404)


# Handle CORS preflight requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str) -> Response:
    response = check_routes(request)
    if response:
        return response

    origin = request.headers.get('Origin')
    if origin is None:
        return response

    response = Response(
        content="OK",
        media_type="text/plain",
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )
    return response


@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = check_routes(request)
    if response:
        return response

    response = await call_next(request)

    origin = request.headers.get('Origin')
    if origin is None:
        return response

    if origin in ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.on_event("startup")
async def start():
    ...

if __name__ != '__main__':
    router = router.Router(app, APP_FILES, import_callback)

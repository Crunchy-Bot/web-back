from typing import Optional
from uuid import uuid4

from fastapi import Request, FastAPI, responses
from itsdangerous import URLSafeSerializer
from aioredis import create_pool, ConnectionsPool, RedisConnection
from orjson import dumps, loads

from utils import settings


class SessionCollection:
    """
    A collection of sessions that can implement and manage sessions of
    individual requests and link them back to the request.
    """

    def __init__(self):
        self._cache: Optional[ConnectionsPool] = None
        self._serializer = URLSafeSerializer(settings.secure_key, "ree")

    def mount_middleware(self, app: FastAPI):
        """ Mounts self to a given FastAPI app in the form of middleware """
        app.middleware("http")(self.as_middleware)
        app.on_event("startup")(self.on_start)
        app.on_event("shutdown")(self.on_shutdown)

    async def on_start(self):
        self._cache = await create_pool(
            settings.cache_uri
        )

    async def on_shutdown(self):
        if self._cache is not None:
            self._cache.close()

    async def as_middleware(self, request: Request, call_next):
        maybe_session = request.cookies.get("session")
        print(maybe_session)
        if maybe_session is not None:
            id_ = maybe_session
            async with self._cache.get() as conn:
                sess = await conn.execute("GET", id_)
                if sess is None:
                    sess = {}
                else:
                    sess = loads(sess)
        else:
            id_ = str(uuid4())
            sess = {}

        print(sess)

        request.scope['session'] = sess
        resp: responses.Response = await call_next(request)

        async with self._cache.get() as conn:
            conn: RedisConnection = conn
            await conn.execute("SET", id_, dumps(request.scope['session']))

        resp.set_cookie(
            "session",
            id_,
            secure=settings.secure_sessions,
        )

        return resp


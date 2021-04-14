from fastapi import Request, FastAPI, responses
from itsdangerous import URLSafeSerializer

from utils import settings


class SessionCollection:
    """
    A collection of sessions that can implement and manage sessions of
    individual requests and link them back to the request.
    """

    def __init__(self):
        self._serializer = URLSafeSerializer(settings.secure_key, "ree")

    def mount_middleware(self, app: FastAPI):
        """ Mounts self to a given FastAPI app in the form of middleware """
        app.middleware("http")(self.as_middleware)

    async def as_middleware(self, request: Request, call_next):
        maybe_session = request.cookies.get("session")
        if maybe_session is not None:
            sess = self._serializer.loads(maybe_session)
        else:
            sess = {}

        request.scope['session'] = sess
        resp: responses.Response = await call_next(request)

        resp.set_cookie(
            "session",
            self._serializer.dumps(request.scope['session']),
            secure=settings.secure_sessions,
        )

        return resp


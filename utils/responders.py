from pydantic import BaseModel
from typing import Any, List
from fastapi.responses import ORJSONResponse


class StandardResponse(BaseModel):
    status: int
    data: Any = None

    def into_response(self):
        return ORJSONResponse(self, status_code=self.status)



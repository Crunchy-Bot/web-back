from pydantic import BaseModel
from typing import Any, List


class StandardResponse(BaseModel):
    status: int
    data: Any = None


class TagItem(BaseModel):
    title: str
    url: str
    referer: str
    description: str


class TagItemsResponse(StandardResponse):
    data: List[TagItem]


class ItemInsertResponse(StandardResponse):
    data: str

from pydantic import BaseModel


class GeneralMessage(BaseModel):
    message: str

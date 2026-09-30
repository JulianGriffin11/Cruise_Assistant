import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    cruise_id: uuid.UUID | None = None
    history: list[ChatTurn] = Field(default_factory=list)

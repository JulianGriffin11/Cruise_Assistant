import uuid

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cruise_id: uuid.UUID
    filename: str
    page_count: int | None
    status: str
    error_message: str | None

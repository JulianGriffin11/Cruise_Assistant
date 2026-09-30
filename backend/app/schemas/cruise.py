import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class CruiseCreate(BaseModel):
    name: str
    year: int
    start_date: date | None = None
    end_date: date | None = None


class CruiseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    year: int
    start_date: date | None
    end_date: date | None

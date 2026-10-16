
from pydantic import BaseModel, ConfigDict


class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    price: float

    model_config = ConfigDict(from_attributes=True)
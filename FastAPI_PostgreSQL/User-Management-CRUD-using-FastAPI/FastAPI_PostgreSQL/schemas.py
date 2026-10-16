from pydantic import BaseModel
class ItemCreate(BaseModel):
    name: str
    description: str
    price: float
class ItemResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    class Config:
        from_attributes = True
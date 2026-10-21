# src/categorical_chatbot/schemas/chat_schema.py
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000,
    )

    session_id: str | None = Field(
        default=None,
        max_length=100,
    )


class ChatResponse(BaseModel):
    session_id: str
    categories: list[str]
    response: str
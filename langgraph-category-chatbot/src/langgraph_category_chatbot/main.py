from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .chat_service import (
    process_chat,
    get_chat_history,
)

app = FastAPI(
    title="Category-Based LangGraph Chatbot",
    description=(
        "A chatbot with category detection, "
        "category-specific responses, and chat history."
    ),
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    session_id: Optional[id] = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        return process_chat(
            message=request.message,
            session_id=request.session_id,
        )
    except Exception as exc:
        # Log the actual exception server-side in production.
        raise HTTPException(
            status_code=502,
            detail="Unable to generate a response. Please try again.",
        ) from exc


@app.get("/history/{session_id}")
def chat_history(session_id: str):
    history = get_chat_history(session_id)

    if not history:
        raise HTTPException(
            status_code=404,
            detail="Session not found or no messages available.",
        )

    return {
        "session_id": session_id,
        "history": history,
    }
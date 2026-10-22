# src/categorical_chatbot/routers/chat_router.py
import logging

from fastapi import APIRouter, HTTPException, status

from categorical_chatbot.schema import (
    ChatRequest,
    ChatResponse,
)
from categorical_chatbot.service import process_chat

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await process_chat(
            session_id=request.session_id,
            message=request.message,
        )

        logger.info(
            "Chat completed successfully for session %s",
            result["session_id"],
        )

        return ChatResponse(**result)

    except ValueError as exc:
        logger.warning("Invalid chat request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The chatbot could not process this message. "
                "Check the application terminal for details."
            ),
        ) from exc

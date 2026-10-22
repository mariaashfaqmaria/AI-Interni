
# src/categorical_chatbot/utils/logging_config.py

import logging

from sqlalchemy import select

from database import AsyncSessionLocal
from categorical_chatbot.model import ChatMessage


# Logging configuration

def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


logger = logging.getLogger(__name__)


# Get chat history for a given session ID and log the number of messages retrieved.

async def get_history(
    session_id: str,
) -> list[dict[str, str]]:
    async with AsyncSessionLocal() as db:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id
            )
            .order_by(
                ChatMessage.turn_index.asc(),
                ChatMessage.id.asc(),
            )
        )

        result = await db.execute(statement)
        messages = result.scalars().all()

        logger.info(
            "Retrieved %s messages for session %s",
            len(messages),
            session_id,
        )

        return [
            {
                "role": item.role,
                "content": item.content,
            }
            for item in messages
        ]

# Save a chat turn (user message and assistant response) to the database and log the operation.

async def save_turn(
    session_id: str,
    turn_index: int,
    user_message: str,
    assistant_response: str,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            db.add_all(
                [
                    ChatMessage(
                        session_id=session_id,
                        turn_index=turn_index,
                        role="user",
                        content=user_message,
                    ),
                    ChatMessage(
                        session_id=session_id,
                        turn_index=turn_index,
                        role="assistant",
                        content=assistant_response,
                    ),
                ]
            )

            await db.commit()

            logger.info(
                "Saved chat turn %s for session %s",
                turn_index,
                session_id,
            )

        except Exception:
            await db.rollback()

            logger.exception(
                "Failed to save chat turn %s for session %s",
                turn_index,
                session_id,
            )

            raise
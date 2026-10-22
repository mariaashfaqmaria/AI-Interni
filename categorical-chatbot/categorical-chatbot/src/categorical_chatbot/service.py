
# src/categorical_chatbot/services/chat_service.py

import json
import logging
import re
from uuid import uuid4

from categorical_chatbot.model import chat_model
from categorical_chatbot.prompt import (
    CATEGORIES,
    get_category_prompt,
    get_response_prompt,
)
from categorical_chatbot.utils.logging_config import (
    get_history,
    save_turn,
)

logger = logging.getLogger(__name__)


# Category Detector

async def detect_categories(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> list[str]:
    """Classify a customer message into supported categories."""

    prompt = get_category_prompt(message)

    logger.info("Classifying current message")

    result = await chat_model.ainvoke(prompt)

    raw = (
        result.content
        if hasattr(result, "content")
        else str(result)
    )
    raw = raw.strip()

    # Remove optional Markdown code fences.
    cleaned = re.sub(
        r"\A```(?:json)?\s*|\s*```\s*\Z",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()

    categories = []

    # First attempt: parse JSON.
    try:
        data = json.loads(cleaned)

        if isinstance(data, dict):
            categories = data.get("categories", [])
        elif isinstance(data, list):
            categories = data

        if isinstance(categories, str):
            categories = [categories]

    except (json.JSONDecodeError, TypeError):
        logger.warning(
            "Model returned non-JSON category output"
        )

    # Keep only supported categories in the defined order.
    if isinstance(categories, list):
        valid = [
            category
            for category in CATEGORIES
            if any(
                isinstance(item, str)
                and item.strip().casefold() == category.casefold()
                for item in categories
            )
        ]

        if valid:
            return valid

    # Fallback: recover category names from the raw output.
    found = [
        category
        for category in CATEGORIES
        if re.search(
            rf"(?<!\w){re.escape(category)}(?!\w)",
            raw,
            flags=re.IGNORECASE,
        )
    ]

    if found:
        logger.warning(
            "Recovered categories from model output"
        )
        return found

    logger.warning(
        "Could not identify a valid category; using General"
    )

    return ["General"]


# Response Generation

async def generate_response(
    message: str,
    categories: list[str],
    history: list[dict[str, str]],
) -> str:
    """Generate a customer-support response using the LLM."""

    prompt = get_response_prompt(
        message=message,
        categories=categories,
        history=history,
    )

    logger.info(
        "Sending response-generation request to OpenRouter"
    )

    result = await chat_model.ainvoke(prompt)

    answer = (
        result.content
        if hasattr(result, "content")
        else str(result)
    )

    if isinstance(answer, list):
        answer = "\n".join(
            str(item.get("text", ""))
            if isinstance(item, dict)
            else str(item)
            for item in answer
        )

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(
            "The language model returned an empty response."
        )

    logger.info("Received response from OpenRouter")

    return answer.strip()


# Chat Service

async def process_chat(
    message: str,
    session_id: str | None = None,
) -> dict:
    """
    Process a customer message, detect its categories,
    generate a response, and save the conversation to PostgreSQL.
    """

    message = message.strip()

    if not message:
        raise ValueError("Message cannot be empty.")

    if session_id is None:
        session_id = str(uuid4())
    else:
        session_id = session_id.strip()

        if not session_id:
            raise ValueError("Session ID cannot be empty.")

        if len(session_id) > 100:
            raise ValueError(
                "Session ID cannot exceed 100 characters."
            )

    logger.info(
        "Retrieving PostgreSQL history for session %s",
        session_id,
    )

    history = await get_history(session_id)

    logger.info(
        "Retrieved %d history messages",
        len(history),
    )

    # Detect categories for the current message.
    categories = await detect_categories(
        message=message,
        history=history,
    )

    logger.info(
        "Detected categories: %s",
        categories,
    )

    # Generate a response using conversation history.
    response = await generate_response(
        message=message,
        categories=categories,
        history=history,
    )

    # Preserve the existing turn-index calculation.
    next_turn = len(history) // 2 + 1

    logger.info("Saving completed turn to PostgreSQL")

    await save_turn(
        session_id=session_id,
        turn_index=next_turn,
        user_message=message,
        assistant_response=response,
    )

    return {
        "session_id": session_id,
        "categories": categories,
        "response": response,
    }
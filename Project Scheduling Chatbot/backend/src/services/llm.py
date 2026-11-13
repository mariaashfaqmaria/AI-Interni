# backend/src/services/llm.py
"""LangChain chat model (OpenRouter via the OpenAI-compatible API) + structured-output helper.
Returns None when no API key / on error so callers can fall back."""
import logging
from functools import lru_cache
from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


@lru_cache
def _build(api_key: str, model: str, base_url: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
        max_tokens=2048,
        max_retries=2,
        default_headers={"X-Title": "Project Scheduling Chatbot"},  # optional OpenRouter attribution
    )


def get_llm() -> ChatOpenAI | None:
    s = get_settings()
    return _build(s.openrouter_api_key, s.openrouter_model, s.openrouter_base_url) if s.openrouter_api_key else None


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)


def structured(schema: type[T], system: str, user: str) -> T | None:
    """Structured output via tool-calling; free OpenRouter models may not support it, so failures fall back to templates."""
    llm = get_llm()
    if not llm:
        return None
    try:
        return llm.with_structured_output(schema).invoke([SystemMessage(content=system), HumanMessage(content=user)])
    except Exception:
        log.exception("Structured LLM call failed; using fallback")
        return None

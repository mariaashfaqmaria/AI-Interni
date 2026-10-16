from typing import TypedDict


class ChatState(TypedDict):
    question: str
    history: list[dict[str, str]]
    categories: list[str]
    answer: str
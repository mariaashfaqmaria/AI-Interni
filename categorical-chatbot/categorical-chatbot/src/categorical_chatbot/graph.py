
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from categorical_chatbot.service import (
    detect_categories,
    generate_response,
)

# ChatState

class ChatState(TypedDict):
    session_id: str
    message: str
    history: list[dict[str, str]]
    categories: list[str]
    response: str

# Classify Node

async def classify_node(state: ChatState) -> dict:
    categories = await detect_categories(
        message=state["message"],
        history=state["history"],
    )

    return {"categories": categories}

# Response Node

async def response_node(state: ChatState) -> dict:
    response = await generate_response(
        message=state["message"],
        categories=state["categories"],
        history=state["history"],
    )

    return {"response": response}


# Graph Workflow

def build_graph():
    builder = StateGraph(ChatState)

    builder.add_node("classify_query", classify_node)
    builder.add_node("generate_response", response_node)

    builder.add_edge(START, "classify_query")
    builder.add_edge("classify_query", "generate_response")
    builder.add_edge("generate_response", END)

    return builder.compile()

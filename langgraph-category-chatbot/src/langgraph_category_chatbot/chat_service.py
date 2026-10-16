from uuid import uuid4

from .graph import chat_graph


conversation_store: dict[
    str, list[dict[str, str]]
] = {}


def process_chat(
    message: str,
    session_id: id | None = None,
) -> dict:

    if session_id is None:
        session_id = str(uuid4())

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    history = conversation_store[session_id]

    # Run the graph using prior conversation history.
    result = chat_graph.invoke({
        "question": message,
        "history": history.copy(),
        "categories": [],
        "answer": "",
    })

    # Append the current turn after generation.
    history.append({
        "role": "user",
        "content": message,
    })

    history.append({
        "role": "assistant",
        "content": result["answer"],
    })

    return {
        "session_id": session_id,
        "question": message,
        "categories": result["categories"],
        "answer": result["answer"],
        "history": history.copy(),
    }


def get_chat_history(session_id: str) -> list[dict[str, str]]:
    return conversation_store.get(session_id, []).copy()
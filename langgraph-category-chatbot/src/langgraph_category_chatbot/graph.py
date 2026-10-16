from langgraph.graph import StateGraph, START, END

from .state import ChatState
from .category_detector import detect_categories
from .response_generator import generate_answer


def category_detection_node(state: ChatState):
    categories = detect_categories(
        question=state["question"],
        history=state["history"],
    )

    return {"categories": categories}


def response_generation_node(state: ChatState):
    answer = generate_answer(
        question=state["question"],
        history=state["history"],
        categories=state["categories"],
    )

    return {"answer": answer}


def build_graph():
    workflow = StateGraph(ChatState)

    workflow.add_node(
        "detect_category",
        category_detection_node,
    )

    workflow.add_node(
        "generate_response",
        response_generation_node,
    )

    workflow.add_edge(START, "detect_category")

    workflow.add_edge(
        "detect_category",
        "generate_response",
    )

    workflow.add_edge("generate_response", END)

    return workflow.compile()


chat_graph = build_graph()
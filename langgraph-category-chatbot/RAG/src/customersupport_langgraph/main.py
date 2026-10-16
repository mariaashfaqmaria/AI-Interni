
import re
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# STEP 1: Define the state
class CustomerSupportState(TypedDict):
    user_query: str
    category: str
    response: str


# STEP 2: Define keyword and phrase patterns
BILLING_PATTERNS = [
    r"\bpayment\b",
    r"\bpaid\b",
    r"\bpay\b",
    r"\bcharged\b",
    r"\bdeducted\b",
    r"\brefund\b",
    r"\breimburse(?:ment)?\b",
    r"\btransaction\b",
    r"\bbilling\b",
    r"\binvoice\b",
    r"\bcredit card\b",
    r"\bdebit card\b",
    r"\bwallet\b",
    r"\bsubscription\b",
    r"\border confirmation\b",
    r"\bpayment confirmation\b",
    r"\bdouble charged\b",
    r"\bmoney\b",
    r"\bprice deducted\b",
    r"\bpayment failed\b",
]

TECHNICAL_PATTERNS = [
    r"\bbug\b",
    r"\berror\b",
    r"\bcrash(?:es|ed|ing)?\b",
    r"\bnot working\b",
    r"\bdoesn't work\b",
    r"\bdoes not work\b",
    r"\bwon't open\b",
    r"\bcannot open\b",
    r"\bcan't open\b",
    r"\bslow\b",
    r"\bloading\b",
    r"\bfrozen\b",
    r"\bfreezes\b",
    r"\bhangs\b",
    r"\blog ?in\b",
    r"\bsign ?in\b",
    r"\bpassword reset\b",
    r"\bconnectivity\b",
    r"\bconnection issue\b",
    r"\bserver\b",
    r"\binstall(?:ation)?\b",
    r"\bupdate failed\b",
    r"\btechnical issue\b",
    r"\bexception\b",
    r"\bapi\b",
    r"\bdatabase\b",
    r"\bcode\b",
    r"\bpython\b",
    r"\blanggraph\b",
]

GREETING_PATTERNS = [
    r"\bhi\b",
    r"\bhello\b",
    r"\bhey\b",
    r"\bgood morning\b",
    r"\bgood afternoon\b",
    r"\bgood evening\b",
    r"\bgreetings\b",
]


def matches_any(query: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, query) for pattern in patterns)


# STEP 3: Classify the query
def classify_query(state: CustomerSupportState):
    query = state["user_query"].strip().lower()

    # Empty queries are handled safely
    if not query:
        category = "general"

    # Priority 1: Payment and order-payment problems
    elif matches_any(query, BILLING_PATTERNS):
        category = "billing"

    # Priority 2: Technical problems
    elif matches_any(query, TECHNICAL_PATTERNS):
        category = "technical"

    # Priority 3: Greeting-only messages
    elif (
        matches_any(query, GREETING_PATTERNS)
        and len(query.split()) <= 5
        and not any(
            word in query
            for word in ["?", "problem", "help", "issue", "please"]
        )
    ):
        category = "greeting"

    # Priority 4: Everything else
    else:
        category = "general"

    return {"category": category}


# STEP 4: Create response nodes
def greeting_response(state: CustomerSupportState):
    return {
        "response": "Hello! How can I help you today?"
    }


def technical_response(state: CustomerSupportState):
    return {
        "response": (
            "I'm sorry you're experiencing a technical issue. "
            "Please describe the problem, including any error message "
            "and the steps that cause it."
        )
    }


def billing_response(state: CustomerSupportState):
    return {
        "response": (
            "I'm sorry about the payment issue. Please share the "
            "transaction status, order ID if available, and whether "
            "the amount was deducted. Do not share your full card "
            "number, password, or security code."
        )
    }


def general_response(state: CustomerSupportState):
    return {
        "response": (
            "Thank you for contacting support. Could you provide "
            "a little more detail so I can direct your query correctly?"
        )
    }


# STEP 5: Define conditional routing
def route_query(state: CustomerSupportState):
    return state["category"]


# STEP 6: Build the LangGraph
builder = StateGraph(CustomerSupportState)

builder.add_node("classify_query", classify_query)
builder.add_node("greeting_response", greeting_response)
builder.add_node("technical_response", technical_response)
builder.add_node("billing_response", billing_response)
builder.add_node("general_response", general_response)

builder.add_edge(START, "classify_query")

builder.add_conditional_edges(
    "classify_query",
    route_query,
    {
        "greeting": "greeting_response",
        "technical": "technical_response",
        "billing": "billing_response",
        "general": "general_response",
    },
)

builder.add_edge("greeting_response", END)
builder.add_edge("technical_response", END)
builder.add_edge("billing_response", END)
builder.add_edge("general_response", END)

app = builder.compile()


# STEP 7: Run the chatbot
if __name__ == "__main__":
    print("Customer Support Chatbot")
    print("Type 'exit' to stop.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        initial_state = {
            "user_query": user_input,
            "category": "",
            "response": "",
        }

        result = app.invoke(initial_state)

        print("Category:", result["category"])
        print("Response:", result["response"])
        print("-" * 50)
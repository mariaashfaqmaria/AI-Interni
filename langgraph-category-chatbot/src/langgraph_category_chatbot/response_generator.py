from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
)

from .config import llm


CATEGORY_INSTRUCTIONS = {
    "Greeting": (
        "Handle greetings, thanks, and farewells naturally. "
        "Be warm and conversational. Do not force a greeting "
        "if the user has already moved to another topic."
    ),
    "Technical": (
        "Help with programming, software, APIs, errors, "
        "and technical troubleshooting. Explain clearly "
        "and address only the technical aspects."
    ),
    "Billing": (
        "Help with invoices, payments, subscriptions, "
        "charges, and refunds. Never invent account details, "
        "payment records, or a company's refund policy."
    ),
    "General": (
        "Answer general-information questions clearly and "
        "naturally, without taking over specialized topics "
        "assigned to other categories."
    ),
}


CATEGORY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are one part of a helpful, human-like chatbot.

Your current responsibility:
{instruction}

Respond naturally to the relevant part of the user's
latest message.

Rules:
- Never print category names or category labels.
- Do not use a fixed greeting or a fixed response template.
- Avoid repeating information already provided in the
  conversation unless it is necessary.
- Use the conversation context to understand follow-ups.
- Do not answer topics outside your assigned responsibility.
- Never invent facts, account details, or policies.
- Return only the response text, not your reasoning.
        """,
    ),
    (
        "human",
        """
Conversation history:
{history}

Latest user message:
{question}
        """,
    ),
])


def create_category_chain(category: str):
    """Create a separate LLM chain for a category."""

    prompt = CATEGORY_PROMPT.partial(
        instruction=CATEGORY_INSTRUCTIONS[category]
    )

    return (
        RunnableLambda(
            lambda inputs: {
                **inputs,
                "history": str(inputs["history"]),
            }
        )
        | prompt
        | llm
        | RunnableLambda(
            lambda response: response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
    )


def generate_answer(
    question: str,
    history: list[dict[str, str]],
    categories: list[str],
) -> str:
    """Generate and combine natural responses."""

    if not categories:
        categories = ["General"]

    # Create chains only for detected categories.
    chains = {
        f"part_{index}": create_category_chain(category)
        for index, category in enumerate(categories)
    }

    inputs = {
        "question": question,
        "history": history[-10:],
    }

    if len(chains) == 1:
        return next(iter(chains.values())).invoke(inputs).strip()

    # Execute the matched category chains concurrently.
    parallel_chain = RunnableParallel(**chains)
    results = parallel_chain.invoke(inputs)

    # Ask the LLM to merge the results into one natural reply.
    merge_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are the final conversational assistant.

Combine the provided response fragments into one coherent,
human-like answer to the user's latest message.

Requirements:
- Write as one assistant speaking naturally.
- Never mention categories, chains, fragments, or routing.
- Do not add headings merely to identify categories.
- Remove repeated greetings, repeated explanations,
  and redundant information.
- Preserve all useful information from the fragments.
- Do not invent additional facts.
- Respond directly to the user's message.
            """,
        ),
        (
            "human",
            """
Latest user message:
{question}

Response fragments:
{fragments}

Write the final answer.
            """,
        ),
    ])

    merge_chain = merge_prompt | llm

    fragments = "\n\n".join(
        answer.strip()
        for answer in results.values()
        if answer.strip()
    )

    final_response = merge_chain.invoke({
        "question": question,
        "fragments": fragments,
    })

    content = final_response.content

    return content.strip() if isinstance(content, str) else str(content)
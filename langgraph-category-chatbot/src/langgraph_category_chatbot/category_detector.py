import json
import re

from .config import llm

CATEGORIES = [
    "Greeting",
    "Technical",
    "Billing",
    "General",
]


def detect_categories(
    question: str,
    history: list[dict[str, str]],
) -> list[str]:

    recent_history = history[-10:]

    prompt = f"""
You are a category classifier for a chatbot.

Available categories:
1. Greeting: greetings, thanks, farewells.
2. Technical: programming, software, errors,
   installations, APIs, and technical troubleshooting.
3. Billing: invoices, payments, subscriptions,
   charges, refunds, and billing disputes.
4. General: ordinary questions that do not fit
   the other categories.

Rules:
- Return every category genuinely needed to answer
  the latest user message.
- A question may belong to multiple categories.
- Use conversation history to understand follow-ups.
- If the user changes topic, classify the new topic.
- Do not keep an old category just because it appeared
  in an earlier message.
- Use General when no other category fits.
- Return only valid JSON in this format:
  {{"categories": ["Technical"]}}

Recent conversation:
{json.dumps(recent_history, ensure_ascii=False)}

Latest user message:
{question}

"""

    response = llm.invoke(prompt)
    content = response.content

    if not isinstance(content, str):
        content = str(content)

    # Extract JSON, including responses inside code fences.
    match = re.search(r"\{.*\}", content, re.DOTALL)

    if match:
        try:
            result = json.loads(match.group())
            detected = result.get("categories", [])

            if not isinstance(detected, list):
                return ["General"]

            valid = [
                category
                for category in CATEGORIES
                if category in detected
            ]

            if valid:
                return valid

        except (json.JSONDecodeError, AttributeError):
            pass

    # Safe fallback if the model returns invalid output.
    return ["General"]
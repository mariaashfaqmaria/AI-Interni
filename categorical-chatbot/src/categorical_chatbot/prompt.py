
# src/categorical_chatbot/services/prompt.py

CATEGORIES = ["Greeting", "Technical", "Billing", "General"]


def get_category_prompt(message: str) -> str:
    """Build the prompt used to classify a customer message."""

    return f"""
You are a category classifier for a customer-support chatbot.

Choose one or more categories from this exact list:
- Greeting
- Technical
- Billing
- General

Rules:
1. Return ONLY a valid JSON object.
2. Use this exact format:
   {{"categories": ["Technical"]}}
3. Include every relevant category for messages involving multiple topics.
4. Greeting: greetings and casual introductions.
5. Technical: programming, bugs, errors, and technical support.
6. Billing: payments, invoices, charges, and refunds.
7. General: other questions.
8. A greeting combined with another issue should include Greeting
   and the category for that issue when both are relevant.
9. Do not return explanations or additional text.

User message:
{message}
"""


def get_response_prompt(
    message: str,
    categories: list[str],
    history: list[dict[str, str]],
) -> str:
    """Build the prompt used to generate a customer-support response."""

    conversation = "\n".join(
        f"{item.get('role', 'user')}: "
        f"{item.get('content', '')}"
        for item in history[-10:]
    )

    return f"""
You are a helpful customer-support chatbot.

Relevant categories:
{", ".join(categories)}

Previous conversation:
{conversation or "No previous conversation."}

Current customer message:
{message}

Instructions:
1. Answer every issue in the current message.
2. Combine all relevant issues into one coherent answer.
3. Address technical and billing issues together when both apply.
4. Use history only when it helps interpret the current message.
5. If the user changes topic, answer the new topic.
6. Never invent account details or payment records.
7. Use clear, polite, simple English.
8. Do not mention internal category labels unless useful.
9. If a greeting accompanies a question, respond to both naturally.

Write one complete response.
"""

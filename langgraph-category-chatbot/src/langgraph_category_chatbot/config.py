import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)

if not API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is missing. "
        "Add it to your .env file."
    )

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)
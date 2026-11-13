# backend/main.py
"""Entry point. Run with:  uv run python main.py   (or: uv run uvicorn main:app --reload)"""
import uvicorn

from src.api import app  # noqa: F401  (exposed so `uvicorn main:app` works)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)

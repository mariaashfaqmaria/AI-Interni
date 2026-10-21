# main.py
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

from settings import settings
from database import (
    init_db,
    close_db,
)
from categorical_chatbot.router import router
from categorical_chatbot.utils.logging_config import configure_logging


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    logging.getLogger(__name__).info(
        "PostgreSQL initialized successfully"
    )

    try:
        yield
    finally:
        await close_db()


# app = FastAPI(
#     title=settings.APP_NAME,
#     lifespan=lifespan,
# )
app.include_router(router)


@app.get("/")
async def home():
    return {
        "message": "Categorical Chatbot API is running.",
        "database": "PostgreSQL",
        "docs": "/docs",
    }
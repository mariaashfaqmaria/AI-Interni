# backend/src/config.py
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # App / Authentication
    secret_key: str = "development-only-change-this-secret-key"
    database_url: str = "sqlite:///./project_scheduling_chatbot.db"
    cors_origins: str = "http://localhost:5173"
    access_token_expire_minutes: int = 30

    # LLM
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index: str = "project-scheduling-chatbot"
    pinecone_namespace: str = "project-scheduling-data"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # LangSmith
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "Project-Scheduling-Chatbot"

    # Documents / Memory
    document_path: str = "data/AI_Project_Data.pdf"
    auto_ingest: bool = True
    checkpoint_path: str = "data/checkpoints"

    @property
    def cors_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_tracing() -> bool:
    """Configure LangSmith tracing using values loaded from .env."""

    settings = get_settings()

    if settings.langsmith_tracing and settings.langsmith_api_key:

        tracing_settings = {
            "LANGSMITH_TRACING": "true",
            "LANGCHAIN_TRACING_V2": "true",
            "LANGSMITH_API_KEY": settings.langsmith_api_key,
            "LANGSMITH_PROJECT": settings.langsmith_project,
            "LANGCHAIN_PROJECT": settings.langsmith_project,
        }

        os.environ.update(tracing_settings)

        return True

    return False

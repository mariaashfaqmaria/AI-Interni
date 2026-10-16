from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FASTAPI CRUD with PostgreSQL"
    debug: bool = False

    database_url: str

    max_upload_size: int = 10 * 1024 * 1024
    welcome_message: str = "Welcome to my FastAPI application"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
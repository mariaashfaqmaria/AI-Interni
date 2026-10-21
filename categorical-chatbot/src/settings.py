# src/categorical_chatbot/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "openrouter/free"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "categorical_chatbot_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str

    APP_NAME: str = "Categorical Chatbot"

    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
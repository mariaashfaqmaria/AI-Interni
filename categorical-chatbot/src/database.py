# src/categorical_chatbot/database/database.py
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


from settings import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(
settings.DATABASE_URL,
echo=False,
pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
bind=engine,
expire_on_commit=False,
)

async def init_db() -> None:
# Import the model once so SQLAlchemy registers its table.
    from database import model  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

async def close_db() -> None:
    await engine.dispose()
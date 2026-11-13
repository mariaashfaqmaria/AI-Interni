# backend/src/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

# Force the synchronous psycopg driver, whatever the .env says.
_url = settings.database_url.strip()
for old in ("postgresql+asyncpg://", "postgres://", "postgresql://"):
    if _url.startswith(old):
        _url = "postgresql+psycopg://" + _url[len(old):]
        break

_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}
engine = create_engine(_url, connect_args=_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

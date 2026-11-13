# backend/src/models.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    selected_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    days: Mapped[int] = mapped_column(Integer, default=14)
    pages: Mapped[str] = mapped_column(String(20), default="")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    thread_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(10), default="chat")  # chat | plan
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user | bot
    text: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{page, match}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project: Mapped[str] = mapped_column(String(200))
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ScheduleItem(Base):
    __tablename__ = "schedule_items"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(20), default="9:00 AM")
    duration: Mapped[str] = mapped_column(String(20), default="1 hr")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10), default="todo")  # todo | progress | done
    priority: Mapped[str] = mapped_column(String(10), default="Medium")
    due: Mapped[str] = mapped_column(String(30), default="")
    done_flag: Mapped[bool] = mapped_column(Boolean, default=False)

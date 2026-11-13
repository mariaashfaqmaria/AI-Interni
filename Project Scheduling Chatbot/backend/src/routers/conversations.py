# backend/src/routers/conversations.py
"""History page: list / view / export / delete conversations (chats and plans)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Conversation, User

router = APIRouter(prefix="/conversations", tags=["history"])


def when(dt: datetime) -> str:
    dt = dt.replace(tzinfo=dt.tzinfo or timezone.utc)
    days = (datetime.now(timezone.utc).date() - dt.date()).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    return f"{dt.day} {dt.strftime('%b')}"


def serialize(c: Conversation, with_messages: bool = True) -> dict:
    out = {
        "id": c.id,
        "thread_id": c.thread_id,
        "type": c.type,
        "title": c.title,
        "when": when(c.updated_at),
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "count": len(c.messages),
        "messages": [],
    }
    if with_messages:
        for m in c.messages:
            item = {"role": m.role, "text": m.text}
            if m.sources:
                # Preserve structured source data; legacy strings are also valid.
                item["sources"] = m.sources
            out["messages"].append(item)
    return out


def _owned(db: Session, user: User, cid: int) -> Conversation:
    c = db.get(Conversation, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return c


@router.get("")
def list_conversations(
    q: str = "",
    type: str = Query("all", pattern="^(all|chat|plan)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
    if type != "all":
        stmt = stmt.where(Conversation.type == type)
    rows = [c for c in db.scalars(stmt) if q.lower() in c.title.lower()]
    return [serialize(c, with_messages=False) for c in rows]


@router.get("/export")
def export_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.id))
    return [serialize(c) for c in rows]


@router.get("/by-thread/{thread_id}")
def by_thread(thread_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.scalar(select(Conversation).where(Conversation.user_id == user.id, Conversation.thread_id == thread_id))
    if not c:
        raise HTTPException(404, "Conversation not found")
    return serialize(c)


@router.get("/{cid}")
def get_conversation(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize(_owned(db, user, cid))


@router.delete("/{cid}", status_code=204)
def delete_conversation(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, cid))
    db.commit()

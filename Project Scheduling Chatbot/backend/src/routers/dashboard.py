# backend/src/routers/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Plan, Project, ScheduleItem, Task, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_tasks = db.scalar(select(func.count()).select_from(Task).where(Task.user_id == user.id)) or 0
    done = db.scalar(select(func.count()).select_from(Task).where(Task.user_id == user.id, Task.status == "done")) or 0
    return {
        "total_projects": db.scalar(select(func.count()).select_from(Project)) or 0,
        "active_projects": db.scalar(select(func.count()).select_from(Plan).where(Plan.user_id == user.id)) or 0,
        "scheduled_tasks": db.scalar(select(func.count()).select_from(ScheduleItem).where(ScheduleItem.user_id == user.id)) or 0,
        "overall_progress": f"{round(done / total_tasks * 100) if total_tasks else 0}%",
    }


@router.get("/calendar-dots")
def calendar_dots(month: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """month = YYYY-MM -> {day_of_month: task_count} for the dashboard mini-calendar."""
    rows = db.scalars(select(ScheduleItem).where(ScheduleItem.user_id == user.id, ScheduleItem.date.like(f"{month}-%")))
    out: dict[int, int] = {}
    for r in rows:
        d = int(r.date[-2:])
        out[d] = out.get(d, 0) + 1
    return out

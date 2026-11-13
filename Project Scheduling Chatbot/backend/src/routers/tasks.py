# backend/src/routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Task, User
from ..schemas import TaskIn, TaskOut, TaskPatch

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _owned(db: Session, user: User, tid: int) -> Task:
    t = db.get(Task, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Task not found")
    return t


def apply_status_priority(task: Task, new_status: str) -> None:
    """Mirror the board UI: done tasks show priority 'Done'; reopening restores 'Medium'."""
    if new_status == "done":
        task.priority = "Done"
    elif task.priority == "Done":
        task.priority = "Medium"
    task.status = new_status


@router.get("", response_model=list[TaskOut])
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Task).where(Task.user_id == user.id).order_by(Task.id)))


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = Task(user_id=user.id, title=body.title, priority=body.priority, due=body.due)
    apply_status_priority(t, body.status)
    db.add(t)
    db.commit()
    return t


@router.patch("/{tid}", response_model=TaskOut)
def update_task(tid: int, body: TaskPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _owned(db, user, tid)
    data = body.model_dump(exclude_unset=True)
    for k in ("title", "priority", "due"):
        if k in data and data[k] is not None:
            setattr(t, k, data[k])
    if data.get("status"):
        apply_status_priority(t, data["status"])
    db.commit()
    return t


@router.delete("/{tid}", status_code=204)
def delete_task(tid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, tid))
    db.commit()
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Task, User
from ..schemas import TaskIn, TaskOut, TaskPatch

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _owned(db: Session, user: User, tid: int) -> Task:
    t = db.get(Task, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Task not found")
    return t


def apply_status_priority(task: Task, new_status: str) -> None:
    """Mirror the board UI: done tasks show priority 'Done'; reopening restores 'Medium'."""
    if new_status == "done":
        task.priority = "Done"
    elif task.priority == "Done":
        task.priority = "Medium"
    task.status = new_status


@router.get("", response_model=list[TaskOut])
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Task).where(Task.user_id == user.id).order_by(Task.id)))


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = Task(user_id=user.id, title=body.title, priority=body.priority, due=body.due)
    apply_status_priority(t, body.status)
    db.add(t)
    db.commit()
    return t


@router.patch("/{tid}", response_model=TaskOut)
def update_task(tid: int, body: TaskPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _owned(db, user, tid)
    data = body.model_dump(exclude_unset=True)
    for k in ("title", "priority", "due"):
        if k in data and data[k] is not None:
            setattr(t, k, data[k])
    if data.get("status"):
        apply_status_priority(t, data["status"])
    db.commit()
    return t


@router.delete("/{tid}", status_code=204)
def delete_task(tid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, tid))
    db.commit()
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Task, User
from ..schemas import TaskIn, TaskOut, TaskPatch

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _owned(db: Session, user: User, tid: int) -> Task:
    t = db.get(Task, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Task not found")
    return t


def apply_status_priority(task: Task, new_status: str) -> None:
    """Mirror the board UI: done tasks show priority 'Done'; reopening restores 'Medium'."""
    if new_status == "done":
        task.priority = "Done"
    elif task.priority == "Done":
        task.priority = "Medium"
    task.status = new_status


@router.get("", response_model=list[TaskOut])
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Task).where(Task.user_id == user.id).order_by(Task.id)))


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = Task(user_id=user.id, title=body.title, priority=body.priority, due=body.due)
    apply_status_priority(t, body.status)
    db.add(t)
    db.commit()
    return t


@router.patch("/{tid}", response_model=TaskOut)
def update_task(tid: int, body: TaskPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _owned(db, user, tid)
    data = body.model_dump(exclude_unset=True)
    for k in ("title", "priority", "due"):
        if k in data and data[k] is not None:
            setattr(t, k, data[k])
    if data.get("status"):
        apply_status_priority(t, data["status"])
    db.commit()
    return t


@router.delete("/{tid}", status_code=204)
def delete_task(tid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, tid))
    db.commit()

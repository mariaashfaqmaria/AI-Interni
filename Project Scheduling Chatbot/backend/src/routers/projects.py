# backend/src/routers/projects.py
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Project, User
from ..schemas import ProjectOut, ProjectPage
from ..services.documents import store as local_store
from ..services.seed import PROJECTS

router = APIRouter(prefix="/projects", tags=["projects"])


def _approved_names() -> list[str]:
    names = [item[0] for item in PROJECTS]
    names.extend(item["project_title"] for item in local_store.projects)
    return names


def _approved_project(db: Session, pid: int) -> Project:
    project = db.get(Project, pid)
    if not project or project.name not in _approved_names():
        raise HTTPException(404, "Approved project not found")
    return project


@router.get("", response_model=ProjectPage)
def list_projects(
    q: str = "",
    tag: str = "All",
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = _approved_names()
    rows = [
        project for project in db.scalars(
            select(Project).where(Project.name.in_(allowed)).order_by(Project.id)
        ).all()
        if (not tag or tag == "All" or tag in (project.tags or []))
        and q.casefold() in project.name.casefold()
    ]
    start = (page - 1) * page_size
    return ProjectPage(
        items=rows[start:start + page_size],
        total=len(rows),
        page=page,
        pages=max(1, math.ceil(len(rows) / page_size)),
    )


@router.get("/compare", response_model=list[ProjectOut])
def compare(
    ids: str = Query(..., description="comma-separated project IDs, e.g. 1,2"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        wanted = [int(value) for value in ids.split(",") if value.strip()]
    except ValueError as exc:
        raise HTTPException(422, "ids must be integers") from exc
    if len(wanted) < 2:
        raise HTTPException(422, "Pick at least 2 projects to compare")
    allowed = _approved_names()
    rows = list(db.scalars(
        select(Project).where(Project.id.in_(wanted), Project.name.in_(allowed)).order_by(Project.id)
    ))
    if len(rows) != len(set(wanted)):
        raise HTTPException(404, "One or more approved projects were not found")
    return rows


@router.get("/suggestions", response_model=list[ProjectOut])
def suggestions(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    allowed = _approved_names()
    return list(db.scalars(
        select(Project).where(Project.name.in_(allowed)).order_by(Project.id).limit(3)
    ))


@router.get("/{pid}", response_model=ProjectOut)
def get_project(pid: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _approved_project(db, pid)


@router.post("/{pid}/select", response_model=ProjectOut)
def select_project(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _approved_project(db, pid)
    user.selected_project_id = pid
    db.add(user)
    db.commit()
    return project

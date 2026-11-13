# backend/src/schemas.py
from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    selected_project_id: int | None = None


# ---------- chat ----------
AnswerMode = Literal["From document", "General advice"]


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None
    mode: AnswerMode = "From document"


class SourceOut(BaseModel):
    project_id: str | None = None
    project_title: str | None = None
    source_type: str = "document file"
    match: float = 0.0


class ChatOut(BaseModel):
    reply: str
    sources: list[SourceOut] = []
    conversation_id: int
    thread_id: str
    file: str | None = None
    plan_id: int | None = None


# ---------- projects ----------
class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    tags: list[str]
    days: int
    pages: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    tags: list[str] = []
    days: int = Field(14, ge=1, le=120)
    pages: str = ""


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    total: int
    page: int
    pages: int


# ---------- planner ----------
class PlanIn(BaseModel):
    project: str
    start: Date
    days: int = Field(14, ge=1, le=60)
    hours: int = Field(2, ge=1, le=12)
    beginner: bool = True
    weekends_off: bool = True


class PlanTask(BaseModel):
    title: str
    description: str = ""
    phase: str
    date: str
    time: str
    duration: str


class PlanOut(BaseModel):
    id: int
    project: str
    start: str
    days: int
    hours: int
    total_hours: int
    weeks: list[dict]
    objective: str
    architecture: list[str]
    research: list[dict]
    tasks: list[PlanTask]
    checklist: dict[str, list[str]]


# ---------- schedule ----------
class ScheduleIn(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = "9:00 AM"
    duration: str = "1 hr"


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    date: str
    time: str
    duration: str


# ---------- tasks ----------
class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: Literal["todo", "progress", "done"] = "todo"
    priority: str = "Medium"
    due: str = ""


class TaskPatch(BaseModel):
    title: str | None = None
    status: Literal["todo", "progress", "done"] | None = None
    priority: str | None = None
    due: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    status: str
    priority: str
    due: str

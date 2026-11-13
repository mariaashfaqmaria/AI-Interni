# backend/src/routers/plans.py
import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..graphs.graph import get_planner_graph
from ..models import Conversation, Message, Plan, Project, ScheduleItem, Task, User, new_id
from ..schemas import PlanIn, PlanOut
from ..services import planner
from ..services.seed import fmt_short

log = logging.getLogger(__name__)
router = APIRouter(prefix="/plans", tags=["planner"])


def to_out(p: Plan) -> PlanOut:
    return PlanOut(id=p.id, **p.content)


def _owned(db: Session, user: User, pid: int) -> Plan:
    p = db.get(Plan, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Plan not found")
    return p


def _init(body: PlanIn) -> dict:
    return body.model_dump()


def _validate_approved_project(db: Session, project_name: str) -> None:
    approved = db.scalar(select(Project).where(Project.name == project_name))
    if approved is None:
        raise HTTPException(
            status_code=422,
            detail="Select one of the 16 approved projects from Project Explorer.",
        )


def _config(user_id: int) -> dict:
    return {"run_name": "project_planner", "tags": ["planner"], "metadata": {"user_id": user_id}}


def persist(db: Session, user_id: int, content: dict) -> Plan:
    plan = Plan(user_id=user_id, project=content["project"], content=content)
    db.add(plan)
    db.flush()
    convo = Conversation(user_id=user_id, type="plan", title=f"Plan: {content['project']}")  # shows in History
    convo.messages = [
        Message(role="user", text=f"Plan {content['project']} in {content['days']} days, {content['hours']} hrs/day."),
        Message(role="bot", text=f"{content['objective']} Total effort: {content['total_hours']} hours."),
    ]
    db.add(convo)
    db.commit()
    return plan


@router.post("/generate", response_model=PlanOut, status_code=201)
def generate(body: PlanIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_approved_project(db, body.project)
    state = get_planner_graph().invoke(_init(body), config=_config(user.id))
    return to_out(persist(db, user.id, planner.assemble(state)))


@router.post("/generate/stream")
def generate_stream(
    body: PlanIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Server-sent events: one event per finished graph step, then the saved plan."""
    _validate_approved_project(db, body.project)
    user_id = user.id

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def events():
        state = _init(body)
        try:
            for chunk in get_planner_graph().stream(state, config=_config(user_id), stream_mode="updates"):
                for node, update in chunk.items():
                    state.update(update or {})
                    yield sse({"step": node, "status": "done"})
            with SessionLocal() as db:  # own session: the request-scoped one may be closed by now
                plan = persist(db, user_id, planner.assemble(state))
                yield sse({"step": "complete", "plan": to_out(plan).model_dump()})
        except Exception:
            log.exception("Plan generation failed")
            yield sse({"step": "error", "detail": "Plan generation failed"})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("", response_model=list[PlanOut])
def list_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_out(p) for p in db.scalars(select(Plan).where(Plan.user_id == user.id).order_by(Plan.id.desc()))]


@router.get("/{pid}", response_model=PlanOut)
def get_plan(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(_owned(db, user, pid))


@router.post("/{pid}/save-to-schedule")
def save_to_schedule(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = _owned(db, user, pid)
    db.execute(delete(ScheduleItem).where(ScheduleItem.plan_id == pid))  # idempotent
    db.execute(delete(Task).where(Task.plan_id == pid))
    for t in plan.content["tasks"]:
        db.add(ScheduleItem(id=new_id(), user_id=user.id, plan_id=pid, title=t["title"],
                            date=t["date"], time=t["time"], duration=t["duration"]))
        db.add(Task(user_id=user.id, plan_id=pid, title=t["title"], status="todo", priority="Medium",
                    due=fmt_short(date.fromisoformat(t["date"]))))
    db.commit()
    return {"saved": len(plan.content["tasks"])}

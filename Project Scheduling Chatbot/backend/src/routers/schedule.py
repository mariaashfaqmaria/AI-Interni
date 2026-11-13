# backend/src/routers/schedule.py
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ScheduleItem, User, new_id
from ..schemas import ScheduleIn, ScheduleOut

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _mine(db: Session, user: User):
    return select(ScheduleItem).where(ScheduleItem.user_id == user.id)


@router.get("", response_model=list[ScheduleOut])
def list_items(
    start: str | None = None, end: str | None = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    stmt = _mine(db, user).order_by(ScheduleItem.date, ScheduleItem.id)
    if start:
        stmt = stmt.where(ScheduleItem.date >= start)
    if end:
        stmt = stmt.where(ScheduleItem.date <= end)
    return list(db.scalars(stmt))


@router.post("", response_model=ScheduleOut, status_code=201)
def add_item(body: ScheduleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = ScheduleItem(id=body.id or new_id(), user_id=user.id, **body.model_dump(exclude={"id"}))
    db.add(item)
    db.commit()
    return item


@router.post("/bulk", response_model=list[ScheduleOut], status_code=201)
def add_many(body: list[ScheduleIn], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = [ScheduleItem(id=b.id or new_id(), user_id=user.id, **b.model_dump(exclude={"id"})) for b in body]
    db.add_all(items)
    db.commit()
    return items


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(ScheduleItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()


@router.get("/export.ics")
def export_ics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AI Project Architect//EN"]
    p = lambda n: f"{n:02d}"  # noqa: E731
    for t in db.scalars(_mine(db, user)):
        hm, _, ap = t.time.partition(" ")
        h, mi = (int(x) for x in hm.split(":"))
        if ap.upper() == "PM" and h < 12:
            h += 12
        if ap.upper() == "AM" and h == 12:
            h = 0
        try:
            num = float(t.duration.split()[0])
        except ValueError:
            num = 1.0
        hrs = num / 60 if "min" in t.duration else num
        end = min(h + int(hrs), 23)
        d = t.date.replace("-", "")
        lines += [
            "BEGIN:VEVENT", f"UID:{t.id}@ai-project-architect", f"SUMMARY:{t.title}",
            f"DTSTART:{d}T{p(h)}{p(mi)}00", f"DTEND:{d}T{p(end)}{p(mi)}00", "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="project-schedule.ics"'})

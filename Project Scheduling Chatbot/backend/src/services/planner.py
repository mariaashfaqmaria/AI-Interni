# backend/src/services/planner.py
"""Deterministic helpers for the planner graph: fallbacks (no LLM) and date assignment."""
from datetime import date, timedelta

TASK_TITLES = [
    "Set up environment", "Research dataset", "Design data schema", "Build data pipeline",
    "Train baseline model", "Evaluate model", "Wrap model in an API", "Write API endpoints",
    "Create dashboard layout", "Connect dashboard to API", "Add alerts", "Write tests",
    "Fix bugs", "Review checklist",
]
WEEK_TITLES = ["Data and setup", "Model and API", "Dashboard, testing"]
PHASES = ["Setup and research", "Build", "Test and deliver"]
CHECKLIST = {
    "Setup and research": ["Environment ready", "Dataset identified", "Requirements written"],
    "Build": ["Data pipeline working", "Baseline model trained", "API endpoints implemented"],
    "Test and deliver": ["Tests passing", "Dashboard connected", "Demo and write-up complete"],
}
ARCHITECTURE = ["Data layer", "Model layer", "API layer (FastAPI)", "Dashboard (React)"]


def weeks_needed(days: int) -> int:
    return max(1, -(-days // 7))


def fallback_outline(project: str, days: int, hours: int, weekends_off: bool = True) -> dict:
    duration_label = "working days" if weekends_off else "calendar days"
    return {
        "objective": f"Deliver a working {project} in {days} {duration_label} at {hours} hr/day.",
        "architecture": ARCHITECTURE,
        "week_titles": [WEEK_TITLES[i % len(WEEK_TITLES)] for i in range(weeks_needed(days))],
    }


def fallback_items(project: str, days: int, beginner: bool, start_index: int = 0) -> list[dict]:
    items = []
    for n in range(start_index, days):
        title = TASK_TITLES[n % len(TASK_TITLES)]
        items.append({
            "title": title,
            "description": f"{title} for {project}." + (" Beginner-friendly: follow a tutorial first." if beginner else ""),
            "phase": PHASES[min(len(PHASES) - 1, n * len(PHASES) // days)],
        })
    return items


def working_days(start: date, count: int, weekends_off: bool) -> list[date]:
    out, d = [], start
    while len(out) < count:
        if not (weekends_off and d.weekday() >= 5):
            out.append(d)
        d += timedelta(days=1)
    return out


def build_tasks(items: list[dict], start: date, hours: int, weekends_off: bool) -> list[dict]:
    dates = working_days(start, len(items), weekends_off)
    duration = f"{hours} hr" if hours == 1 else f"{hours} hrs"
    return [{**it, "date": d.isoformat(), "time": "9:00 AM", "duration": duration} for it, d in zip(items, dates)]


def assemble(s: dict) -> dict:
    """Turn final graph state into the stored/returned plan content."""
    outline = s["outline"]
    n = weeks_needed(s["days"])
    titles = (outline["week_titles"] + WEEK_TITLES * n)[:n]
    return {
        "project": s["project"],
        "start": s["start"].isoformat(),
        "days": s["days"],
        "hours": s["hours"],
        "total_hours": s["days"] * s["hours"],
        "weeks": [{"week": i + 1, "title": t} for i, t in enumerate(titles)],
        "objective": outline["objective"],
        "architecture": outline["architecture"],
        "research": [
            {
                "project_id": r.get("project_id"),
                "project_title": r.get("project_title"),
                "domain": r.get("domain"),
                "source_type": r.get("source_type", "document file"),
                "match": r.get("match", 0.0),
                "text": r.get("text", "")[:500],
            }
            for r in s.get("research", [])
        ],
        "tasks": s["tasks"],
        "checklist": s["checklist"],
    }

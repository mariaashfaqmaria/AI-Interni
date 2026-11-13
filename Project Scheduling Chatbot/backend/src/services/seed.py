# backend/src/services/seed.py
"""Approved starter catalogue and SQL catalogue synchronization."""
from datetime import date
import math

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..models import Project, Task, User
from .documents import tokenize

# These six projects are deliberately in domains not used by the ten PDF projects.
PROJECTS = [
    (
        "Smart Factory Quality Control",
        "Build a system that monitors manufacturing data, identifies product defects, and helps factory teams improve production quality.",
        ["Manufacturing", "Intermediate"],
        21,
    ),
    (
        "Personalized Travel Discovery Platform",
        "Create a platform that recommends travel destinations, attractions, and itineraries based on users' interests, budgets, and available time.",
        ["Tourism", "Intermediate"],
        18,
    ),
    (
        "Athlete Performance Analysis System",
        "Develop an application that analyzes sports performance records and presents useful insights about player progress, training, and match statistics.",
        ["Sports", "Intermediate"],
        21,
    ),
    (
        "Restaurant Operations Management System",
        "Build a system for managing restaurant menus, table reservations, orders, inventory, and daily sales reports.",
        ["Food Service", "Beginner"],
        14,
    ),
    (
        "Digital Public Service Portal",
        "Create a web portal where citizens can submit service requests, track application progress, and receive updates from public departments.",
        ["Government", "Intermediate"],
        21,
    ),
    (
        "Renewable Energy Monitoring Dashboard",
        "Develop a dashboard that tracks solar or wind energy production, displays consumption trends, and helps operators monitor system performance.",
        ["Energy", "Intermediate"],
        18,
    ),
]

PDF_PROJECT_DOMAINS = {
    "PulsePath": "Healthcare",
    "SkillSpring": "Education",
    "LedgerLoop": "Finance",
    "FieldNest": "Agriculture",
    "CartCanvas": "E-commerce",
    "RouteRipple": "Transportation",
    "HavenKey": "Real Estate",
    "SceneSync": "Entertainment",
    "AccessHarbor": "Cybersecurity",
    "EcoTrace": "Environment",
}
EXPECTED_TOTAL_PROJECTS = 16


def seed_project_records() -> list[dict]:
    """Return seed projects in the same structure as PDF retrieval results."""
    records = []
    for name, description, tags, days in PROJECTS:
        records.append({
            "project_id": name.lower().replace(" ", "-"),
            "project_title": name,
            "domain": tags[0],
            "application_type": "Web application",
            "source": "seed catalog",
            "source_type": "seeds file",
            "match": 1.0,
            "text": (
                f"Project: {name}\nDescription: {description}\n"
                f"Domain: {tags[0]}\nLevel: {tags[1]}\n"
                f"Suggested duration: {days} days"
            ),
            "days": days,
            "tags": tags,
        })
    return records


def search_seed_projects(query: str, k: int = 3) -> list[dict]:
    query_tokens = set(tokenize(query))
    if not query_tokens or k <= 0:
        return []
    records = seed_project_records()
    project_tokens = [tokenize(f"{p['project_title']} {p['text']}") for p in records]
    df = {token: sum(token in tokens for tokens in project_tokens) for token in query_tokens}
    idf = {token: math.log(1 + len(records) / (1 + df[token])) for token in query_tokens}
    total = sum(idf.values()) or 1.0
    results = []
    for index, tokens in enumerate(project_tokens):
        present = [token for token in query_tokens if token in tokens]
        if not present:
            continue
        coverage = sum(idf[token] for token in present) / total
        if coverage < 0.12:
            continue
        tf = sum(1 + math.log(tokens.count(token)) for token in present)
        item = dict(records[index])
        item["match"] = round(coverage, 4)
        item["_rank"] = (coverage, tf)
        results.append(item)
    results.sort(key=lambda item: item["_rank"], reverse=True)
    for item in results:
        item.pop("_rank", None)
    return results[:k]


def seed_projects(db: Session) -> None:
    """Insert/update the six approved seed projects; final reconciliation runs after PDF load."""
    existing = {p.name.casefold(): p for p in db.scalars(select(Project)).all()}
    for name, description, tags, days in PROJECTS:
        project = existing.get(name.casefold())
        values = {
            "description": description,
            "tags": [*tags, "source:seeds-file"],
            "days": days,
            "pages": "",
        }
        if project is None:
            db.add(Project(name=name, **values))
        else:
            for key, value in values.items():
                setattr(project, key, value)
    db.commit()


def sync_document_projects(db: Session, document_projects: list[dict]) -> int:
    """
    Reconcile SQL to exactly the ten approved PDF projects plus six seed projects.
    Existing selected-project references to removed custom rows are cleared safely.
    """
    if len(document_projects) != 10:
        raise ValueError(f"Expected exactly 10 PDF projects, received {len(document_projects)}.")

    actual = {str(p.get("project_title", "")).strip(): str(p.get("domain", "")).strip()
              for p in document_projects}
    if actual != PDF_PROJECT_DOMAINS:
        raise ValueError("The PDF project titles/domains do not match the approved catalogue.")

    records = []
    for item in document_projects:
        records.append({
            "name": item["project_title"],
            "description": item.get("text", ""),
            "tags": [item.get("domain", "Not specified"),
                     item.get("application_type", "Not specified"),
                     "source:document-file"],
            "days": 14,
            "pages": "",
        })
    for name, description, tags, days in PROJECTS:
        records.append({
            "name": name,
            "description": description,
            "tags": [*tags, "source:seeds-file"],
            "days": days,
            "pages": "",
        })

    names = [item["name"].casefold() for item in records]
    domains = [item["tags"][0].casefold() for item in records]
    if len(records) != EXPECTED_TOTAL_PROJECTS or len(set(names)) != EXPECTED_TOTAL_PROJECTS:
        raise ValueError("Approved catalogue must contain exactly 16 unique project titles.")
    if len(set(domains)) != EXPECTED_TOTAL_PROJECTS:
        raise ValueError("Approved catalogue must contain exactly 16 unique domains.")

    existing = {p.name.casefold(): p for p in db.scalars(select(Project)).all()}
    approved = set(names)
    stale = [p for key, p in existing.items() if key not in approved]
    stale_ids = [p.id for p in stale]
    if stale_ids:
        db.execute(
            update(User).where(User.selected_project_id.in_(stale_ids))
            .values(selected_project_id=None)
        )
        db.execute(delete(Project).where(Project.id.in_(stale_ids)))

    added = 0
    for item in records:
        project = existing.get(item["name"].casefold())
        if project is None:
            db.add(Project(name=item["name"], description=item["description"],
                           tags=item["tags"], days=item["days"], pages=item["pages"]))
            added += 1
        else:
            project.description = item["description"]
            project.tags = item["tags"]
            project.days = item["days"]
            project.pages = item["pages"]

    db.commit()
    final_rows = db.scalars(select(Project)).all()
    final_names = {p.name.casefold() for p in final_rows}
    if len(final_rows) != EXPECTED_TOTAL_PROJECTS or final_names != approved:
        raise RuntimeError(
            f"SQL catalogue verification failed: expected 16 approved projects, found {len(final_rows)}."
        )
    return added


def fmt_short(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def seed_user_tasks(db: Session, user_id: int) -> None:
    rows = [
        ("Complete project research", "todo", "High", "Today"),
        ("Design database schema", "todo", "Medium", ""),
        ("Write API endpoints", "todo", "Medium", ""),
        ("Build data pipeline", "progress", "High", ""),
        ("Create dashboard layout", "progress", "Low", ""),
        ("Set up development environment", "done", "Done", ""),
        ("Implement core features", "done", "Done", ""),
    ]
    db.add_all(Task(user_id=user_id, title=title, status=status, priority=priority, due=due)
               for title, status, priority, due in rows)
    db.commit()

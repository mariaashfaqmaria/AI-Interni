# backend/src/api.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401 - register SQLAlchemy models
from .config import configure_tracing, get_settings
from .database import Base, SessionLocal, engine
from .routers import auth, chat, conversations, dashboard, plans, projects, schedule, tasks
from .routes import documents
from .services import retriever
from .services.seed import seed_projects, sync_document_projects
from .services.documents import store as local_store

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)

    # Seed projects are always available. When the PDF is present, the
    # synchronizer reconciles the database to exactly 16 approved projects.
    with SessionLocal() as db:
        seed_projects(db)

    log.info("LangSmith tracing: %s", "on" if configure_tracing() else "off")
    try:
        retriever.startup()
        log.info(
            "Retrieval backend: %s | documents ready: %s",
            retriever.backend_name(),
            retriever.has_documents(),
        )
    except Exception:
        # Pinecone can be temporarily unavailable while local PDF retrieval remains usable.
        log.exception("Retrieval startup failed; continuing with available local catalogue.")

    if len(local_store.projects) == 10:
        try:
            with SessionLocal() as db:
                added = sync_document_projects(db, local_store.projects)
                log.info("Approved project catalogue synchronized; added %s projects", added)
        except Exception:
            log.exception("Could not synchronize the approved SQL project catalogue.")
    else:
        log.error(
            "The PDF catalogue is not loaded. Six seed projects are available; "
            "place the approved AI_Project_Data.pdf at DOCUMENT_PATH to enable all 16."
        )

    yield


app = FastAPI(title="Project Scheduling Chatbot API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for route in (auth, chat, conversations, projects, plans, schedule, tasks, dashboard, documents):
    app.include_router(route.router)


@app.get("/health")
def health():
    from .services.seed import PROJECTS
    from .services.documents import store

    try:
        pinecone_vectors = retriever.has_documents_pinecone() if retriever.use_pinecone() else 0
    except Exception:
        log.exception("Could not verify Pinecone index health")
        pinecone_vectors = -1
    return {
        "status": "ok",
        "retrieval": retriever.backend_name(),
        "llm": bool(get_settings().openrouter_api_key),
        "tracing": get_settings().langsmith_tracing,
        "pdf_projects": len(store.projects),
        "seed_projects": len(PROJECTS),
        "catalogue_ready": len(store.projects) == 10,
        "expected_total_projects": 16,
        "pinecone_index": get_settings().pinecone_index,
        "pinecone_vectors": pinecone_vectors,
    }

# backend/src/services/retriever.py
"""Retrieval facade for the approved 16-project catalogue."""
import logging
from pathlib import Path

from ..config import get_settings
from . import vectorstore
from .documents import store as local_store
from .seed import PROJECTS, search_seed_projects

log = logging.getLogger(__name__)
_indexed = False


def use_pinecone() -> bool:
    return bool(get_settings().pinecone_api_key)


def backend_name() -> str:
    return "pinecone" if use_pinecone() else "local"


def has_documents() -> bool:
    global _indexed
    if use_pinecone() and not _indexed:
        try:
            _indexed = vectorstore.vector_count() == 16
        except Exception:
            log.exception("Could not read Pinecone stats")
    # The six approved seed projects remain available even if the PDF is absent.
    return _indexed or bool(local_store.projects) or len(PROJECTS) == 6


def filename() -> str | None:
    return local_store.filename or Path(get_settings().document_path).name


def _merge_local_results(query: str, k: int) -> list[dict]:
    pdf_hits = local_store.search(query, k=k)
    seed_hits = search_seed_projects(query, k=k)
    merged = {}
    for item in [*pdf_hits, *seed_hits]:
        key = item.get("project_id") or item.get("project_title")
        current = merged.get(key)
        if current is None or float(item.get("match", 0)) > float(current.get("match", 0)):
            merged[key] = item
    return sorted(merged.values(), key=lambda item: float(item.get("match", 0)), reverse=True)[:k]


def search(query: str, k: int = 4) -> list[dict]:
    if not query or not query.strip():
        return []
    if use_pinecone():
        try:
            count = vectorstore.vector_count()
            if count == 16:
                global _indexed
                _indexed = True
                return vectorstore.search(query, k=k)
            log.warning("Pinecone catalogue has %s vectors; expected 16. Local retrieval will be used.", count)
        except Exception:
            log.exception("Pinecone search failed; using local project stores")
    return _merge_local_results(query, k)


def ingest(path: Path) -> dict:
    global _indexed
    path = Path(path)
    # Validate/load locally before touching Pinecone.
    local_store.load(path)
    if len(local_store.projects) != 10:
        raise ValueError(f"Expected 10 approved PDF projects, loaded {len(local_store.projects)}.")
    info = {
        "file": path.name,
        "pages": len(local_store.pages),
        "pdf_projects": len(local_store.projects),
        "seed_projects": len(PROJECTS),
        "projects": 16,
        "chunks": 16,
        "backend": backend_name(),
    }
    if use_pinecone():
        info.update(vectorstore.ingest_pdf(path))
        _indexed = True
    return info


def startup() -> None:
    global _indexed
    settings = get_settings()
    path = Path(settings.document_path)
    if path.exists():
        local_store.load(path)
    elif settings.auto_ingest:
        log.warning("Configured project PDF was not found: %s", path)
    if use_pinecone() and settings.auto_ingest and path.exists():
        try:
            current_count = vectorstore.vector_count()
            current_catalogue = vectorstore.catalogue_is_current(path)
        except Exception:
            current_count = 0
            current_catalogue = False
            log.exception("Could not verify existing Pinecone catalogue.")
        if not current_catalogue:
            log.info(
                "Pinecone namespace contains %s vectors or outdated IDs; "
                "ingesting the approved 16-project catalogue.",
                current_count,
            )
            ingest(path)
        else:
            _indexed = True


def has_documents_pinecone() -> bool:
    global _indexed
    _indexed = vectorstore.vector_count() == 16
    return _indexed

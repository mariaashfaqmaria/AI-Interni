# backend/src/services/vectorstore.py
"""Pinecone vector store for the approved 16-project catalogue."""
import logging
import re
import time
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langsmith import traceable
from pinecone import Pinecone, ServerlessSpec
from pypdf import PdfReader

from ..config import get_settings
from .seed import PROJECTS, PDF_PROJECT_DOMAINS

log = logging.getLogger(__name__)
EXPECTED_PDF_PROJECTS = 10
EXPECTED_TOTAL_PROJECTS = 16
_PROJECT_HEADING_RE = re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][A-Za-z0-9]+)\s*$")


def _project_id(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")


def _pc() -> Pinecone:
    return Pinecone(api_key=get_settings().pinecone_api_key)


@lru_cache(maxsize=1)
def _embeddings() -> HuggingFaceEmbeddings:
    settings = get_settings()
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def ensure_index():
    settings = get_settings()
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not configured.")
    pc = _pc()
    index_name = settings.pinecone_index
    existing = pc.list_indexes().names()
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=settings.embedding_dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )
    # A bounded wait prevents an infinite startup hang.
    description = None
    for _ in range(60):
        description = pc.describe_index(index_name)
        if description.status["ready"]:
            break
        time.sleep(2)
    if description is None or not description.status["ready"]:
        raise TimeoutError(f"Pinecone index '{index_name}' did not become ready within 120 seconds.")
    if description.dimension != settings.embedding_dimension:
        raise RuntimeError(
            f"Pinecone dimension mismatch: index={description.dimension}, "
            f"embedding={settings.embedding_dimension}. Use a fresh index with dimension "
            f"{settings.embedding_dimension}."
        )
    return pc.Index(index_name)


@lru_cache(maxsize=1)
def get_store() -> PineconeVectorStore:
    settings = get_settings()
    return PineconeVectorStore(
        index=ensure_index(), embedding=_embeddings(), namespace=settings.pinecone_namespace
    )


def vector_count() -> int:
    settings = get_settings()
    namespaces = ensure_index().describe_index_stats().namespaces or {}
    item = namespaces.get(settings.pinecone_namespace)
    return int(getattr(item, "vector_count", 0) or 0) if item else 0


def load_pdf_documents(path: Path) -> list[Document]:
    reader = PdfReader(str(path))
    return [
        Document(page_content=(page.extract_text() or "").strip(),
                 metadata={"source": path.name, "page": page_no})
        for page_no, page in enumerate(reader.pages, start=1)
        if (page.extract_text() or "").strip()
    ]


def split_into_project_sections(pages: list[Document]) -> list[Document]:
    """Create one complete document for each of the ten numbered PDF projects."""
    if not pages:
        raise ValueError("The PDF contains no extractable text pages.")
    lines = "\n".join(d.page_content for d in pages).splitlines()
    starts = []
    for index, line in enumerate(lines):
        match = _PROJECT_HEADING_RE.match(line.strip())
        if match:
            starts.append((index, int(match.group(1)), match.group(2).strip()))
    if len(starts) != EXPECTED_PDF_PROJECTS:
        raise ValueError(
            f"Expected exactly 10 numbered PDF projects, found {len(starts)}. "
            "No existing Pinecone vectors were deleted."
        )
    numbers = [item[1] for item in starts]
    if numbers != list(range(1, EXPECTED_PDF_PROJECTS + 1)):
        raise ValueError(f"PDF project numbering must be 1 through 10; found {numbers}.")

    output = []
    for pos, (start, number, title) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        body_lines = [
            line for line in lines[start:end]
            if not re.match(r"^\s*10 Software Engineering Project Ideas\s*$", line, re.I)
            and not re.match(r"^\s*Page\s+\d+\s*$", line, re.I)
        ]
        content = "\n".join(body_lines).strip()
        domain_match = re.search(r"(?im)^\s*Domain:\s*(.+?)\s*$", content)
        app_match = re.search(r"(?im)^\s*Application type:\s*(.+?)\s*$", content)
        if not content or not domain_match:
            raise ValueError(f"Project {number} ({title}) is missing content or domain.")
        domain = domain_match.group(1).strip()
        if PDF_PROJECT_DOMAINS.get(title) != domain:
            raise ValueError(f"Unexpected title/domain in PDF: {title} / {domain}.")
        output.append(Document(
            page_content=content,
            metadata={
                "source": pages[0].metadata.get("source", "AI_Project_Data.pdf"),
                "source_type": "document file",
                "project_number": number,
                "project_id": _project_id(title),
                "project_title": title,
                "domain": domain,
                "application_type": app_match.group(1).strip() if app_match else "Not specified",
            },
        ))
    if len({d.metadata["domain"].casefold() for d in output}) != EXPECTED_PDF_PROJECTS:
        raise ValueError("The ten PDF projects must have ten unique domains.")
    return output


def build_seed_documents() -> list[Document]:
    docs = []
    for name, description, tags, days in PROJECTS:
        domain, level = tags[0], tags[1]
        content = (
            f"Project: {name}\nDescription: {description}\nDomain: {domain}\n"
            f"Level: {level}\nSuggested duration: {days} days"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "source": "seed catalog",
                "source_type": "seeds file",
                "project_number": 0,
                "project_id": _project_id(name),
                "project_title": name,
                "domain": domain,
                "application_type": "Web application",
                "suggested_days": days,
            },
        ))
    return docs




def catalogue_is_current(path: Path) -> bool:
    """Check vector IDs, not only count, before skipping automatic re-ingestion."""
    pages = load_pdf_documents(Path(path))
    documents = split_into_project_sections(pages) + build_seed_documents()
    expected = {f"project-{doc.metadata['project_id']}" for doc in documents}
    actual = set()
    for batch in ensure_index().list(namespace=get_settings().pinecone_namespace):
        actual.update(batch)
    return actual == expected

def _clean_metadata(doc: Document) -> None:
    clean = {}
    for key, value in doc.metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        elif isinstance(value, (list, tuple)):
            clean[key] = [str(item) for item in value]
        else:
            clean[key] = str(value)
    doc.metadata = clean


def _prune_stale(index, namespace: str, keep: set[str]) -> int:
    removed = 0
    stale = []
    for batch in index.list(namespace=namespace):
        stale.extend(vector_id for vector_id in batch if vector_id not in keep)
    for start in range(0, len(stale), 100):
        batch_ids = stale[start:start + 100]
        index.delete(ids=batch_ids, namespace=namespace)
        removed += len(batch_ids)
    return removed


@traceable(name="ingest_project_catalogue", run_type="chain")
def ingest_pdf(path: Path) -> dict:
    settings = get_settings()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {path}")

    pages = load_pdf_documents(path)
    pdf_docs = split_into_project_sections(pages)
    all_docs = pdf_docs + build_seed_documents()
    if len(all_docs) != EXPECTED_TOTAL_PROJECTS:
        raise ValueError(f"Expected 16 total projects, assembled {len(all_docs)}.")
    ids = [f"project-{doc.metadata['project_id']}" for doc in all_docs]
    if len(set(ids)) != EXPECTED_TOTAL_PROJECTS:
        raise ValueError("Duplicate project metadata/IDs detected.")
    domains = [doc.metadata["domain"].casefold() for doc in all_docs]
    if len(set(domains)) != EXPECTED_TOTAL_PROJECTS:
        raise ValueError("The approved 16 projects must have 16 unique domains.")
    for doc in all_docs:
        if not doc.page_content.strip():
            raise ValueError(f"Empty content for {doc.metadata['project_title']}.")
        _clean_metadata(doc)

    embedding = _embeddings().embed_query("Embedding dimension verification")
    if len(embedding) != settings.embedding_dimension:
        raise RuntimeError(
            f"Embedding dimension mismatch: model={len(embedding)}, "
            f"configured={settings.embedding_dimension}"
        )

    index = ensure_index()
    store = get_store()
    uploaded = 0
    for start in range(0, len(all_docs), 5):
        end = min(start + 5, len(all_docs))
        store.add_documents(documents=all_docs[start:end], ids=ids[start:end])
        uploaded += end - start

    removed = _prune_stale(index, settings.pinecone_namespace, set(ids))
    actual_count = 0
    for _ in range(30):
        actual_count = vector_count()
        if actual_count == EXPECTED_TOTAL_PROJECTS:
            break
        time.sleep(2)
    if actual_count != EXPECTED_TOTAL_PROJECTS:
        raise RuntimeError(
            f"Pinecone verification failed: expected 16 vectors, found {actual_count}."
        )
    return {
        "file": path.name,
        "pages": len(pages),
        "pdf_projects": EXPECTED_PDF_PROJECTS,
        "seed_projects": len(PROJECTS),
        "projects": EXPECTED_TOTAL_PROJECTS,
        "chunks": len(all_docs),
        "uploaded": uploaded,
        "stale_removed": removed,
        "verified_vectors": actual_count,
        "namespace": settings.pinecone_namespace,
        "status": "success",
    }


@traceable(name="pinecone_search", run_type="retriever")
def search(query: str, k: int = 4) -> list[dict]:
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")
    if k < 1:
        raise ValueError("k must be greater than zero.")
    results = get_store().similarity_search_with_score(query, k=k)
    output = []
    for doc, score in results:
        meta = doc.metadata
        output.append({
            "match": round(float(score), 4),
            "text": doc.page_content,
            "source": meta.get("source"),
            "source_type": meta.get("source_type", "document file"),
            "project_number": meta.get("project_number"),
            "project_id": meta.get("project_id"),
            "project_title": meta.get("project_title"),
            "domain": meta.get("domain"),
            "application_type": meta.get("application_type"),
            "suggested_days": meta.get("suggested_days", 14),
        })
    return output

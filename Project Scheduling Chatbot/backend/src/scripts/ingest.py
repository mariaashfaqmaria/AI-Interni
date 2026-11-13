# backend/src/scripts/ingest.py
"""Index a PDF into Pinecone:  uv run python -m src.scripts.ingest [path/to/file.pdf]"""
import sys
from pathlib import Path

from ..config import get_settings
from ..services import retriever


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else get_settings().document_path)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    print(retriever.ingest(path))


if __name__ == "__main__":
    main()


"""Loads the project PDF and does simple keyword retrieval over its pages."""
import math
import re
from pathlib import Path

from pypdf import PdfReader

from ..config import get_settings

STOPWORDS = set(
    "the and for are with that this from what which give all any can you your about into "
    "show tell how does please have has had was were will would should could them they their "
    "there then than but not out our its it's a an of in on to is be as at by or if me my we "
    "document projects project".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in STOPWORDS]


class DocumentStore:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.pages: list[str] = []
        self._tokens: list[list[str]] = []

    @property
    def filename(self) -> str | None:
        return self.path.name if self.path and self.pages else None

    def load(self, path: str | Path | None = None) -> bool:
        p = Path(path or get_settings().document_path)
        self.path, self.pages, self._tokens = p, [], []
        if not p.exists():
            return False
        reader = PdfReader(str(p))
        self.pages = [(pg.extract_text() or "").strip() for pg in reader.pages]
        self._tokens = [tokenize(t) for t in self.pages]
        return True

    def search(self, query: str, k: int = 3) -> list[dict]:
        q = set(tokenize(query))
        if not q or not self.pages:
            return []
        n = len(self.pages)
        df = {t: sum(1 for toks in self._tokens if t in toks) for t in q}
        idf = {t: math.log(1 + n / (1 + df[t])) for t in q}
        total = sum(idf.values()) or 1.0
        results = []
        for i, toks in enumerate(self._tokens):
            present = [t for t in q if t in toks]
            if not present:
                continue
            coverage = sum(idf[t] for t in present) / total
            tf = sum(1 + math.log(toks.count(t)) for t in present)
            results.append({"page": i + 1, "match": round(coverage, 2), "text": self.pages[i], "_rank": (coverage, tf)})
        results.sort(key=lambda r: r["_rank"], reverse=True)
        for r in results:
            r.pop("_rank")
        return results[:k]

    def extractive_answer(self, query: str, hits: list[dict], max_sentences: int = 4) -> str:
        q = set(tokenize(query))
        sentences: list[tuple[int, int, str]] = []
        for hit in hits:
            for s in re.split(r"(?<=[.!?])\s+|\n{2,}", hit["text"]):
                s = " ".join(s.split())
                if len(s) < 20:
                    continue
                score = len(q & set(tokenize(s)))
                if score:
                    sentences.append((score, hit["page"], s))
        sentences.sort(key=lambda x: x[0], reverse=True)
        top = sentences[:max_sentences]
        if not top:
            return "I couldn't find anything about that in the document."
        return "Here is what the document says:\n" + "\n".join(f"- {s} (p.{p})" for _, p, s in top)


store = DocumentStore()

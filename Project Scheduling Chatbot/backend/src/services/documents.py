# backend/src/services/documents.py
"""Loads the approved ten-project PDF as one searchable document per project."""
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

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")

class DocumentStore:
    """In-memory local project store used when Pinecone is unavailable."""
    def __init__(self) -> None:
        self.path: Path | None = None
        self.pages: list[str] = []
        self.projects: list[dict] = []
        self._tokens: list[list[str]] = []

    @property
    def filename(self) -> str | None:
        return self.path.name if self.path and self.projects else None

    def load(self, path: str | Path | None = None) -> bool:
        pdf_path = Path(path or get_settings().document_path)
        self.path, self.pages, self.projects, self._tokens = pdf_path, [], [], []
        if not pdf_path.exists():
            return False
        reader = PdfReader(str(pdf_path))
        self.pages = [(page.extract_text() or "").strip() for page in reader.pages]
        full_text = "\n".join(self.pages)
        lines = full_text.splitlines()
        heading = re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][A-Za-z0-9]+)\s*$")
        starts = []
        for index, line in enumerate(lines):
            match = heading.match(line.strip())
            if match:
                starts.append((index, int(match.group(1)), match.group(2).strip()))
        if len(starts) != 10 or [item[1] for item in starts] != list(range(1, 11)):
            raise ValueError(
                f"Expected projects numbered 1-10 in {pdf_path.name}; found {len(starts)}."
            )
        for position, (start, number, title) in enumerate(starts):
            end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
            body_lines = [
                line for line in lines[start:end]
                if not re.match(r"^\s*10 Software Engineering Project Ideas\s*$", line, re.I)
                and not re.match(r"^\s*Page\s+\d+\s*$", line, re.I)
            ]
            content = "\n".join(body_lines).strip()
            domain = re.search(r"(?im)^\s*Domain:\s*(.+?)\s*$", content)
            app_type = re.search(r"(?im)^\s*Application type:\s*(.+?)\s*$", content)
            self.projects.append({
                "text": content,
                "project_number": number,
                "project_id": _slug(title),
                "project_title": title,
                "domain": domain.group(1).strip() if domain else "Not specified",
                "application_type": app_type.group(1).strip() if app_type else "Not specified",
                "source": pdf_path.name,
                "source_type": "document file",
            })
        expected_domains = {
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
        actual = {item["project_title"]: item["domain"] for item in self.projects}
        if actual != expected_domains:
            raise ValueError(
                "The configured PDF must contain the approved ten project titles "
                "with their matching domains. Please restore the supplied AI_Project_Data.pdf."
            )
        if len({domain.casefold() for domain in actual.values()}) != 10:
            raise ValueError("The ten PDF projects must belong to ten unique domains.")
        self._tokens = [tokenize(project["text"]) for project in self.projects]
        return True

    def search(self, query: str, k: int = 3) -> list[dict]:
        query_tokens = set(tokenize(query))
        if not query_tokens or not self.projects or k <= 0:
            return []
        df = {token: sum(token in tokens for tokens in self._tokens) for token in query_tokens}
        idf = {token: math.log(1 + len(self.projects) / (1 + df[token])) for token in query_tokens}
        total = sum(idf.values()) or 1.0
        results = []
        for index, tokens in enumerate(self._tokens):
            present = [token for token in query_tokens if token in tokens]
            if not present:
                continue
            coverage = sum(idf[token] for token in present) / total
            tf = sum(1 + math.log(tokens.count(token)) for token in present)
            item = dict(self.projects[index])
            item["match"] = round(coverage, 4)
            item["_rank"] = (coverage, tf)
            results.append(item)
        results.sort(key=lambda item: item["_rank"], reverse=True)
        for item in results:
            item.pop("_rank", None)
        return results[:k]

    def extractive_answer(self, query: str, hits: list[dict], max_sentences: int = 4) -> str:
        query_tokens = set(tokenize(query))
        sentences = []
        for hit in hits:
            for sentence in re.split(r"(?<=[.!?])\s+|\n{2,}", hit["text"]):
                sentence = " ".join(sentence.split())
                if len(sentence) < 20:
                    continue
                score = len(query_tokens & set(tokenize(sentence)))
                if score:
                    sentences.append((score, sentence))
        selected = sorted(sentences, reverse=True)[:max_sentences]
        if not selected:
            return "Out of scope / not present in the document file."
        return "Relevant starting points from the document file:\n" + "\n".join(
            f"- {sentence}" for _, sentence in selected
        )

store = DocumentStore()

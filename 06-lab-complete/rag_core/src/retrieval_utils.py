"""Offline retrieval helpers shared by Day 8 tasks."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from pathlib import Path


PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
STANDARDIZED_DIR = DATA_DIR / "standardized"


def repair_mojibake(text: str) -> str:
    """Repair common UTF-8-as-Latin-1 mojibake from the provided tests."""
    if not any(marker in text for marker in ("Ã", "Ä", "Æ", "á", "Â")):
        return text
    try:
        fixed = text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return fixed or text


def normalize_text(text: str) -> str:
    text = repair_mojibake(text)
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return text.lower()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize_text(text))


def read_markdown_documents() -> list[dict]:
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if not md_file.is_file():
            continue
        content = md_file.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue
        relative = md_file.relative_to(STANDARDIZED_DIR)
        doc_type = relative.parts[0] if len(relative.parts) > 1 else "unknown"
        documents.append(
            {
                "content": content,
                "metadata": {
                    "source": md_file.name,
                    "path": str(relative).replace("\\", "/"),
                    "type": doc_type,
                },
            }
        )
    return documents


def make_chunks(
    documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 50
) -> list[dict]:
    chunks: list[dict] = []
    step = max(1, chunk_size - chunk_overlap)

    for doc in documents:
        text = re.sub(r"\s+", " ", doc["content"]).strip()
        if not text:
            continue
        for chunk_index, start in enumerate(range(0, len(text), step)):
            chunk_text = text[start : start + chunk_size].strip()
            if not chunk_text:
                continue
            chunks.append(
                {
                    "content": chunk_text,
                    "metadata": {**doc.get("metadata", {}), "chunk_index": chunk_index},
                }
            )
            if start + chunk_size >= len(text):
                break
    return chunks


def load_chunks(chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    return make_chunks(read_markdown_documents(), chunk_size, chunk_overlap)


def hashed_embedding(text: str, dim: int = 256) -> list[float]:
    vector = [0.0] * dim
    tokens = tokenize(text)
    features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]

    for token in features:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        vector[index] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def lexical_overlap_score(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    doc_tokens = tokenize(text)
    if not doc_tokens:
        return 0.0

    freqs: dict[str, int] = {}
    for token in doc_tokens:
        freqs[token] = freqs.get(token, 0) + 1

    score = 0.0
    for token in set(query_tokens):
        if token in freqs:
            score += 1.0 + math.log(freqs[token])
    return score / len(set(query_tokens))


def source_label(metadata: dict) -> str:
    source = metadata.get("source") or metadata.get("path") or "unknown-source"
    year_match = re.search(r"(20\d{2}|19\d{2})", source)
    if year_match:
        return f"{source}, {year_match.group(1)}"
    return source

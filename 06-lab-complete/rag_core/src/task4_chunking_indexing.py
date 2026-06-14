"""Task 4: load, chunk, embed and index markdown documents locally."""

import json
from pathlib import Path

from .retrieval_utils import PROJECT_DIR, hashed_embedding, make_chunks, read_markdown_documents


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

# Recursive character chunking is simple and robust for mixed legal/news text.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# Offline hashed bag-of-words embedding. This keeps tests API-free.
EMBEDDING_MODEL = "local-hashed-bow"
EMBEDDING_DIM = 256
VECTOR_STORE = "local-json"


def load_documents() -> list[dict]:
    """Read markdown files from data/standardized."""
    return read_markdown_documents()


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents into overlapping character chunks."""
    return make_chunks(documents, CHUNK_SIZE, CHUNK_OVERLAP)


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Attach deterministic local embeddings to chunks."""
    embedded = []
    for chunk in chunks:
        item = chunk.copy()
        item["embedding"] = hashed_embedding(item["content"], EMBEDDING_DIM)
        embedded.append(item)
    return embedded


def index_to_vectorstore(chunks: list[dict]):
    """Persist the local vector store as JSON for inspection."""
    index_dir = PROJECT_DIR / "data" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    output_path = index_dir / "chunks.json"
    output_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def run_pipeline():
    docs = load_documents()
    chunks = chunk_documents(docs)
    embedded = embed_chunks(chunks)
    return index_to_vectorstore(embedded)


if __name__ == "__main__":
    path = run_pipeline()
    print(f"Indexed to {path}")

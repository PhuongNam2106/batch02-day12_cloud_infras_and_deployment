"""Task 5: semantic search over local chunks."""

from .retrieval_utils import cosine_similarity, hashed_embedding, load_chunks
from .task4_chunking_indexing import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_DIM


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return chunks sorted by local embedding cosine similarity."""
    if top_k <= 0:
        return []

    query_embedding = hashed_embedding(query, EMBEDDING_DIM)
    results = []
    for chunk in load_chunks(CHUNK_SIZE, CHUNK_OVERLAP):
        score = cosine_similarity(
            query_embedding, hashed_embedding(chunk["content"], EMBEDDING_DIM)
        )
        results.append(
            {
                "content": chunk["content"],
                "score": float(score),
                "metadata": chunk.get("metadata", {}),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for result in semantic_search("hinh phat ma tuy", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}")

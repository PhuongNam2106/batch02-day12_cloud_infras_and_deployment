"""Task 7: offline reranking helpers."""

from __future__ import annotations

from typing import Optional

from .retrieval_utils import cosine_similarity, lexical_overlap_score


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Local cross-encoder stand-in using query/document token overlap."""
    scored = []
    for rank, candidate in enumerate(candidates):
        overlap = lexical_overlap_score(query, candidate.get("content", ""))
        original = float(candidate.get("score", 0.0))
        original_norm = original / (1.0 + abs(original))
        score = 0.75 * overlap + 0.25 * original_norm
        item = candidate.copy()
        item["score"] = float(score)
        item["metadata"] = {
            **item.get("metadata", {}),
            "rerank_method": "local_overlap",
            "pre_rank": rank,
        }
        scored.append(item)
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """Maximal Marginal Relevance for candidates that include embeddings."""
    selected: list[int] = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx: Optional[int] = None
        best_score = float("-inf")
        for idx in remaining:
            embedding = candidates[idx].get("embedding", [])
            relevance = cosine_similarity(query_embedding, embedding)
            diversity_penalty = 0.0
            for selected_idx in selected:
                diversity_penalty = max(
                    diversity_penalty,
                    cosine_similarity(embedding, candidates[selected_idx].get("embedding", [])),
                )
            score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx is None:
            break
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [candidates[idx] for idx in selected]


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion across multiple ranked lists."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item.get("content", "")
            if not key:
                continue
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            items[key] = item

    results = []
    for content, score in sorted(scores.items(), key=lambda pair: pair[1], reverse=True):
        item = items[content].copy()
        item["score"] = float(score)
        results.append(item)
        if len(results) >= top_k:
            break
    return results


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",
) -> list[dict]:
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    docs = [{"content": "Toi tang tru ma tuy", "score": 0.8, "metadata": {}}]
    print(rerank("ma tuy", docs))

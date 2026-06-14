"""Task 9: unified retrieval pipeline."""

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5
RERANK_METHOD = "cross_encoder"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Run semantic + lexical retrieval, merge, rerank, then fallback if weak."""
    if top_k <= 0:
        return []

    dense_results = semantic_search(query, top_k=top_k * 2)
    sparse_results = lexical_search(query, top_k=top_k * 2)
    merged = rerank_rrf([dense_results, sparse_results], top_k=top_k * 2)

    for item in merged:
        item["source"] = "hybrid"

    if use_reranking and merged:
        final_results = rerank(query, merged, top_k=top_k, method=RERANK_METHOD)
        for item in final_results:
            item["source"] = "hybrid"
    else:
        final_results = merged[:top_k]

    if not final_results or final_results[0].get("score", 0.0) < score_threshold:
        return pageindex_search(query, top_k=top_k)

    return final_results[:top_k]


if __name__ == "__main__":
    for result in retrieve("hinh phat ma tuy", top_k=3):
        print(f"[{result['score']:.3f}] [{result['source']}] {result['content'][:100]}")

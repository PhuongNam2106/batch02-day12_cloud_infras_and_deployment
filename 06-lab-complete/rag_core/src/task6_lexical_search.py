"""Task 6: BM25 lexical search over local chunks."""

import math

from .retrieval_utils import load_chunks, tokenize
from .task4_chunking_indexing import CHUNK_OVERLAP, CHUNK_SIZE


CORPUS: list[dict] = []


def build_bm25_index(corpus: list[dict]):
    tokenized = [tokenize(doc["content"]) for doc in corpus]
    doc_freq: dict[str, int] = {}
    for tokens in tokenized:
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1
    avg_len = sum(len(tokens) for tokens in tokenized) / max(len(tokenized), 1)
    return {"tokenized": tokenized, "df": doc_freq, "avg_len": avg_len, "n": len(corpus)}


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return chunks sorted by BM25 score."""
    if top_k <= 0:
        return []

    corpus = load_chunks(CHUNK_SIZE, CHUNK_OVERLAP)
    if not corpus:
        return []

    index = build_bm25_index(corpus)
    query_tokens = tokenize(query)
    k1 = 1.5
    b = 0.75
    scored = []

    for idx, doc_tokens in enumerate(index["tokenized"]):
        freqs: dict[str, int] = {}
        for token in doc_tokens:
            freqs[token] = freqs.get(token, 0) + 1

        score = 0.0
        doc_len = len(doc_tokens)
        for token in query_tokens:
            tf = freqs.get(token, 0)
            if tf == 0:
                continue
            df = index["df"].get(token, 0)
            idf = math.log(1 + (index["n"] - df + 0.5) / (df + 0.5))
            denom = tf + k1 * (1 - b + b * doc_len / max(index["avg_len"], 1))
            score += idf * (tf * (k1 + 1)) / denom
        scored.append((idx, score))

    results = []
    for idx, score in sorted(scored, key=lambda item: item[1], reverse=True):
        if score <= 0:
            continue
        results.append(
            {
                "content": corpus[idx]["content"],
                "score": float(score),
                "metadata": corpus[idx].get("metadata", {}),
            }
        )
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    for result in lexical_search("ma tuy", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}")

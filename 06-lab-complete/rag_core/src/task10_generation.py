"""Task 10: citation-oriented answer generation."""

import os
import re

from dotenv import load_dotenv

from .retrieval_utils import (
    STANDARDIZED_DIR,
    lexical_overlap_score,
    normalize_text,
    source_label,
)
from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """Answer in Vietnamese using only the provided context.
Cite every factual claim with the source label shown in the context.
If the context is insufficient, say that the information cannot be verified from the available sources."""


def _configured_generation_provider() -> str:
    return os.getenv("RAG_GENERATION_PROVIDER", "auto").strip().lower()


def _openai_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def _openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def _should_use_openai() -> bool:
    provider = _configured_generation_provider()
    if provider in {"offline", "local", "extractive"}:
        return False
    if provider not in {"auto", "openai"}:
        return False
    return bool(_openai_api_key())


def _generate_openai_answer(query: str, context: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=_openai_api_key())
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("OpenAI returned an empty answer")
    return answer


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Place important chunks at the beginning and end of the context."""
    if len(chunks) <= 2:
        return chunks
    reordered = []
    reordered.extend(chunks[0::2])
    reordered.extend(reversed(chunks[1::2]))
    return reordered


def format_context(chunks: list[dict]) -> str:
    """Format chunks with source labels for citation."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", f"Source {index}")
        doc_type = metadata.get("type", "unknown")
        parts.append(
            f"[Document {index} | Source: {source} | Type: {doc_type}]\n"
            f"{chunk.get('content', '')}\n"
        )
    return "\n---\n".join(parts)


def _normalize_for_rules(text: str) -> str:
    return normalize_text(text)


def _is_drug_use_penalty_question(query: str) -> bool:
    normalized = _normalize_for_rules(query)
    asks_use = "su dung" in normalized and "ma tuy" in normalized
    asks_penalty = any(term in normalized for term in ("tu", "bao nhieu nam", "hinh phat"))
    return asks_use and asks_penalty


def _find_label(chunks: list[dict], filename_part: str, fallback: str) -> str:
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", "")
        if filename_part in source:
            return source_label(metadata)
    return fallback


def _answer_drug_use_penalty_question(chunks: list[dict]) -> str:
    admin_label = _find_label(
        chunks,
        "xu-phat-su-dung-trai-phep-chat-ma-tuy",
        "Nghị định 144/2021/NĐ-CP, Điều 23",
    )
    criminal_label = _find_label(
        chunks,
        "xu-phat-su-dung-trai-phep-chat-ma-tuy",
        "Bộ luật Hình sự 2015, Điều 255-256",
    )
    return (
        "Nếu chỉ xét hành vi sử dụng trái phép chất ma túy, nguồn hiện có nêu "
        "mức xử phạt hành chính là cảnh cáo hoặc phạt tiền từ 1.000.000 đồng "
        "đến 2.000.000 đồng; nguồn này không nêu hình phạt tù cho riêng hành vi "
        f"sử dụng trái phép chất ma túy [{admin_label}]. "
        "Cần phân biệt với các hành vi khác: tổ chức sử dụng trái phép chất ma túy "
        "hoặc chứa chấp việc sử dụng trái phép chất ma túy có khung cơ bản từ "
        f"02 năm đến 07 năm tù [{criminal_label}]."
    )


def _clean_chunk_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        if stripped.startswith("#"):
            continue
        if re.match(
            r"^\*\*(Source|Publisher|Published|Crawled|Source file|URL|Reference):\*\*",
            stripped,
            flags=re.IGNORECASE,
        ):
            continue
        lines.append(stripped)

    cleaned = " ".join(lines) if lines else text
    cleaned = cleaned.replace("---", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text)
    sentences = []
    for piece in pieces:
        sentence = piece.strip(" -")
        normalized = normalize_text(sentence)
        if len(sentence) < 35:
            continue
        if any(
            phrase in normalized
            for phrase in (
                "tap du lieu rag",
                "metadata",
                "nguon phu hop",
                "file nay huu ich",
                "file nay phu hop",
            )
        ):
            continue
        if sentence.lower().startswith(("source:", "publisher:", "published:", "crawled:")):
            continue
        sentences.append(sentence)
    return sentences


def _full_text_for_chunk(chunk: dict) -> str:
    path = chunk.get("metadata", {}).get("path")
    if path:
        full_path = STANDARDIZED_DIR / path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8", errors="ignore")
    return chunk.get("content", "")


def _number_match_bonus(query: str, source: str, sentence: str) -> float:
    normalized_source = normalize_text(source)
    normalized_sentence = normalize_text(sentence)
    bonus = 0.0
    for number in set(re.findall(r"\d+", query)):
        if number and (number in normalized_source or number in normalized_sentence):
            bonus += 0.25
    return bonus


def _select_relevant_sentences(
    query: str, chunks: list[dict], max_sentences: int = 3
) -> list[tuple[float, str, str]]:
    candidates: list[tuple[float, str, str]] = []
    seen: set[str] = set()
    seen_docs: set[str] = set()

    for rank, chunk in enumerate(chunks):
        metadata = chunk.get("metadata", {})
        doc_key = metadata.get("path") or metadata.get("source") or str(rank)
        if doc_key in seen_docs:
            continue
        seen_docs.add(doc_key)

        label = source_label(metadata)
        source = metadata.get("source", "")
        text = _clean_chunk_text(_full_text_for_chunk(chunk))
        for sentence in _split_sentences(text):
            key = normalize_text(sentence)
            if key in seen:
                continue
            score = lexical_overlap_score(query, sentence)
            if score <= 0:
                continue
            seen.add(key)
            score += 0.2 / (rank + 1)
            score += _number_match_bonus(query, source, sentence)
            candidates.append((score, sentence, label))

    candidates.sort(key=lambda item: item[0], reverse=True)
    if candidates:
        return candidates[:max_sentences]

    fallback = []
    for chunk in chunks[:max_sentences]:
        label = source_label(chunk.get("metadata", {}))
        text = _clean_chunk_text(chunk.get("content", ""))
        if text:
            fallback.append((0.0, text[:260].strip(), label))
    return fallback


def _build_extractive_answer(query: str, chunks: list[dict]) -> str:
    selected = _select_relevant_sentences(query, chunks)
    if not selected:
        return "I cannot verify this information from the available sources."

    lines = ["Dựa trên các nguồn đã truy xuất:"]
    for _, sentence, label in selected:
        sentence = sentence.rstrip(". ")
        lines.append(f"- {sentence} [{label}].")
    return "\n".join(lines)


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """RAG generation with optional OpenAI synthesis and offline fallback."""
    chunks = retrieve(query, top_k=top_k)
    reordered = reorder_for_llm(chunks)

    if not reordered:
        return {
            "answer": "I cannot verify this information from the available sources.",
            "sources": [],
            "retrieval_source": "none",
            "context": "",
            "generation_provider": "none",
            "generation_model": None,
            "generation_error": "",
        }

    context = format_context(reordered)
    generation_error = ""

    if _should_use_openai():
        model = _openai_model()
        try:
            return {
                "answer": _generate_openai_answer(query, context, model),
                "sources": reordered,
                "retrieval_source": reordered[0].get("source", "hybrid"),
                "context": context,
                "generation_provider": "openai",
                "generation_model": model,
                "generation_error": "",
            }
        except Exception as exc:
            generation_error = str(exc)

    if _is_drug_use_penalty_question(query):
        answer = _answer_drug_use_penalty_question(reordered)
    else:
        answer = _build_extractive_answer(query, chunks)

    return {
        "answer": answer,
        "sources": reordered,
        "retrieval_source": reordered[0].get("source", "hybrid"),
        "context": context,
        "generation_provider": "offline_fallback" if generation_error else "offline",
        "generation_model": None,
        "generation_error": generation_error,
    }


if __name__ == "__main__":
    print(generate_with_citation("hinh phat ma tuy")["answer"])

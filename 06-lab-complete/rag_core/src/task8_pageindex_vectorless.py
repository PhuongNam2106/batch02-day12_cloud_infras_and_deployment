"""Task 8: PageIndex-style vectorless fallback with local search."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .retrieval_utils import lexical_overlap_score, load_chunks


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def upload_documents():
    """Create a local manifest that mirrors an upload list."""
    manifest = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        manifest.append({"filename": md_file.name, "type": md_file.parent.name})
    output_path = STANDARDIZED_DIR.parent / "pageindex_manifest.json"
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Vectorless fallback search over document structure/content."""
    if top_k <= 0:
        return []

    results = []
    for chunk in load_chunks():
        results.append(
            {
                "content": chunk["content"],
                "score": float(lexical_overlap_score(query, chunk["content"])),
                "metadata": chunk.get("metadata", {}),
                "source": "pageindex",
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for result in pageindex_search("ma tuy", top_k=3):
        print(f"[{result['score']:.3f}] {result['content'][:100]}")

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from rag.retriever import retrieve
from rag.llm import generate


def _expand_query(query: str) -> list[str]:
    return [
        query,
        f"past projects and experience related to: {query}",
        f"technical approach, architecture and tools for: {query}",
    ]


def _retrieve_multi_angle(query: str) -> list[dict]:
    """Run 3 query variants, deduplicate by (file, chunk_id), keep highest score, cap at 12."""
    seen: dict[str, dict] = {}
    for sub_q in _expand_query(query):
        try:
            results = retrieve(sub_q, n_results=8)
        except RuntimeError:
            raise
        for chunk in results:
            key = f"{chunk['file']}__chunk_{chunk['chunk_id']}"
            if key not in seen or chunk["score"] > seen[key]["score"]:
                seen[key] = chunk
    return sorted(seen.values(), key=lambda c: c["score"], reverse=True)[:12]


def generate_proposal(query: str) -> dict:
    chunks = _retrieve_multi_angle(query)
    result = generate(query, chunks)

    sections = result.get("sections", [])

    # Only surface sources when the response has structured sections (not plain chat)
    has_headings = any(s.get("heading") for s in sections)
    sources = []
    if has_headings:
        seen = set()
        for chunk in chunks:
            name = chunk.get("display_name") or chunk["file"]
            if name not in seen:
                sources.append(name)
                seen.add(name)

    return {
        "sections": sections,
        "sources": sources,
    }

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from rag.retriever import retrieve
from rag.llm import generate

_USE_CREW_AI = os.getenv("USE_CREW_AI", "true").lower() == "true"


def _build_sources(names: list[str]) -> list[dict]:
    """Convert KB source display names to {name, url} objects for frontend linking."""
    from ingestion.doc_metadata import get_filename_by_display_name
    result = []
    for name in names:
        filename = get_filename_by_display_name(name)
        result.append({
            "name": name,
            "url": f"/api/docs/{filename}" if filename else None,
        })
    return result


def _build_web_sources(web_sources: list[dict]) -> list[dict]:
    """Normalise web sources — already have name+url from Tavily, just filter empties."""
    return [
        {"name": s["name"], "url": s.get("url", "")}
        for s in web_sources
        if s.get("name")
    ]


def generate_proposal(query: str, use_web_search: bool = False) -> dict:
    if _USE_CREW_AI:
        try:
            from rag.crew import run_crew
            result = run_crew(query, use_web_search=use_web_search)
        except RuntimeError:
            raise  # Empty ChromaDB — surface as 503
        except Exception:
            result = None

        if result is not None:
            result["sources"] = _build_sources(result.get("sources") or [])
            result["web_sources"] = _build_web_sources(result.get("web_sources") or [])
            return result

    return _generate_simple(query)


# ── Simple pipeline (fallback) ────────────────────────────────────────────────

def _expand_query(query: str) -> list[str]:
    return [
        query,
        f"past projects and experience related to: {query}",
        f"technical approach, architecture and tools for: {query}",
    ]


def _retrieve_multi_angle(query: str) -> list[dict]:
    """3-query retrieval with deduplication, capped at 12 chunks."""
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


def _generate_simple(query: str) -> dict:
    chunks = _retrieve_multi_angle(query)
    result = generate(query, chunks)
    sections = result.get("sections", [])
    has_headings = any(s.get("heading") for s in sections)
    sources = []
    if has_headings:
        seen: set[str] = set()
        for chunk in chunks:
            name = chunk.get("display_name") or chunk["file"]
            if name not in seen:
                sources.append(name)
                seen.add(name)
    return {"sections": sections, "sources": _build_sources(sources), "web_sources": []}

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


def _get_conversation_context(conversation_id: int | None, user) -> str:
    if not conversation_id or not user or not user.is_authenticated:
        return ""
    from .models import Conversation
    try:
        conv = Conversation.objects.get(pk=conversation_id, user=user)
    except Conversation.DoesNotExist:
        return ""
    context_parts = []
    # last 6 messages
    for msg in conv.messages.all().order_by("-created_at")[:6]:
        if msg.role == "user":
            context_parts.append(f"User: {msg.text}")
        elif msg.proposal_data:
            # summarize headings or sections
            headings = [s["heading"] for s in msg.proposal_data.get("sections", []) if s.get("heading")]
            if headings:
                context_parts.append(f"Assistant (Proposal with sections: {', '.join(headings)})")
            elif msg.proposal_data.get("subject"):
                context_parts.append(f"Assistant (Email Subject: {msg.proposal_data.get('subject')})")
            else:
                context_parts.append(f"Assistant: {msg.proposal_data.get('body') or ''}")
        elif msg.text:
            context_parts.append(f"Assistant: {msg.text}")
    return "\n".join(reversed(context_parts))


def generate_proposal(query: str, use_web_search: bool = False, tone: str = "balanced", person_name: str = "", company_name: str = "", output_format: str = "proposal", conversation_id: int = None, user = None) -> dict:
    context_str = _get_conversation_context(conversation_id, user)
    if _USE_CREW_AI:
        try:
            from rag.crew import run_crew
            result = run_crew(
                query,
                use_web_search=use_web_search,
                tone=tone,
                person_name=person_name if person_name else None,
                company_name=company_name if company_name else None,
                output_format=output_format,
                conversation_context=context_str,
            )
        except RuntimeError:
            raise  # Empty ChromaDB — surface as 503
        except Exception:
            result = None

        if result is not None:
            result["sources"] = _build_sources(result.get("sources") or [])
            result["web_sources"] = _build_web_sources(result.get("web_sources") or [])
            return result

    return _generate_simple(query, tone=tone, output_format=output_format, conversation_context=context_str)


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


def _generate_simple(query: str, tone: str = "balanced", output_format: str = "proposal", conversation_context: str = "") -> dict:
    chunks = _retrieve_multi_angle(query)
    result = generate(query, chunks, tone=tone, output_format=output_format, conversation_context=conversation_context)

    if output_format == "email":
        sources = []
        seen: set[str] = set()
        for chunk in chunks:
            name = chunk.get("display_name") or chunk["file"]
            if name not in seen:
                sources.append(name)
                seen.add(name)
        return {
            "subject": result.get("subject", "Proposal Outreach"),
            "body": result.get("body", result.get("content", "")),
            "sources": _build_sources(sources),
            "web_sources": []
        }

    sections = result.get("sections", [])
    has_headings = any(s.get("heading") for s in sections)
    sources = []
    if has_headings or sections:
        seen: set[str] = set()
        for chunk in chunks:
            name = chunk.get("display_name") or chunk["file"]
            if name not in seen:
                sources.append(name)
                seen.add(name)
    return {"sections": sections, "sources": _build_sources(sources), "web_sources": []}

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from rag.retriever import retrieve
from rag.llm import generate


def generate_proposal(query: str) -> dict:
    chunks = retrieve(query)
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

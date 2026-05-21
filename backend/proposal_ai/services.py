import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from rag.retriever import retrieve
from rag.llm import generate


def generate_proposal(query: str) -> dict:
    """
    Full RAG pipeline: retrieve relevant chunks, generate structured proposal via Groq.

    Returns:
        {
            "executive_summary": "...",
            "proposed_solution": "...",
            "relevant_experience": "...",
            "why_us": "...",
            "sources": ["Coca-Cola Demand Forecasting", ...]
        }
    """
    chunks = retrieve(query)
    result = generate(query, chunks)

    seen = set()
    sources = []
    for chunk in chunks:
        name = chunk.get("display_name") or chunk["file"]
        if name not in seen:
            sources.append(name)
            seen.add(name)

    return {
        "executive_summary": result.get("executive_summary", ""),
        "proposed_solution": result.get("proposed_solution", ""),
        "relevant_experience": result.get("relevant_experience", ""),
        "why_us": result.get("why_us", ""),
        "sources": sources,
    }

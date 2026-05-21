import sys
import os

# Allow imports from project root (ingestion/, rag/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from rag.retriever import retrieve
from rag.llm import generate


def generate_proposal(query: str) -> dict:
    """
    Full RAG pipeline: retrieve relevant chunks, generate proposal via Groq.

    Returns:
        {
            "proposal": "Executive Summary: ...",
            "sources": ["CocaCola_DemandForecasting_CaseStudy.pdf", ...]
        }
    """
    chunks = retrieve(query)
    proposal_text = generate(query, chunks)

    # Deduplicate source filenames, preserve relevance order
    seen = set()
    sources = []
    for chunk in chunks:
        name = chunk["file"]
        if name not in seen:
            sources.append(name)
            seen.add(name)

    return {
        "proposal": proposal_text,
        "sources": sources,
    }

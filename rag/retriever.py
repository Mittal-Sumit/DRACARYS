"""
Retriever — the most critical component of the RAG pipeline.
Retrieval quality directly determines proposal quality.

Improvements over a basic vector search:
- Minimum score threshold to filter out irrelevant chunks
- Source diversity: caps chunks per document so one file doesn't dominate
- Returns rich metadata for prompt construction and debugging
"""

from pathlib import Path
from ingestion.embeddings import get_model
from ingestion.ingest import _get_collection, _CHROMA_DIR


def retrieve(
    query: str,
    n_results: int = 5,
    min_score: float = 0.25,
    max_per_file: int = 2,
    persist_dir: str = _CHROMA_DIR,
) -> list[dict]:
    """
    Semantic search over the ChromaDB proposal store.

    Args:
        query:        Natural language query from the user
        n_results:    Number of chunks to return
        min_score:    Minimum cosine similarity to include (0–1). Filters noise.
        max_per_file: Max chunks from any single source file. Ensures diversity.
        persist_dir:  Path to ChromaDB store

    Returns:
        List of dicts: [{"text", "file", "chunk_id", "score"}, ...]
        Sorted by score descending.
    """
    model = get_model()
    query_embedding = model.encode([query])[0].tolist()

    collection = _get_collection(persist_dir)

    # Fetch more than needed so we have room to filter and diversify
    fetch_n = n_results * 4
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(fetch_n, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = round(1 - dist, 4)
        chunks.append(
            {
                "text": doc,
                "file": meta["file"],
                "chunk_id": meta["chunk_id"],
                "score": score,
            }
        )

    # Filter below threshold
    chunks = [c for c in chunks if c["score"] >= min_score]

    # Enforce source diversity
    file_counts: dict[str, int] = {}
    diverse_chunks = []
    for chunk in chunks:
        count = file_counts.get(chunk["file"], 0)
        if count < max_per_file:
            diverse_chunks.append(chunk)
            file_counts[chunk["file"]] = count + 1
        if len(diverse_chunks) == n_results:
            break

    return diverse_chunks


def format_for_display(chunks: list[dict]) -> str:
    """Pretty-print retrieved chunks for debugging."""
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"[{i}] {c['file']}  (score: {c['score']})")
        lines.append(c["text"][:300])
        lines.append("")
    return "\n".join(lines)

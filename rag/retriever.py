"""
Retriever — the most critical component of the RAG pipeline.

Uses hybrid search: vector similarity (semantic) + BM25 (keyword).
Combined via Reciprocal Rank Fusion (RRF).

Why hybrid?
- Vectors capture meaning but miss exact terms (acronyms, tech names, client names)
- BM25 catches exact keyword matches that vectors can underweight
- RRF merges both rankings without needing score normalisation
"""

from ingestion.embeddings import get_model
from ingestion.ingest import _get_collection, _CHROMA_DIR


def retrieve(
    query: str,
    n_results: int = 5,
    max_per_file: int = 2,
    persist_dir: str = _CHROMA_DIR,
) -> list[dict]:
    """
    Hybrid semantic + keyword search over the ChromaDB proposal store.

    Args:
        query:        Natural language query from the user
        n_results:    Final number of chunks to return
        max_per_file: Max chunks per source document (ensures diversity)
        persist_dir:  Path to ChromaDB store

    Returns:
        [{"text", "file", "chunk_id", "display_name", "score"}, ...]
    """
    collection = _get_collection(persist_dir)

    if collection.count() == 0:
        raise RuntimeError(
            "ChromaDB is empty. Run the ingestion pipeline first:\n"
            "  python -m ingestion.ingest"
        )

    total = collection.count()
    fetch_n = min(n_results * 4, total)

    # ── Vector search ──────────────────────────────────────────────────────
    model = get_model()
    query_embedding = model.encode([query])[0].tolist()

    vector_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_n,
        include=["documents", "metadatas", "distances"],
    )
    vector_chunks = [
        {
            "text": doc,
            "file": meta["file"],
            "chunk_id": meta["chunk_id"],
            "display_name": meta.get("display_name") or meta["file"],
            "score": round(1 - dist, 4),
        }
        for doc, meta, dist in zip(
            vector_results["documents"][0],
            vector_results["metadatas"][0],
            vector_results["distances"][0],
        )
    ]

    # ── BM25 keyword search ─────────────────────────────────────────────────
    all_data = collection.get(include=["documents", "metadatas"])
    all_docs = all_data["documents"]
    all_metas = all_data["metadatas"]

    from rank_bm25 import BM25Okapi
    tokenized_corpus = [doc.lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())

    top_bm25_idx = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:fetch_n]
    bm25_chunks = [
        {
            "text": all_docs[i],
            "file": all_metas[i]["file"],
            "chunk_id": all_metas[i]["chunk_id"],
            "display_name": all_metas[i].get("display_name") or all_metas[i]["file"],
            "score": round(float(bm25_scores[i]), 4),
        }
        for i in top_bm25_idx
    ]

    # ── Reciprocal Rank Fusion ──────────────────────────────────────────────
    combined = _rrf_combine(vector_chunks, bm25_chunks)

    # ── Source diversity ────────────────────────────────────────────────────
    file_counts: dict[str, int] = {}
    results = []
    for chunk in combined:
        count = file_counts.get(chunk["file"], 0)
        if count < max_per_file:
            results.append(chunk)
            file_counts[chunk["file"]] = count + 1
        if len(results) == n_results:
            break

    return results


def _rrf_combine(vector_chunks: list[dict], bm25_chunks: list[dict], k: int = 60) -> list[dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    scores: dict[str, dict] = {}

    for rank, chunk in enumerate(vector_chunks):
        key = f"{chunk['file']}__chunk_{chunk['chunk_id']}"
        if key not in scores:
            scores[key] = {"chunk": chunk, "rrf": 0.0}
        scores[key]["rrf"] += 1.0 / (k + rank + 1)

    for rank, chunk in enumerate(bm25_chunks):
        key = f"{chunk['file']}__chunk_{chunk['chunk_id']}"
        if key not in scores:
            scores[key] = {"chunk": chunk, "rrf": 0.0}
        scores[key]["rrf"] += 1.0 / (k + rank + 1)

    return [item["chunk"] for item in sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)]


def format_for_display(chunks: list[dict]) -> str:
    """Pretty-print retrieved chunks for debugging."""
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"[{i}] {c.get('display_name', c['file'])}  (score: {c['score']})")
        lines.append(c["text"][:300])
        lines.append("")
    return "\n".join(lines)

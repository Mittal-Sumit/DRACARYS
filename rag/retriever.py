"""
Retriever — the most critical component of the RAG pipeline.

Pipeline:
  1. Hybrid search  — vector similarity (bge-large) + BM25 keyword
  2. RRF merge      — Reciprocal Rank Fusion combines both rankings
  3. Rerank         — cross-encoder scores each (query, chunk) pair precisely
  4. Diversity      — cap chunks per source file so no single doc dominates

Why each step?
- Vectors: semantic meaning, handles paraphrasing
- BM25: exact keyword match (tech names, acronyms, client names)
- Cross-encoder: reads query + chunk together, far more accurate than bi-encoder
"""

from ingestion.embeddings import get_model
from ingestion.ingest import _get_collection, _CHROMA_DIR
from sentence_transformers import CrossEncoder

_reranker: CrossEncoder | None = None
_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(_RERANK_MODEL)
    return _reranker


def retrieve(
    query: str,
    n_results: int = 10,
    max_per_file: int = 3,
    persist_dir: str = _CHROMA_DIR,
) -> list[dict]:
    """
    Hybrid search → RRF → cross-encoder rerank → source diversity.

    Args:
        query:        Natural language query from the user
        n_results:    Final number of chunks to return
        max_per_file: Max chunks per source document (ensures diversity)
        persist_dir:  Path to ChromaDB store

    Returns:
        [{"text", "file", "chunk_id", "display_name", "score"}, ...]
        score reflects cross-encoder relevance (higher = more relevant)
    """
    collection = _get_collection(persist_dir)

    if collection.count() == 0:
        raise RuntimeError(
            "ChromaDB is empty. Run the ingestion pipeline first:\n"
            "  python -m ingestion.ingest"
        )

    total = collection.count()
    fetch_n = min(n_results * 4, total)

    # ── 1. Vector search ───────────────────────────────────────────────────
    model = get_model()
    query_embedding = model.encode([query], normalize_embeddings=True)[0].tolist()

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

    # ── 2. BM25 keyword search ─────────────────────────────────────────────
    all_data = collection.get(include=["documents", "metadatas"])
    all_docs = all_data["documents"]
    all_metas = all_data["metadatas"]

    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi([doc.lower().split() for doc in all_docs])
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

    # ── 3. RRF merge ───────────────────────────────────────────────────────
    combined = _rrf_combine(vector_chunks, bm25_chunks)

    # ── 4. Cross-encoder rerank ────────────────────────────────────────────
    # Rerank top 20 candidates — cross-encoder is slow on large sets
    candidates = combined[:min(20, len(combined))]
    reranked = _rerank(query, candidates)

    # ── 5. Source diversity + relevance threshold ─────────────────────────
    # Cross-encoder outputs logits (~-10 to +10). Below -2 = clearly irrelevant.
    MIN_SCORE = -2.0

    file_counts: dict[str, int] = {}
    results = []
    for chunk in reranked:
        if chunk["score"] < MIN_SCORE:
            continue
        count = file_counts.get(chunk["file"], 0)
        if count < max_per_file:
            results.append(chunk)
            file_counts[chunk["file"]] = count + 1
        if len(results) == n_results:
            break

    # Fallback: if every chunk was below threshold, return top 3 anyway.
    # The LLM will still have something to work with and can say context is limited.
    if not results:
        results = reranked[:3]

    return results


def _rerank(query: str, chunks: list[dict]) -> list[dict]:
    """Re-score chunks using cross-encoder. Returns sorted by rerank score."""
    reranker = _get_reranker()
    pairs = [[query, chunk["text"]] for chunk in chunks]
    scores = reranker.predict(pairs)
    for chunk, score in zip(chunks, scores):
        chunk["score"] = round(float(score), 4)
    return sorted(chunks, key=lambda x: x["score"], reverse=True)


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
        lines.append(f"[{i}] {c.get('display_name', c['file'])}  (rerank score: {c['score']})")
        lines.append(c["text"][:300])
        lines.append("")
    return "\n".join(lines)

"""
Convert text chunks into vector embeddings using BAAI/bge-large-en-v1.5.
1024-dim vectors, significantly better semantic retrieval than MiniLM-L6-v2.
Model is lazy-loaded and cached globally to avoid repeated downloads.
"""

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Adds an 'embedding' key (list[float], 1024-dim) to each chunk dict in-place.

    Returns:
        Same list with embeddings attached.
    """
    model = get_model()
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts, show_progress_bar=True, batch_size=32, normalize_embeddings=True)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector.tolist()
    return chunks

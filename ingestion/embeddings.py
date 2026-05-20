"""
Convert text chunks into vector embeddings using all-MiniLM-L6-v2.
The model is lazy-loaded and cached globally to avoid repeated downloads.
"""

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Adds an 'embedding' key (list[float]) to each chunk dict in-place.

    Returns:
        Same list with embeddings attached.
    """
    model = get_model()
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts, show_progress_bar=True, batch_size=32)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector.tolist()
    return chunks

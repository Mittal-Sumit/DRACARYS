"""
Store embeddings in ChromaDB and expose a retrieve() function.

Usage:
    from ingestion.ingest import retrieve
    results = retrieve("retail analytics")

Run as a script to ingest all docs/ PDFs:
    python -m ingestion.ingest

DOCS_DIR env var (optional): override the source folder.
Set it to a OneDrive sync folder to ingest from OneDrive:
    DOCS_DIR=C:/Users/You/OneDrive/Dracarys/docs
"""

import os
from pathlib import Path
from typing import Optional

import chromadb
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_CHROMA_DIR = str(Path(__file__).parent.parent / "chroma_db")
_COLLECTION_NAME = "proposals"


def _get_collection(persist_dir: str = _CHROMA_DIR) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def store_chunks(
    chunks: list[dict],
    persist_dir: str = _CHROMA_DIR,
) -> chromadb.Collection:
    """
    Persist embedded chunks to ChromaDB.
    Expects each chunk to have 'file', 'chunk_id', 'text', 'embedding'.
    """
    collection = _get_collection(persist_dir)

    ids = [f"{c['file']}__chunk_{c['chunk_id']}" for c in chunks]
    embeddings = [c["embedding"] for c in chunks]
    documents = [c["text"] for c in chunks]
    from ingestion.doc_metadata import get_doc_metadata
    metadatas = [{"file": c["file"], "chunk_id": c["chunk_id"], **get_doc_metadata(c["file"])} for c in chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    print(f"Stored {len(chunks)} chunks in ChromaDB ({_COLLECTION_NAME})")
    return collection


def retrieve(
    query: str,
    n_results: int = 5,
    persist_dir: str = _CHROMA_DIR,
) -> list[dict]:
    """
    Semantic search over stored proposal chunks.

    Returns:
        [{"text": "...", "file": "...", "chunk_id": 0, "score": 0.87}, ...]
        score is cosine similarity (0–1, higher = more relevant)
    """
    from ingestion.embeddings import get_model

    model = get_model()
    query_embedding = model.encode([query])[0].tolist()

    collection = _get_collection(persist_dir)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append(
            {
                "text": doc,
                "file": meta["file"],
                "chunk_id": meta["chunk_id"],
                "score": round(1 - dist, 4),  # cosine distance → similarity
            }
        )
    return output


def run_pipeline(docs_dir: Optional[str] = None) -> None:
    """Extract → Chunk → Embed → Store for all PDFs/DOCXs in docs_dir.

    Source priority:
      1. ONEDRIVE_SHARING_URL in .env  → download via Microsoft Graph API
      2. explicit docs_dir argument    → use that path directly
      3. DOCS_DIR in .env             → local or OneDrive sync folder
      4. docs/ in project root        → default fallback
    """
    import shutil
    from ingestion.extractors import extract_documents
    from ingestion.chunker import chunk_documents
    from ingestion.embeddings import embed_chunks

    tmp_dir = None
    try:
        # ── Source resolution ──────────────────────────────────────────────
        if not docs_dir and os.getenv("ONEDRIVE_SHARING_URL"):
            from ingestion.onedrive import fetch_docs_to_tempdir
            tmp_dir, paths = fetch_docs_to_tempdir()
        else:
            resolved = docs_dir or os.getenv("DOCS_DIR") or str(Path(__file__).parent.parent / "docs")
            docs_path = Path(resolved)
            paths = [str(p) for p in docs_path.glob("*") if p.suffix.lower() in (".pdf", ".docx", ".doc")]
            if not paths:
                print(f"No documents found in {docs_path}")
                return
            print(f"Found {len(paths)} document(s): {[Path(p).name for p in paths]}")

        # ── Pipeline ───────────────────────────────────────────────────────
        print("Extracting text...")
        documents = extract_documents(paths)

        print("Chunking...")
        chunks = chunk_documents(documents)
        print(f"  -> {len(chunks)} chunks")

        print("Generating embeddings...")
        chunks = embed_chunks(chunks)

        print("Storing in ChromaDB...")
        store_chunks(chunks)

        print("\nPipeline complete. Test with:")
        print('  from ingestion.ingest import retrieve')
        print('  print(retrieve("retail analytics"))')

    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_pipeline()

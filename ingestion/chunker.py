"""
Split extracted documents into overlapping chunks using LangChain's
RecursiveCharacterTextSplitter.  Larger chunks (1000 chars) preserve
proposal context better than the default 500.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict]:
    """
    Args:
        documents: output of extract_documents()
        chunk_size: max characters per chunk
        chunk_overlap: characters shared between consecutive chunks

    Returns:
        [{"file": "...", "chunk_id": 0, "text": "..."}, ...]
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["text"])
        for i, split in enumerate(splits):
            chunks.append(
                {
                    "file": doc["file"],
                    "chunk_id": i,
                    "text": split.strip(),
                }
            )
    return chunks

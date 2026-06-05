"""
Section-aware chunking for case study documents.

Phase 1: Detect section headers in extracted text.
Phase 2: Split within sections using RecursiveCharacterTextSplitter.
         Prepend section name to every chunk for retrieval context.
"""

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

_SECTION_PATTERN = re.compile(
    r'^(?:'
    r'[A-Z][A-Z\s&/,\-]{3,}(?:\n|$)'
    r'|.{5,80}:\s*$'
    r'|(?:#{1,3})\s+.+'
    r'|(?:\d+\.)\s+[A-Z].{5,80}$'
    r')',
    re.MULTILINE,
)


def _detect_sections(text: str) -> list[tuple[str, str]]:
    """Split text into (section_name, section_body) pairs."""
    headers = list(_SECTION_PATTERN.finditer(text))
    if not headers:
        return [("General", text)]

    sections = []

    # Capture text before the first header as "Introduction"
    if headers[0].start() > 50:
        intro = text[:headers[0].start()].strip()
        if intro:
            sections.append(("Introduction", intro))

    for i, match in enumerate(headers):
        name = match.group().strip().rstrip(':')
        # Collapse whitespace in header name
        name = re.sub(r'\s+', ' ', name).strip()
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((name, body))

    return sections or [("General", text)]


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> list[dict]:
    """
    Section-aware chunking: detect sections first, then split within sections.
    Each chunk is prefixed with its section name for retrieval context.

    Args:
        documents: output of extract_documents()
        chunk_size: max characters per chunk
        chunk_overlap: characters shared between consecutive chunks

    Returns:
        [{"file": "...", "chunk_id": 0, "text": "...", "section": "..."}, ...]
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        sections = _detect_sections(doc["text"])
        for section_name, section_text in sections:
            splits = splitter.split_text(section_text)
            for split in splits:
                prefixed = f"[{section_name}]\n{split.strip()}"
                chunks.append(
                    {
                        "file": doc["file"],
                        "chunk_id": len(chunks),
                        "text": prefixed,
                        "section": section_name,
                    }
                )
    return chunks

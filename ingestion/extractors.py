"""
Text extraction from PDF and DOCX files.
Primary: PyMuPDF (direct text extraction, fast for digital PDFs).
Fallback: Tesseract OCR via pdf2image (for scanned/image-only pages).
"""

from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


def _ocr_page(pdf_path: str, page_number: int) -> str:
    """OCR a single page using PyMuPDF pixmap + pytesseract (fallback for scanned pages)."""
    try:
        import pytesseract
        from PIL import Image
        import io
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        doc.close()
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def extract_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages_text = []
    for page in doc:
        text = page.get_text().strip()
        if not text:
            text = _ocr_page(path, page.number + 1)
        pages_text.append(text)
    doc.close()
    return "\n\n".join(t for t in pages_text if t)


def extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_documents(paths: list[str]) -> list[dict]:
    """
    Extract text from a list of PDF/DOCX file paths.

    Returns:
        [{"file": "retail_project.pdf", "text": "Project overview..."}, ...]
    """
    results = []
    for path in paths:
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            text = extract_pdf(str(p))
        elif suffix in (".docx", ".doc"):
            text = extract_docx(str(p))
        else:
            continue
        if text:
            results.append({"file": p.name, "text": text})
    return results

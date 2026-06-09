FROM python:3.12-slim

WORKDIR /app

# System deps: tesseract for OCR, libgl1/libglib2.0 for PyMuPDF
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python deps — own layer, cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models so container startup is instant
# (models are still needed at runtime for encoding query embeddings)
RUN python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-large-en-v1.5'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Pre-built ChromaDB — generated locally, committed to this repo
# Cached unless you re-run ingestion and push updated chroma_db/
COPY chroma_db/ chroma_db/

# Runtime code
COPY docs/ docs/
COPY ingestion/ ingestion/
COPY rag/ rag/
COPY backend/ backend/
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Dummy SECRET_KEY only for collectstatic; overridden at runtime by HF Spaces secret
ENV SECRET_KEY=build-time-placeholder
RUN cd backend && python manage.py collectstatic --noinput

ENV DOCS_DIR=/app/docs
ENV CHROMA_DB_PATH=/app/chroma_db

EXPOSE 8000

CMD ["/entrypoint.sh"]

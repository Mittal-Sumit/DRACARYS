# Dracarys — AI Pre-Sales Proposal Assistant

Dracarys is an AI assistant built for pre-sales teams. It ingests past proposal documents, stores them as searchable embeddings, and uses an LLM to generate context-aware responses grounded in your company's real project history — so your team stops digging through folders and starts pitching faster.

---

## The Problem It Solves

Pre-sales engineers spend hours hunting through old proposals to find relevant case studies, tech stacks, and pricing benchmarks before pitching a new client. Dracarys puts that knowledge into a semantic search engine backed by an LLM, so the answer to "what did we do for retail clients?" is a query away.

---

## How It Works

```
docs/ (PDFs, DOCX)
      │
      ▼
 extractors.py  ──► text per document
      │
      ▼
  chunker.py    ──► overlapping text chunks
      │
      ▼
 embeddings.py  ──► vectors (all-MiniLM-L6-v2)
      │
      ▼
  ChromaDB      ──► persistent vector store
      │
      ▼
  retrieve()    ──► top-k relevant chunks
      │
      ▼
  Groq LLM      ──► generated proposal response
      │
      ▼
Django REST API ──► frontend / integrations
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Django 6 + Django REST Framework |
| Frontend | React 19 + Vite |
| OCR (scanned docs) | Tesseract + PyMuPDF |
| LLM | Groq |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| Vector DB | ChromaDB |
| Chunking | LangChain Text Splitters |
| Agent orchestration | CrewAI *(upcoming)* |

---

## Project Structure

```
Dracarys/
├── backend/                  # Django project
│   ├── backend/              # Django settings, URLs, WSGI
│   ├── proposal_ai/          # Main app (models, views, serializers)
│   ├── manage.py
│   └── requirements.txt      # Django-only deps (pinned)
│
├── ingestion/                # Document ingestion pipeline
│   ├── extractors.py         # PDF + DOCX → raw text
│   ├── chunker.py            # Text → overlapping chunks
│   ├── embeddings.py         # Chunks → vectors (all-MiniLM-L6-v2)
│   └── ingest.py             # Orchestrates pipeline + exposes retrieve()
│
├── rag/                      # RAG layer (in progress)
│   ├── retriever.py          # Query ChromaDB
│   ├── llm.py                # Groq client
│   ├── prompts.py            # Prompt templates
│   └── generator.py          # Full answer generation
│
├── docs/                     # Drop your proposal PDFs/DOCXs here
├── chroma_db/                # Persisted vector store (auto-created)
├── processed_data/           # Intermediate outputs
├── frontend/                 # React + Vite frontend
├── .env                      # Secrets (never committed)
└── requirements.txt          # All dependencies
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- *(Optional)* [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — only needed for scanned/image PDFs. Most digital proposal PDFs do not need it.

---

## Setup

### 1. Clone the repo

```bash
git clone <repository-url>
cd Dracarys
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install all dependencies

```bash
pip install -r requirements.txt
```

> Note: `sentence-transformers` pulls in PyTorch (~123 MB). First install takes a few minutes.

### 4. Create your `.env` file

```bash
# .env (root directory)
DEBUG=True
SECRET_KEY=your-django-secret-key

GROQ_API_KEY=your-groq-api-key
```

### 5. Set up the Django database

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser   # optional, for admin panel
cd ..
```

### 6. Add your proposal documents

Drop PDF or DOCX files into the `docs/` folder.

```
docs/
├── retail_analytics_proposal.pdf
├── nestle_data_warehouse.pdf
└── any_other_proposal.docx
```

### 7. Run the ingestion pipeline

```bash
python -m ingestion.ingest
```

This extracts text, chunks it, generates embeddings, and stores everything in ChromaDB. Run it again whenever you add new documents.

---

## Testing Retrieval (Milestone 1)

Once ingestion is complete, test semantic search from a Python shell:

```python
from ingestion.ingest import retrieve

results = retrieve("retail analytics")
for r in results:
    print(r["file"], r["score"])
    print(r["text"][:200])
    print()
```

Expected output: top 5 chunks from your past proposals most relevant to the query, with a similarity score between 0 and 1.

---

## Running the Backend

```bash
cd backend
python manage.py runserver
```

API base: `http://localhost:8000/api/`  
Admin panel: `http://localhost:8000/admin/`

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173/`

---

## Roadmap

- [x] Project scaffold (Django + React + ChromaDB)
- [x] PDF + DOCX text extraction
- [x] LangChain chunking
- [x] Embedding generation (all-MiniLM-L6-v2)
- [x] ChromaDB storage + semantic retrieval
- [ ] Groq LLM integration
- [ ] RAG response generation
- [ ] CrewAI agent orchestration
- [ ] Django REST API endpoints for chat
- [ ] Frontend chat UI

---

## Contributing

1. Branch off `main` — use `yourname/feature-name` convention
2. Make your changes
3. Test ingestion and retrieval still work
4. Open a pull request against `main`

---

## License

[Add your license here]

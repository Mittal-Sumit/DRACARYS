---
title: Dracarys
emoji: 🔥
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
---

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
 extractors.py  ──► text per document (PyMuPDF + OCR fallback)
      │
      ▼
  chunker.py    ──► overlapping text chunks (1000 chars, 150 overlap)
      │
      ▼
 embeddings.py  ──► vectors (bge-large-en-v1.5, 1024-dim)
      │
      ▼
  ChromaDB      ──► persistent vector store (cosine similarity)
      │
      ▼
  retriever.py  ──► hybrid search: vector + BM25 → RRF → cross-encoder rerank
      │
      ▼
  Groq LLM      ──► structured JSON proposal (4 sections + sources)
      │
      ▼
Django REST API ──► React chat UI
```

---

## Tech Stack

### Backend

| Component | Technology |
|---|---|
| API server | Django 6 + Django REST Framework |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Embeddings | `BAAI/bge-large-en-v1.5` via sentence-transformers (1024-dim) |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Hybrid search | BM25 (rank-bm25) + vector, merged via Reciprocal Rank Fusion |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| PDF extraction | PyMuPDF (fitz), pytesseract OCR fallback for scanned pages |
| DOCX extraction | python-docx |
| CORS | django-cors-headers |

### Frontend

| Component | Technology |
|---|---|
| Framework | React 19 + Vite |
| Animations | Motion (Framer Motion v12, `motion/react`) |
| Icons | lucide-react |
| Fonts | Quicksand (headings), Nunito (body) — Google Fonts |

---

## Project Structure

```
Dracarys/
├── backend/                  # Django project
│   ├── backend/              # settings, URLs, WSGI
│   └── proposal_ai/          # views, serializers, services
│
├── ingestion/                # Document ingestion pipeline
│   ├── extractors.py         # PDF + DOCX → raw text
│   ├── chunker.py            # Text → overlapping chunks
│   ├── embeddings.py         # Chunks → vectors (bge-large-en-v1.5)
│   ├── doc_metadata.py       # Per-document metadata (client, industry, etc.)
│   └── ingest.py             # Orchestrates full pipeline
│
├── rag/                      # RAG layer
│   ├── retriever.py          # Hybrid search + reranker
│   ├── llm.py                # Groq client (JSON mode)
│   ├── prompts.py            # System prompt + user message builder
│   └── generator.py          # End-to-end generation
│
├── frontend/                 # React + Vite chat UI
│   └── src/
│       ├── pages/Home.jsx        # Chat page (messages, state, scroll)
│       ├── components/
│       │   ├── Sidebar.jsx       # Animated blob avatar + nav + stats
│       │   ├── ChatBox.jsx       # Auto-resize textarea, Enter-to-send
│       │   ├── ProposalPreview.jsx # Staggered proposal sections with icons
│       │   └── Loader.jsx        # Typing dots animation
│       ├── api/api.js            # Axios client → Django backend
│       └── index.css             # CSS variables, fonts
│
├── docs/                     # Drop your proposal PDFs/DOCXs here
├── chroma_db/                # Persisted vector store (auto-created, gitignored)
├── .env                      # Secrets (never committed)
└── requirements.txt          # All Python dependencies
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- *(Optional)* [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — only needed for scanned/image PDFs. Digital PDFs do not require it.

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

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

> Note: `sentence-transformers` downloads PyTorch (~500 MB). First install takes several minutes. The `bge-large-en-v1.5` model (~1.3 GB) is downloaded on first use.

### 4. Create your `.env` file

```
# .env — place in the root Dracarys/ directory
DEBUG=True
SECRET_KEY=your-django-secret-key

GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile

ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### 5. Set up the Django database

```bash
cd backend
python manage.py migrate
cd ..
```

### 6. Add your proposal documents

Drop PDF or DOCX files into the `docs/` folder:

```
docs/
├── retail_analytics_proposal.pdf
├── nestle_data_warehouse.pdf
└── any_other_proposal.docx
```

Then register metadata for each document in `ingestion/doc_metadata.py` — this gives the LLM readable names and context (client, industry, services used).

### 7. Run the ingestion pipeline

```bash
python -m ingestion.ingest
```

This extracts text, chunks it, generates embeddings with `bge-large-en-v1.5`, and stores everything in ChromaDB. Re-run whenever you add new documents.

> If you switch embedding models, wipe `chroma_db/` first:
> ```powershell
> Remove-Item -Recurse -Force chroma_db
> python -m ingestion.ingest
> ```

---

## Running the App

### Backend

```bash
cd backend
python manage.py runserver
```

API runs at `http://localhost:8000/api/`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI runs at `http://localhost:5173/`

The Vite dev server proxies `/api/*` requests to `http://localhost:8000` — both servers must be running.

---

## API

### `POST /api/generate-proposal/`

**Request:**
```json
{ "query": "We need a proposal for a retail client migrating to AWS" }
```

**Response:**
```json
{
  "executive_summary": "...",
  "proposed_solution": "...",
  "relevant_experience": "...",
  "why_us": "...",
  "sources": ["Nestle Data Warehouse", "Retail Analytics Platform"]
}
```

---

## UI Overview

The frontend is a chat-style interface:

- **Sidebar** — animated morphing blob avatar, navigation (Chat / Archive / Settings), pitch search, stats card
- **Chat area** — message bubbles (user right/orange, assistant left/teal), animated entry
- **Proposal preview** — proposal sections with icons rendered inline in the chat, staggered fade-in animation
- **Input dock** — floating textarea with auto-resize, Enter to send / Shift+Enter for newline
- **Loader** — animated typing dots while the backend is generating

---

## Roadmap

- [x] PDF + DOCX text extraction
- [x] LangChain chunking
- [x] Embedding generation (`bge-large-en-v1.5`)
- [x] ChromaDB persistent storage + semantic retrieval
- [x] Hybrid search (vector + BM25 + RRF)
- [x] Cross-encoder reranker
- [x] Document metadata + source attribution
- [x] Groq LLM integration (JSON mode)
- [x] Django REST API
- [x] React chat UI with animations
- [ ] Persistent chat history
- [ ] Multi-session support
- [ ] File upload from UI
- [ ] CrewAI agent orchestration

---

## Contributing

1. Branch off `main` — use `yourname/feature-name` convention
2. Make your changes
3. Test ingestion and retrieval still work (`python -m ingestion.ingest`)
4. Open a pull request against `main`

---

## License

[Add your license here]

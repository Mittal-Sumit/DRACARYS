# Dracarys — Full Knowledge Transfer

**Project:** AI-powered pre-sales assistant for Ganit Business Solutions  
**Stack:** Django 6 · React 19 · CrewAI · ChromaDB · Gemini  
**Purpose:** Helps sales/pre-sales engineers instantly generate grounded pitches and answer capability questions using Ganit's past project work.

---

## Table of Contents

1. [What Does Dracarys Do?](#1-what-does-dracarys-do)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Full Request Flow — End to End](#3-full-request-flow--end-to-end)
4. [RAG Pipeline — How We Find Relevant Content](#4-rag-pipeline--how-we-find-relevant-content)
5. [CrewAI 3-Agent Pipeline](#5-crewai-3-agent-pipeline)
6. [Backend — Django API](#6-backend--django-api)
7. [Frontend — React App](#7-frontend--react-app)
8. [Authentication System](#8-authentication-system)
9. [Document Management](#9-document-management)
10. [LLM Configuration — Gemini](#10-llm-configuration--gemini)
11. [Tone Modes](#11-tone-modes)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Running Locally](#13-running-locally)
14. [Running via Docker](#14-running-via-docker)
15. [Key Design Decisions](#15-key-design-decisions)
16. [Known Limitations](#16-known-limitations)

---

## 1. What Does Dracarys Do?

Dracarys is a **sales intelligence assistant**. A sales person types a question or pitch request, and Dracarys:

- Searches a **knowledge base** of Ganit's past case studies (PDFs)
- Retrieves the most relevant content using hybrid search + AI reranking
- Runs a **3-agent AI pipeline** (Planner → Researcher → Writer) to generate a structured, grounded response
- Returns a formatted answer with **source citations** linking back to the original documents
- For pitches, also returns a hidden **"How to Win"** section with sales tactics

**Example queries:**
- *"What experience do we have in pharma data engineering?"*
- *"Proposal for a data strategy engagement for a mid-size FMCG company"*
- *"What cloud platforms have we worked on?"*

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     USER (Browser)                       │
│              React 19 + Vite (Port 3000)                 │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (Axios, JWT)
┌──────────────────────▼──────────────────────────────────┐
│                  Django 6 + DRF (Port 8000)              │
│   ┌─────────────────────────────────────────────────┐   │
│   │             proposal_ai/views.py                 │   │
│   │          GenerateProposalView (AllowAny)         │   │
│   └──────────────────────┬──────────────────────────┘   │
│                           │                              │
│   ┌───────────────────────▼──────────────────────────┐  │
│   │             proposal_ai/services.py               │  │
│   │          generate_proposal() orchestrator         │  │
│   └──────────────────────┬───────────────────────────┘  │
└──────────────────────────┼──────────────────────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │         rag/crew.py                 │
         │    CrewAI 3-Agent Pipeline          │
         │  Planner → Researcher → Writer      │
         └──────┬──────────────┬──────────────┘
                │              │
    ┌───────────▼───┐    ┌─────▼──────────────┐
    │ rag/retriever │    │  Gemini API         │
    │  Hybrid RAG   │    │  (gemini-2.5-flash  │
    │  + Reranker   │    │   -lite via litellm)│
    └───────┬───────┘    └─────────────────────┘
            │
    ┌───────▼──────────────────────┐
    │         ChromaDB             │
    │   (local persistent store)   │
    │   BAAI/bge-large-en-v1.5     │
    │   1024-dim cosine vectors    │
    └──────────────────────────────┘
```

---

## 3. Full Request Flow — End to End

Here is exactly what happens when a user sends a message:

```
User types: "Proposal for pharma data platform"
           │
           ▼
[Frontend: Home.jsx]
  • isConversational()? — No (not a greeting/smalltalk)
  • Calls api.generateProposal(query, useWebSearch, conversationId, tone)
           │
           ▼
[Backend: POST /api/generate-proposal/]
  • GenerateProposalView receives request
  • Validates: query, use_web_search, conversation_id, tone
  • Calls services.generate_proposal()
           │
           ▼
[services.py: generate_proposal()]
  • USE_CREW_AI=true → calls rag.crew.run_crew()
           │
           ▼
[rag/crew.py: _run_crew_once()]
  │
  ├─── STEP 1: Query Planner Agent
  │      • LLM generates 5–6 search queries for a pitch
  │        e.g. "pharma data engineering case study"
  │             "regulatory compliance data platform"
  │             "SAP Salesforce integration pharma"
  │             "Ganit pharma experience credentials"
  │
  ├─── STEP 2: Parallel KB + Web Fetch (S3 optimisation)
  │      • All queries hit ChromaDB simultaneously (ThreadPoolExecutor)
  │      • Each query runs: vector search → BM25 → RRF → rerank
  │      • Web search (Tavily) runs in parallel if enabled
  │      • Results collected into a structured text block
  │
  ├─── STEP 3: Research Analyst Agent
  │      • Given all pre-fetched KB results as text (no live tool calls)
  │      • Synthesises into a "Research Brief" — client names, metrics, tech
  │      • If web search on: produces two separate sections (KB Brief / Web Brief)
  │
  └─── STEP 4: Proposal Writer Agent
         • Given only the Research Brief (never raw chunks)
         • Writes structured JSON: sections + sources + win_strategy
         • Applies tone-specific section template (6 or 7 sections for pitch)
         • Enforces Number Citation Rule (no invented metrics)
           │
           ▼
[services.py]
  • _build_sources(): converts {name, file} → {name, url} for frontend
  • Returns: {sections, sources, web_sources, win_strategy, conversation_id}
           │
           ▼
[Frontend: ProposalPreview.jsx]
  • Renders sections as react-markdown
  • Shows KB source pills ("From our work") + web source pills ("Web")
  • Shows "How to Win" panel (win_strategy) if present
```

**Typical response time:** ~12–17 seconds for a pitch, ~8–10 seconds for a Q&A.

---

## 4. RAG Pipeline — How We Find Relevant Content

The retriever (`rag/retriever.py`) uses a 4-step hybrid pipeline:

### Step 1: Vector Search
- Query is embedded using `BAAI/bge-large-en-v1.5` (1024-dim)
- ChromaDB finds the top N most semantically similar chunks
- Good at: paraphrased questions, conceptual similarity

### Step 2: BM25 Keyword Search
- Classic keyword matching (TF-IDF variant)
- Same chunks are scored by exact word match
- Good at: client names, technology names, acronyms (e.g. "SAP", "LIMS", "Cipla")

### Step 3: RRF (Reciprocal Rank Fusion)
- Combines both ranked lists into one merged ranking
- A chunk ranked #2 in vector AND #3 in BM25 scores better than one ranked #1 in only one list
- Formula: `score = 1/(60 + rank_vector) + 1/(60 + rank_bm25)`

### Step 4: Cross-Encoder Reranking
- Top 20 candidates go through `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Unlike embeddings (which encode query and chunk separately), cross-encoder reads BOTH together — far more accurate
- Outputs a relevance score (-10 to +10 logit scale)
- Chunks below -2.0 are dropped as irrelevant

### BM25 Cache (Performance)
- BM25 index is rebuilt only when `collection.count()` changes
- Eliminates repeated full-collection loads during the 5–6 parallel queries per pitch
- Saves ~2 seconds per request

### Parameters
| Scenario | n_results | max_per_file | text_limit |
|---|---|---|---|
| Pitch/Proposal | 6 | 3 | 600 chars |
| Q&A | 10 | 3 | 1000 chars |

`max_per_file=3` ensures no single document dominates the results.

---

## 5. CrewAI 3-Agent Pipeline

Three agents run in sequence. Each has a specific job and sees only what it needs.

### Why 3 agents instead of 1?

| Single-shot RAG | 3-Agent Pipeline |
|---|---|
| LLM writes directly from raw chunks | LLM writes from a synthesised brief |
| No query expansion — misses relevant content | Planner generates 5–6 diverse queries |
| LLM distracted by retrieval noise | Writer sees clean, curated brief |
| Source list is inferred (hallucination risk) | Sources tracked from actual tool calls |

---

### Agent 1: Query Planner (`Sales Intelligence Strategist`)

**Temperature:** 0.3 (deterministic)  
**Job:** Break the user's question into 3–4 targeted search queries (or 5–6 for pitches).

**For a pitch, it generates queries covering:**
1. The specific industry (pharma, FMCG, banking...)
2. The technical capability requested (data warehouse, ML, BI...)
3. Specific source systems named (SAP, Salesforce, LIMS, MES...)
4. Relevant case studies and outcomes
5. Company credentials and differentiators

**Output:** `{"queries": ["query 1", "query 2", ...]}`

---

### Agent 2: Research Analyst

**Temperature:** 0.3  
**Job:** Synthesise the pre-fetched KB results (and web results if enabled) into a clean Research Brief.

**This agent has NO live tool calls** — all KB and web results are pre-fetched in parallel (S3 optimisation) and injected as text into the task description. This eliminates a class of errors where the LLM would emit tool invocation syntax as literal text.

**Output format (web search on):**
```
=== INTERNAL KB BRIEF ===
Facts extracted from our case studies only.
Client names, technologies, measurable outcomes.

=== WEB RESEARCH BRIEF ===
Market context from web only.
Industry benchmarks, client background, trends.
```

The strict two-section separation is critical — blending KB and web causes the Writer to mix first-person ("we did X") with attributed claims ("According to X"), degrading output quality.

---

### Agent 3: Proposal Writer (`Sales Intelligence Assistant`)

**Temperature:** 0.45  
**Job:** Write the final structured JSON response using ONLY the Research Brief.

**Output schema (pitch/proposal):**
```json
{
  "sections": [
    {"heading": "Problem Understanding", "content": "markdown..."},
    {"heading": "Recommended Approach", "content": "markdown..."},
    ...
  ],
  "sources": ["Cipla BI & Data Engineering", "Sun Pharma GCP Data Engineering"],
  "win_strategy": {
    "pitch_strategy": "Open with Cipla — closest industry match...",
    "value_propositions": ["string", "string", "string"],
    "objections": [
      {"objection": "You don't have pharma-specific IP", "response": "..."},
      ...
    ]
  }
}
```

**Key rules enforced on the Writer:**
1. **Number Citation Rule (Rule 1):** Every metric must exist verbatim in the Research Brief. If not → hedged language ("potential benefits may include...", "similar engagements have demonstrated..."). This is the primary hallucination guard.
2. **Source attribution:** KB → first-person ("We delivered X"). Web → attributed ("According to [Source]"). Never blended in the same sentence.
3. **No filler words:** "leveraging", "robust", "seamlessly", "cutting-edge" are banned.
4. **Depth rule:** Every relevant fact in the brief must appear in the response. No truncation.

---

### S3: Parallel KB Fetch (Performance Optimisation)

Instead of the Researcher calling the KB tool sequentially query-by-query, all KB searches run simultaneously using `ThreadPoolExecutor`:

```
Planner generates: [Q1, Q2, Q3, Q4, Q5]
                           │
                    ┌──────▼──────┐
         ┌──────────┤ThreadPool   ├──────────┐
         │          └─────────────┘          │
    Q1→retrieve  Q2→retrieve  Q3→retrieve  Q4→retrieve  Q5→retrieve
         │               │            │           │           │
         └───────────────┴────────────┴───────────┴───────────┘
                                    │
                         Combined KB brief injected
                         into Researcher's task description
```

This saves ~4 seconds on pitch requests.

---

## 6. Backend — Django API

### Project Structure

```
backend/
├── backend/
│   ├── settings.py    — DB, CORS, JWT, DRF config
│   ├── urls.py        — CRITICAL: api/auth/ MUST come before api/
│   └── wsgi.py
├── accounts/          — signup, login, token refresh (AllowAny, @ganitinc.com domain)
└── proposal_ai/
    ├── models.py      — Conversation + ChatMessage (stores history)
    ├── serializers.py — Request validation
    ├── views.py       — GenerateProposalView + Conversation CRUD
    ├── services.py    — RAG orchestrator
    └── urls.py        — All proposal_ai routes
```

### API Endpoints

| Method | URL | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/signup/` | None | Register (@ganitinc.com only) |
| POST | `/api/auth/login/` | None | Get JWT tokens |
| POST | `/api/auth/token/refresh/` | None | Refresh access token |
| POST | `/api/generate-proposal/` | None (AllowAny) | Main AI endpoint |
| GET | `/api/conversations/` | JWT | List user's conversations |
| GET | `/api/conversations/<id>/` | JWT | Load a conversation |
| DELETE | `/api/conversations/<id>/` | JWT | Delete a conversation |
| GET | `/api/docs/<filename>` | None | Serve source PDF (local dev) |

### Request/Response Format

**Request to `/api/generate-proposal/`:**
```json
{
  "query": "Proposal for pharma data platform",
  "use_web_search": false,
  "conversation_id": null,
  "tone": "pitch"
}
```

**Response:**
```json
{
  "sections": [{"heading": "Problem Understanding", "content": "..."}],
  "sources": [{"name": "Cipla BI & Data Engineering", "url": "/api/docs/Cipla_BI...pdf", "similarity_score": 87.3}],
  "web_sources": [],
  "win_strategy": {"pitch_strategy": "...", "value_propositions": [...], "objections": [...]},
  "conversation_id": 42,
  "conversation_title": "Proposal for pharma data platform"
}
```

### Error Codes

| Status | Meaning |
|---|---|
| 400 | Bad request (missing query, invalid tone) |
| 404 | Conversation not found or not owned by user |
| 503 | Gemini quota exhausted / ChromaDB empty |
| 500 | Unexpected pipeline error |

---

## 7. Frontend — React App

### Key Files

```
frontend/src/
├── api/api.js               — Axios client with JWT interceptors + retry
├── context/AuthContext.jsx  — Auth state (token in memory, refresh in localStorage)
├── pages/
│   ├── Home.jsx             — Main chat UI
│   ├── Login.jsx
│   └── Signup.jsx
├── components/
│   ├── Sidebar.jsx          — Conversation list
│   ├── ChatBox.jsx          — Input bar, tone selector, web toggle
│   └── ProposalPreview.jsx  — Renders sections, source pills, win_strategy
└── App.jsx                  — Router + AuthProvider
```

### How the Chat UI Works

1. User types in `ChatBox.jsx` and presses Enter (or clicks Send)
2. `isConversational()` check — if it's a greeting like "hello" or "how are you", it replies locally without calling the API (saves tokens, avoids latency)
3. Otherwise: calls `api.generateProposal()` → shows loading state → renders response
4. `ProposalPreview.jsx` renders:
   - Each section as markdown (react-markdown + remark-gfm)
   - KB source pills: green, labeled "From our work", link to the PDF
   - Web source pills: blue, labeled "Web", link to the external URL
   - "How to Win" collapsible panel (win_strategy — not shown to clients)

### Tone Selector

Three modes available in the UI:

| Mode | Label | Audience |
|---|---|---|
| `pitch` | Balanced | Default for sales meetings |
| `pitch_executive` | Executive | C-suite, business language only |
| `pitch_technical` | Technical | CTOs, architects, deep technical detail |
| `proposal` | Proposal | Formal written document, 9 sections |
| `ask` | Q&A | Direct question answering |

---

## 8. Authentication System

### Design

- **Access token:** 15-minute JWT. Stored in **memory only** (never localStorage or cookies). This means XSS cannot steal it.
- **Refresh token:** 7-day JWT. Stored in `localStorage` under key `dracarys_session`.
- **Bootstrap flow:** On every page load → read localStorage → call `/api/auth/token/refresh/` → restore session. If this fails → user is a guest (no redirect to login).
- **Silent refresh:** When any request gets a 401 → interceptor refreshes token → retries the original request. `_refreshPromise` deduplication prevents multiple concurrent refreshes from racing each other.
- **Signup restriction:** Only `@ganitinc.com` email addresses are accepted.
- **Guest access:** The main AI endpoint is `AllowAny` — guests can use the tool but their history is not saved.

---

## 9. Document Management

### Ingested Documents (Knowledge Base)

| File | Display Name | Industry |
|---|---|---|
| CocaCola_DemandForecasting_CaseStudy.pdf | Coca-Cola Demand Forecasting | FMCG |
| Nestle_DataWarehouse_CaseStudy.pdf | Nestle Global Data Warehouse | FMCG |
| PG_DataWarehouse_CaseStudy.pdf | P&G Trade Analytics Platform | FMCG |
| Cipla_BI_DataEngineering_CaseStudy.pdf | Cipla BI & Data Engineering | Pharma |
| HSBC_AzureDataPlatform_CaseStudy.pdf | HSBC Azure Data Platform | Banking |
| Jaguar_MicrosoftFabric_CaseStudy.pdf | Jaguar Microsoft Fabric Analytics | Automotive |
| Philips_Healthcare_PredictiveMaintenance_POC.pdf | Philips Healthcare Predictive Maintenance POC | Healthcare |
| Siemens_Healthineers_CaseStudy.pdf | Siemens Healthineers Data Analytics | Healthcare |
| SunPharma_GCP_DE_ReactNode_CaseStudy.pdf | Sun Pharma GCP Data Engineering | Pharma |
| Ganit_Corporate_Profile_RAG_Optimized.pdf | Ganit Corporate Profile | Consulting |

### Ingestion Pipeline

When a document is added:

```
PDF/DOCX file
     │
     ▼
ingestion/extractors.py
  • PyMuPDF for text extraction
  • pytesseract OCR fallback for scanned pages
     │
     ▼
ingestion/chunker.py
  • LangChain RecursiveCharacterTextSplitter
  • Chunk size: 1500 chars, overlap: 200 chars
     │
     ▼
ingestion/embeddings.py
  • BAAI/bge-large-en-v1.5 model
  • 1024-dimensional vectors, normalized
     │
     ▼
ChromaDB (local persistent)
  • chroma_db/chroma.sqlite3 — metadata index
  • chroma_db/<uuid>/ — HNSW binary vector files
```

### Adding a New Document

```powershell
# 1. Drop the PDF into docs/
# 2. Register it in ingestion/doc_metadata.py (_DOC_METADATA dict)
# 3. Wipe and rebuild ChromaDB
Remove-Item chroma_db -Recurse -Force
python -m ingestion.ingest
# 4. Commit and push
git add docs/<file>.pdf ingestion/doc_metadata.py chroma_db/
git commit -m "docs: add <document name>"
```

---

## 10. LLM Configuration — Gemini

### Current Setup

- **Model:** `gemini/gemini-2.5-flash-lite` (via litellm + CrewAI's native Gemini provider)
- **Planner & Researcher temperature:** 0.3 (factual, deterministic)
- **Writer temperature:** 0.45 (slightly creative for writing quality)
- **Max tokens:** 16,384 per call

### Why Gemini (not Groq)?

Groq has a strict **12,000 token per request** limit. A pitch with 5–6 queries × 6 chunks × 1000 chars ≈ 11–12k tokens just for the context — leaving almost no room for the LLM output. This caused constant 413 (token limit) errors.

Gemini has a **1M context window** — no per-request limit. The switch eliminated all token limit errors.

### Key Manager (Rate Limit Handling)

`rag/gemini_keys.py` manages multiple API keys:

- Keys read from `.env`: `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, etc.
- On a 429 (rate limit) error → automatically rotates to the next key
- If all keys exhausted → raises `GeminiQuotaExhaustedError` → HTTP 503

### Required `.env` Variables

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini/gemini-2.5-flash-lite
USE_CREW_AI=true
CREWAI_TELEMETRY_ENABLED=false   # prevents quota burn from pre-pipeline telemetry calls
OTEL_SDK_DISABLED=true           # same reason
```

Free tier limits for `gemini-2.5-flash-lite`: ~10 RPM, better daily limits than 2.5-flash.

---

## 11. Tone Modes

Dracarys supports 5 distinct response modes, each producing completely different section structures (not just vocabulary changes):

### `pitch` (default) — 6 sections
1. Problem Understanding
2. Recommended Approach
3. Relevant Experience
4. Expected Business Outcomes
5. Why Ganit
6. Key Discussion Points

### `pitch_executive` — 7 sections
1. Business Context
2. The Cost of Inaction
3. Expected Business Outcomes
4. Relevant Experience
5. Why Ganit
6. Key Discussion Points
7. Discovery Questions

*Rule: Zero technical terminology. Every element must be business language.*

### `pitch_technical` — 6 sections
1. Technical Context
2. Architecture Overview
3. Technical Approach
4. Relevant Technical Experience
5. Implementation Approach
6. Technical Discussion Points

*Rule: Name every specific service, pattern, and trade-off.*

### `proposal` — 9 sections (formal written document)
Executive Summary · Business Challenge · Relevant Experience · Solution Approach · Technical Architecture · Delivery Plan · Risks & Mitigation · Benefits & Expected Outcomes · Next Steps

### `ask` — flexible (1–5 sections)
Direct question answering — section count calibrated to question complexity.

---

## 12. Deployment Architecture

### Production Setup

| Layer | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploys on push to `sumit/ai/feature` |
| Backend | HuggingFace Spaces (Docker) | CPU Basic, 16 GB RAM |
| Database | Supabase PostgreSQL | Session pooler connection |
| Vector DB | ChromaDB | Pre-built locally, committed to HF repo via Git LFS |

### Docker Setup (for local/manager deployment)

```
docker-compose.yml
  ├── backend  (Dockerfile)       → Django + Gunicorn on :8000
  └── frontend (Dockerfile.frontend) → React built + served by nginx on :80
                                        mapped to host port :3000
```

nginx routes:
- `/api/*` → proxied to backend:8000
- Everything else → React SPA (index.html)

### Git Remotes

```
origin → GitHub (github.com/Mittal-Sumit/DRACARYS)
hf     → HuggingFace Space (auto-rebuilds on push)
```

---

## 13. Running Locally

### One-time setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd frontend; npm install; cd ..
cd backend; python manage.py migrate; cd ..
python -m ingestion.ingest   # builds ChromaDB from docs/
```

### Start servers

**Terminal 1 — Backend:**
```powershell
venv\Scripts\activate
cd backend
python manage.py runserver --noreload
```
`--noreload` is required — Python file changes require manual restart.

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm run dev
```

Access at: `http://localhost:5173`

### Environment file (`.env`)

```env
SECRET_KEY=<django-secret>
DEBUG=True
GEMINI_API_KEY=<your-key>
GEMINI_MODEL=gemini/gemini-2.5-flash-lite
GROQ_MODEL=llama-3.3-70b-versatile
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
USE_CREW_AI=true
CREWAI_TELEMETRY_ENABLED=false
OTEL_SDK_DISABLED=true
TAVILY_API_KEY=<optional>
DOCS_DIR=C:\path\to\docs
```

---

## 14. Running via Docker

### Prerequisites
- Docker Desktop installed
- No other services on ports 3000 or 8000

### Steps

```bash
# 1. Extract the zip
# 2. Edit .env — fill in two fields:
#    SECRET_KEY=any-50-char-string
#    GEMINI_API_KEY=your-key-from-aistudio.google.com

# 3. Build and start (first time: ~5–10 min for model downloads)
docker compose up --build

# 4. Open browser
http://localhost:3000
```

### First-time build downloads (~1.5 GB total):
- `BAAI/bge-large-en-v1.5` — ~1.3 GB (embedding model)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` — ~200 MB (reranker model)

These are cached by Docker — subsequent `docker compose up` starts in seconds.

---

## 15. Key Design Decisions

| Decision | Reason |
|---|---|
| 3-agent pipeline instead of single-shot RAG | Planner generates diverse queries → surfaces more content. Researcher pre-synthesises → Writer sees clean signal. Strict role separation produces better quality at each step. |
| Parallel KB fetch (S3) | 5–6 sequential retrieve() calls at ~0.8s each = 4–5s wasted. Running them in ThreadPoolExecutor cuts this to ~1s. |
| Pre-fetched context (no live tool calls in Researcher) | LLMs with large injected context blocks sometimes emit tool invocations as literal text instead of actual function calls. Pre-fetching eliminates this failure mode entirely. |
| KB/web strict separation (two labelled briefs) | Mixed briefs cause the Writer to blend first-person KB facts with attributed web claims in the same sentence, degrading accuracy and citation quality. |
| Output schema first in Writer task description | Gemini anchors on the beginning of a prompt. Schema placed first means the model commits to the JSON structure before processing the instructions. |
| Gemini over Groq | Groq's 12k token limit was hit constantly on pitch requests. Gemini has 1M context — eliminates the entire class of token limit errors. |
| Access token in memory only | Never exposed to XSS attacks via localStorage. Refresh token in localStorage gives persistence across page loads. |
| `_refreshPromise` deduplication | Multiple concurrent API calls all failing with 401 would each try to refresh the token, causing a race condition. One shared promise prevents this. |
| `api/auth/` before `api/` in urlpatterns | Django uses first-match routing. Wrong order sends auth requests into proposal_ai (which has no auth routes), causing 404s. |
| Number Citation Rule as Rule 1 | Highest-priority hallucination guard. Forces hedged language for any metric not found verbatim in the retrieved context. |

---

## 16. Known Limitations

| Issue | Details |
|---|---|
| Pitch quality ceiling | Thin case studies (Cipla, Siemens) have limited content → hallucination risk on those specific clients. Fix: enrich those PDFs. |
| 20 RPD on Gemini free tier | The free `gemini-2.5-flash` tier has 20 requests/day. `gemini-2.5-flash-lite` has better limits. Paid tier removes this entirely. |
| Guest history is ephemeral | Conversations are only saved for logged-in users. Guests lose history on page refresh — by design. |
| Conversational replies not saved | Messages caught by `isConversational()` (greetings, smalltalk) never hit the API and are not persisted. |
| Source links only work locally | `/api/docs/<file>` is served by Django in local dev. In production, DocView returns 404 (docs/ not in Docker image by default). |
| No UI file upload | Adding documents requires CLI access and a code change in `doc_metadata.py`. |
| Web search agent may skip tool | If the LLM decides a tool call isn't needed, it skips it. Workaround: include "search the web for..." explicitly in the query. |

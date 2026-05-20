# Dracarys - AI Proposal Generation System

A RAG (Retrieval-Augmented Generation) based system for intelligent proposal generation using Django backend and LLM integration.

## Project Overview

Dracarys is an AI-powered proposal generation system that combines:
- **Backend API**: Django REST Framework for managing proposals
- **Data Ingestion**: Document chunking and embedding pipeline
- **RAG System**: Retriever-Augmented Generation for context-aware proposals
- **Vector Database**: ChromaDB for semantic search and retrieval

## Project Structure

```
├── backend/                 # Django project
│   ├── proposal_ai/        # Main Django app for proposal management
│   ├── db.sqlite3          # SQLite database
│   ├── manage.py           # Django management script
│   └── requirements.txt     # Python dependencies
├── ingestion/              # Data ingestion pipeline
│   ├── chunker.py          # Document chunking logic
│   ├── embeddings.py       # Embedding generation
│   ├── extractors.py       # Data extraction utilities
│   └── ingest.py           # Main ingestion orchestrator
├── rag/                    # RAG implementation
│   ├── generator.py        # Proposal generation logic
│   ├── llm.py              # LLM interface
│   ├── prompts.py          # Prompt templates
│   └── retriever.py        # Vector store retrieval
├── chroma_db/              # ChromaDB vector store
├── processed_data/         # Processed documents and metadata
└── docs/                   # Documentation
```

## Prerequisites

- Python 3.8 or higher
- pip or conda for package management
- SQLite (included with Python)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Dracarys
```

### 2. Create a Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

## Setup & Configuration

### 1. Create .env File

Create a `.env` file in the root directory with your configuration:

```
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///db.sqlite3

# LLM Configuration
LLM_API_KEY=your-llm-api-key
LLM_MODEL=your-model-name
```

**Note:** The `.env` file is listed in `.gitignore` - each developer must create their own with appropriate credentials.

### 2. Django Database Setup

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser  # Create admin user
cd ..
```

### 3. Initialize Vector Database

```bash
python ingestion/ingest.py
```

This will:
- Process documents in `processed_data/`
- Generate embeddings
- Populate ChromaDB with vectors

## Running the Project

### Start the Django Development Server

```bash
cd backend
python manage.py runserver
```

The API will be available at `http://localhost:8000/`
Admin panel at `http://localhost:8000/admin/`

### Run Data Ingestion Pipeline

```bash
python ingestion/ingest.py
```

### Generate Proposals

```bash
from rag.generator import ProposalGenerator
generator = ProposalGenerator()
proposal = generator.generate("Your proposal context here")
```

## API Endpoints

### Proposals
- `GET /api/proposals/` - List all proposals
- `POST /api/proposals/` - Create new proposal
- `GET /api/proposals/{id}/` - Retrieve proposal details
- `PUT /api/proposals/{id}/` - Update proposal
- `DELETE /api/proposals/{id}/` - Delete proposal

### Admin Panel
- Navigate to `http://localhost:8000/admin/` to manage proposals and data

## Development

### Running Tests

```bash
cd backend
python manage.py test proposal_ai
```

### Code Structure

- **Models** (`proposal_ai/models.py`): Database schema
- **Serializers** (`proposal_ai/serializers.py`): API data validation
- **Views** (`proposal_ai/views.py`): API endpoints
- **Services** (`proposal_ai/services.py`): Business logic

## Troubleshooting

### Database Errors
```bash
cd backend
python manage.py reset_migrations
python manage.py migrate
```

### Missing Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### ChromaDB Issues
Clear and reinitialize the vector database:
```bash
rm -rf chroma_db/
python ingestion/ingest.py
```

## Files to Create Manually

The following file must be manually created by developers (it's in `.gitignore` and not committed to the repository):

- **`.env`** - Environment variables and credentials (Django SECRET_KEY, LLM API keys, etc.)

All other ignored files and folders (`venv/`, `__pycache__/`, `*.pyc`, `build/`, `dist/`, `node_modules/`) are automatically created during installation or runtime. The `chroma_db/` folder is committed to the repository and will be cloned with the project.

## Contributing

1. Create a new branch for features
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

[Add your license here]

## Support

For issues or questions, please open an issue in the repository.

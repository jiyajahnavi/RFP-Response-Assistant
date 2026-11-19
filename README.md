# RFP Response Assistant

An AI-powered enterprise platform designed to streamline the end-to-end lifecycle of Requests for Proposals (RFPs). It enables automated question extraction, intelligent contextual drafting using LLM/Gemini API and historical response repositories, granular role-based review workflows, and exportable client-ready proposal packages.

---

## 1. Multi-Phase Architecture & Status

All 5 roadmap phases outlined in the architecture specification ([documentation.pdf](documentation.pdf)) have been fully implemented, tested, and integrated:

| Phase | Focus & Objectives | Status | Key Deliverables |
|---|---|---|---|
| **Phase 1** | Backend Foundation & Database Setup | **COMPLETED** | FastAPI lifespan DB ping, 6 core SQLAlchemy models, Alembic migrations, CRUD baseline, Swagger UI. |
| **Phase 2** | RFP & Question Management (CRUD & Ingestion) | **COMPLETED** | RFP & Question CRUD, Document Ingestion parser (PDF, DOCX, XLSX), auto-sequence numbering, category classifier, SME assignment. |
| **Phase 3** | AI Generation & Response Library Search | **COMPLETED** | Semantic vector search (Gemini Embeddings), RAG knowledge retrieval, contextual drafting (Gemini 2.5 Flash), confidence scoring, citations, enforced `Draft` status invariant. |
| **Phase 4** | Approval Workflow & Version Control | **COMPLETED** | Response state machine (`Draft` → `In Review` → `Approved` → `Rejected`), immutable audit trail in `ResponseVersion`, Promotion Gate (only `Approved` enter `ResponseLibrary`), reviewer attribution. |
| **Phase 5** | Export, Analytics & Angular Frontend | **COMPLETED** | Angular 18+ SPA (Dashboard, Questionnaire Matrix, Approval Workbench, Knowledge Base Search), formatted exports (`.docx`, `.xlsx`, `.pdf`), progress tracking & SLA metrics. |

---

## 2. Directory Structure

```
RFP Response Assistant/
├── .env                  # Environment configuration (DB, API Keys)
├── .env.example          # Environment template
├── .gitignore            # Exclusion rules for Python, DB, and Angular
├── documentation.pdf     # System Architecture Specification & Roadmap
├── README.md             # Complete project guide
├── backend/
│   ├── alembic.ini       # Alembic configuration
│   ├── pytest.ini        # Pytest configuration
│   ├── requirements.txt  # Dependencies (FastAPI, SQLAlchemy, Gemini, Docx, ReportLab, etc.)
│   ├── alembic/          # Versioned database migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py       # FastAPI application, CORS, lifespan, routes
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic BaseSettings loading .env
│   │   │   ├── database.py   # SQLAlchemy engine, session maker, get_db
│   │   │   ├── exceptions.py # Custom domain exceptions
│   │   │   └── logging.py    # Structured logger
│   │   ├── models/
│   │   │   └── entities.py   # 6 core relational models
│   │   ├── schemas/
│   │   │   └── rfp.py        # Pydantic request/response schemas
│   │   ├── repositories/
│   │   │   └── rfp_repository.py # Repository data access layer
│   │   ├── services/
│   │   │   ├── rfp_service.py      # Core business logic & document ingestion
│   │   │   ├── ai_service.py       # Gemini RAG & Semantic vector search
│   │   │   ├── workflow_service.py # State machine, promotion gate, exports & analytics
│   │   │   └── gemini_service.py   # Google GenAI client
│   │   ├── utils/
│   │   │   ├── classifier.py       # Category classification engine
│   │   │   └── document_parser.py  # PDF, DOCX, XLSX questionnaire extractor
│   │   └── api/v1/
│   │       ├── router.py           # Unified router aggregation
│   │       └── endpoints/
│   │           ├── health.py           # Health check & DB ping
│   │           ├── rfps.py             # RFP CRUD & document upload
│   │           ├── questions.py        # Question CRUD & SME assignment
│   │           ├── responses.py        # AI generation, revisions, approval workflow
│   │           ├── library.py          # Response library & semantic search
│   │           └── export_analytics.py # Word, Excel, PDF export & SLA analytics
│   └── tests/
│       ├── conftest.py             # In-memory SQLite fixtures
│       ├── test_health.py          # Health check tests
│       ├── test_models.py          # Schema & relationship tests
│       ├── test_rfps.py            # RFP listing & retrieval tests
│       ├── test_phase2.py          # Question CRUD, parser, classifier tests
│       └── test_phases_3_4_5.py    # AI drafting, approval states, exports & analytics tests
└── frontend/                       # Angular 18+ Enterprise Single Page App
    ├── angular.json
    ├── package.json
    ├── src/
    │   ├── main.ts
    │   ├── styles.css              # Modern design system & variables
    │   └── app/
    │       ├── app.component.ts    # Global navigation & API connectivity monitor
    │       ├── app.routes.ts       # Application routes
    │       ├── models/rfp.model.ts # Typed domain interfaces
    │       ├── services/api.service.ts # Centralized Angular HTTP service
    │       └── components/
    │           ├── rfp-dashboard/  # RFP portfolio, KPI cards, modal creation
    │           ├── rfp-detail/     # Questionnaire matrix, AI generator, review workbench, exports
    │           └── library-search/ # Semantic search & Knowledge Base explorer
```

---

## 3. Getting Started & Execution Guide

### Backend Setup

1. **Activate Virtual Environment**:
   ```bash
   cd backend
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Update `.env` in the root:
   ```ini
   DATABASE_URL="sqlite:///./rfp_assistant.db" # or MySQL / SQL Server
   GEMINI_API_KEY="your-gemini-api-key"
   GEMINI_MODEL="gemini-2.5-flash"
   GEMINI_EMBEDDING_MODEL="gemini-embedding-001"
   ```

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Run the Automated Test Suite (100% Passing)**:
   ```bash
   pytest -v
   ```

6. **Start Backend Server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Interactive Swagger UI is available at: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

---

### Frontend Setup (Angular 18+)

1. **Navigate to Frontend Directory**:
   ```bash
   cd frontend
   ```

2. **Build the Application**:
   ```bash
   npm run build
   ```

3. **Start the Frontend Development Server**:
   ```bash
   npm start
   ```
   Open your browser at: [http://localhost:4200](http://localhost:4200)

---

## 4. Key API Endpoints

- `GET /api/v1/health` - Database ping & system status.
- `GET /api/v1/rfps` - List RFPs with pagination.
- `POST /api/v1/rfps` - Create new proposal.
- `POST /api/v1/rfps/{rfp_id}/ingest` - Ingest questions from PDF/DOCX/XLSX.
- `POST /api/v1/questions/{id}/generate-draft` - Gemini AI RAG response generation.
- `PUT /api/v1/responses/{id}` - Update response text & create immutable audit version.
- `PATCH /api/v1/responses/{id}/status` - Advance approval workflow (`Draft` → `In Review` → `Approved` → `Rejected`).
- `POST /api/v1/responses/{id}/promote` - Promote approved response to Response Library.
- `GET /api/v1/library/search?q=...` - Semantic vector search across historical responses.
- `GET /api/v1/analytics?rfp_id={id}` - Real-time progress, SLA, and turnaround metrics.
- `GET /api/v1/export/{id}/docx` - Export styled Word proposal document.
- `GET /api/v1/export/{id}/xlsx` - Export formatted Excel questionnaire.
- `GET /api/v1/export/{id}/pdf` - Export client-ready PDF proposal package.

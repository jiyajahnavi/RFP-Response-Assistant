# RFP Response Assistant 

An AI-powered application designed for managing Requests for Proposals (RFPs), extracting questions, generating draft responses, and managing the proposal approval workflow.

---

## 1. Architecture Overview

Phase 1 establishes a scalable, layered backend foundation with strict separation of concerns:

```
RFP Response Assistant/
├── .env                  # Local environment configuration (git-ignored)
├── .env.example          # Environment template with SQL Server & SQLite samples
├── .gitignore            # Git exclusion rules
├── README.md             # Architecture & execution guide
└── backend/
    ├── alembic.ini       # Alembic migration configuration
    ├── pytest.ini        # Pytest discovery configuration
    ├── requirements.txt  # Python package dependencies
    ├── alembic/
    │   ├── env.py        # Dynamic Alembic environment configured with app settings
    │   └── versions/     # Versioned migration scripts (001: 5708561fe160_create_initial_rfp_tables.py)
    ├── app/
    │   ├── main.py       # FastAPI application, CORS, lifespan, and centralized exception handling
    │   ├── core/
    │   │   ├── config.py     # Pydantic BaseSettings loading .env
    │   │   ├── database.py   # SQLAlchemy engine, connection pooling, and get_db session dependency
    │   │   ├── exceptions.py # Custom domain exceptions (EntityNotFoundException, etc.)
    │   │   └── logging.py    # Centralized structured logging setup
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── entities.py   # SQLAlchemy ORM models (6 core entities + relationships + indexes)
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   └── rfp.py        # Pydantic v2 schemas for request/response serialization & validation
    │   ├── repositories/
    │   │   ├── __init__.py
    │   │   └── rfp_repository.py # Data access abstraction for RFPs
    │   ├── services/
    │   │   ├── __init__.py
    │   │   └── rfp_service.py    # Business logic layer
    │   ├── api/
    │   │   └── v1/
    │   │       ├── router.py     # API v1 centralized router
    │   │       └── endpoints/
    │   │           ├── health.py # GET /api/v1/health (DB connectivity verification)
    │   │           └── rfps.py   # GET /api/v1/rfps and GET /api/v1/rfps/{rfp_id}
    │   └── utils/
    └── tests/
        ├── conftest.py       # Isolated in-memory SQLite fixtures & FastAPI TestClient
        ├── test_health.py    # Health check & DB ping test
        ├── test_models.py    # Model constraints, foreign keys, and business rules tests
        └── test_rfps.py      # RFP listing, pagination, retrieval, and 404 tests
```

---

## 2. Prerequisites

- Python 3.10+ (tested and verified on Python 3.14)
- (Optional for SQL Server / Azure SQL): Microsoft ODBC Driver 17 or 18 for SQL Server (`brew install msodbcsql18` on macOS or standard Linux/Windows drivers)

---

## 3. Environment Setup & Dependency Installation

1. Navigate to the project root:
   ```bash
   cd "RFP Response Assistant"
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv backend/venv
   source backend/venv/bin/activate
   ```

3. Install project dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

---

## 4. SQL Database Configuration

The application supports both **SQL Server / Azure SQL** (production target) and **SQLite** (local zero-dependency testing).

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### For SQL Server / Azure SQL:
Configure `DATABASE_URL` in `.env`:
```ini
DATABASE_URL="mssql+pyodbc://<username>:<password>@<server_address>:1433/<database_name>?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=no"
```

### For Local SQLite:
```ini
DATABASE_URL="sqlite:///./rfp_assistant.db"
```

*Note: Database credentials are never hardcoded and are loaded strictly via Pydantic settings from `.env`.*

---

## 5. Database Migrations (Alembic)

Alembic is configured dynamically with `app.core.config.settings` and `app.core.database.Base.metadata`.

1. Run migrations to create or upgrade all database tables:
   ```bash
   cd backend
   alembic upgrade head
   ```

2. To generate future revisions after modifying SQLAlchemy models:
   ```bash
   alembic revision --autogenerate -m "describe_changes"
   ```

---

## 6. Running the FastAPI Application

Start the development server with Uvicorn:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Alternatively, from the project root:
```bash
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

---

## 7. Accessing API Documentation

Once the server is running, explore the interactive documentation:
- **Swagger UI**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **ReDoc**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
- **OpenAPI Schema (JSON)**: [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)

---

## 8. Implemented Endpoints

- `GET /api/v1/health`: Checks API and validates live database connectivity (`SELECT 1`).
- `GET /api/v1/rfps`: Retrieves paginated list of RFPs (`skip`, `limit` query parameters).
- `GET /api/v1/rfps/{rfp_id}`: Retrieves single RFP with associated `questions`. Returns clean 404 JSON response if not found.

---

## 9. Running Tests

The test suite runs against an isolated in-memory database using `pytest`:

```bash
cd backend
pytest -v
```

All 5 automated tests cover:
- Health check and DB ping (`test_health.py`)
- Entity relationships, cascade deletes, draft constraints, and versioning (`test_models.py`)
- RFP retrieval, pagination, and 404 error formatting (`test_rfps.py`)

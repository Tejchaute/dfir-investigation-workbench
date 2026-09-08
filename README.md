# DFIR Investigation Workbench

DFIR Investigation Workbench is a planned local-first platform for preserving, analyzing, correlating,
and reporting Windows forensic evidence. The repository is currently at **Phase 2: Case
Management**. It contains the persistent core domain and a Case lifecycle API. Evidence workflows
and forensic capabilities remain planned and are not implemented.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, psycopg, pytest
- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts
- Database: PostgreSQL 18
- Deployment shape: Docker Compose modular monolith (frontend, backend, PostgreSQL)

## Local configuration

Copy `.env.example` to `.env` at the repository root, then replace the development password. `DATABASE_URL` is required;
the backend deliberately fails at startup if it is absent. The example storage roots point to
`data/cases` for evidence and `data/exports` for generated reports. Keep these paths separate.

The evidence mount is read-only inside Docker. Never place real evidence, secrets, or generated
reports under version control.

## Backend

Python 3.12 and [uv](https://docs.astral.sh/uv/) are recommended:

```powershell
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The health endpoint is `GET http://localhost:8000/health`.

### Case API

```text
POST  /api/cases
GET   /api/cases?limit=25&offset=0
GET   /api/cases/{case_id}
PATCH /api/cases/{case_id}
POST  /api/cases/{case_id}/close
POST  /api/cases/{case_id}/archive
```

Case creation accepts `name`, `description`, and `investigator`. UUID, case number, timestamps, and
initial `OPEN` status are controlled by the server. Updates accept only those three metadata fields.
The lifecycle is strictly `OPEN → CLOSED → ARCHIVED`; invalid transitions return HTTP 409.

Case numbers use `CASE-YYYY-NNNN`. PostgreSQL sequence `case_number_seq` allocates the numeric
portion safely under concurrent requests. Sequence values are not rolled back, so gaps are expected
after failed transactions. Lifecycle mutations and their audit events commit atomically. Until
authentication exists, audit records use the explicit non-user actor `LOCAL_APPLICATION`.

Run checks:

```powershell
cd backend
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
npm run lint
npm run typecheck
npm run build
```

The development UI runs at `http://localhost:5173`. Override its single API origin with
`VITE_API_BASE_URL` before building.

## PostgreSQL and Docker Compose

With Docker installed and a configured `.env`:

```powershell
docker compose up -d postgres
docker compose up --build
docker compose down
```

Run migrations from `backend` after PostgreSQL is healthy:

```powershell
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe schema change"
```

There are intentionally no schema revisions in Phase 0. Application startup never calls
`Base.metadata.create_all()`.

Phase 1 introduced revision `0001_phase1_core`. It creates `cases`, `evidence`,
`evidence_hashes`, `chain_of_custody_entries`, and `audit_events`. Relationships use restrictive
foreign keys: parent deletion does not silently erase forensic records. Raw evidence remains on the
filesystem and is never stored in these tables.

PostgreSQL integration tests require a separate disposable database whose name contains `test`:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@localhost:5432/dfir_test"
uv run pytest
```

The integration suite deliberately refuses to run migration downgrade tests against a database
without `test` in its name.

Phase 2 adds revision `0002_case_number_sequence` for concurrency-safe case numbering.

## Repository areas

- `backend/app/api`, `core`, `db`, `schemas`, `services`, `forensic`, `reporting`: intentional backend boundaries
- `frontend/src/api`, `components`, `pages`, `hooks`, `types`, `utils`, `styles`: frontend boundaries
- `data/cases`: ignored local evidence storage
- `data/samples`: ignored synthetic fixture area
- `data/exports`: ignored report/export storage
- `docs`: supporting documentation
- `scripts`: convenient PowerShell development entry points

Refer to `PRD.md`, `architecture.md`, and `rules.md` for authoritative requirements.

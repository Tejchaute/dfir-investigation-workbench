# DFIR Investigation Workbench

DFIR Investigation Workbench is a planned local-first platform for preserving, analyzing, correlating,
and reporting Windows forensic evidence. The repository is currently at **Phase 0: Project
Foundation**. It contains runtime, storage, database, API, UI, logging, error-handling, and test
infrastructure only. Case management and all forensic capabilities are planned and not implemented.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, psycopg, pytest
- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts
- Database: PostgreSQL 17
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

## Repository areas

- `backend/app/api`, `core`, `db`, `schemas`, `services`, `forensic`, `reporting`: intentional backend boundaries
- `frontend/src/api`, `components`, `pages`, `hooks`, `types`, `utils`, `styles`: frontend boundaries
- `data/cases`: ignored local evidence storage
- `data/samples`: ignored synthetic fixture area
- `data/exports`: ignored report/export storage
- `docs`: supporting documentation
- `scripts`: convenient PowerShell development entry points

Refer to `PRD.md`, `architecture.md`, and `rules.md` for authoritative requirements.

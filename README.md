# DFIR Investigation Workbench

DFIR Investigation Workbench is a planned local-first platform for preserving, analyzing, correlating,
and reporting Windows forensic evidence. The repository is currently at **Phase 7: Timeline Engine**.
It contains the persistent core domain, Case lifecycle API, controlled evidence registration and
verification, the reusable parser framework, and read-only offline EVTX and Registry hive parsers.
It also includes focused Prefetch, Shell Link, and NTFS/$MFT parsers plus a persistent,
provenance-preserving timeline normalization layer. Correlation and later forensic-analysis
capabilities remain planned.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, psycopg, pytest
- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts
- Database: PostgreSQL 18
- Deployment shape: Docker Compose modular monolith (frontend, backend, PostgreSQL)

## Local configuration

Copy `.env.example` to `.env` at the repository root, then replace the development password. `DATABASE_URL` is required;
the backend deliberately fails at startup if it is absent. The example storage roots point to
`data/cases` for evidence and `data/exports` for generated reports. Keep these paths separate.

The Docker evidence mount is writable only so the backend can create its controlled storage copy.
Application workflows never modify a registered copy. Never place real evidence, secrets, or
generated reports under version control.

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

### Evidence API

```text
POST /api/cases/{case_id}/evidence
GET  /api/cases/{case_id}/evidence?limit=25&offset=0
GET  /api/evidence/{evidence_id}
GET  /api/evidence/{evidence_id}/hashes
GET  /api/evidence/{evidence_id}/coc
POST /api/evidence/{evidence_id}/verify
POST /api/evidence/{evidence_id}/parse
GET  /api/evidence/{evidence_id}/artifacts?limit=25&offset=0
GET  /api/artifacts/{artifact_id}
GET  /api/artifacts/{artifact_id}/records?limit=25&offset=0
POST /api/cases/{case_id}/timeline/generate
GET  /api/cases/{case_id}/timeline?limit=100&offset=0
```

Registration accepts multipart file content, evidence metadata, and a required real
`custody_person`. It is allowed only for open cases. The application streams bytes into a
server-generated path beneath `EVIDENCE_ROOT`, computes SHA-256 during the copy, records an
`ACQUISITION` hash and initial custody entry, and never uses the submitted filename as a path.
Evidence numbers use the PostgreSQL-backed `EVD-YYYY-NNNN` sequence format; gaps after rolled-back
transactions are expected. Verification is read-only and records a distinct `VERIFICATION` hash.
A mismatch is reported as `match=false` and is not characterized as tampering.

Filesystem and database commits cannot form one native atomic transaction. Registration therefore
finalizes a unique controlled file before committing metadata and removes only that new file if the
database transaction fails. A process or host crash in that narrow interval can leave an orphaned
file for later administrative reconciliation; it cannot create a completed database record pointing
to a partial copy.

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
Phase 3 adds revision `0003_evidence_number_sequence` for concurrency-safe evidence numbering.
Phase 4 adds revision `0004_parser_framework`, creating generic `artifacts` and `artifact_records`
tables. Every parser run creates a new Artifact so earlier outputs remain auditable. Production has
explicitly registered EVTX and Registry parsers in Phase 5. The Phase 4 generic schema represents
both, so Phase 5 requires no migration. Phase 6 adds Prefetch, LNK, and focused NTFS/$MFT parsing.

Phase 6 adds revision `0005_ntfs_mft_type`, extending the controlled artifact type constraint with
`NTFS_MFT`. The generic parse endpoint now resolves production parsers for `PREFETCH`, `LNK`, and
`NTFS_MFT`; no separate parser API or artifact storage model was introduced.

Phase 7 adds revision `0006_timeline_events`. The `timeline_events` table stores normalized
observations with restrictive provenance foreign keys to Case, Evidence, Artifact, and
ArtifactRecord. Generation is idempotent per source record, event type, timestamp source, and event
ordinal. Re-parsing creates new ArtifactRecords and therefore new historical timeline observations.

## Repository areas

- `backend/app/api`, `core`, `db`, `schemas`, `services`, `forensic`, `reporting`: intentional backend boundaries
- `frontend/src/api`, `components`, `pages`, `hooks`, `types`, `utils`, `styles`: frontend boundaries
- `data/cases`: ignored local evidence storage
- `data/samples`: ignored synthetic fixture area
- `data/exports`: ignored report/export storage
- `docs`: supporting documentation
- `scripts`: convenient PowerShell development entry points

Refer to `PRD.md`, `architecture.md`, and `rules.md` for authoritative requirements.

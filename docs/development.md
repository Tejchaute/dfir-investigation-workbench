# Development notes

The authoritative product, architecture, and implementation constraints remain `PRD.md`,
`architecture.md`, and `rules.md` at the repository root. Phase 0 establishes infrastructure only;
no forensic behavior is implemented.

## Phase 1 database entities

- A Case owns zero or more Evidence metadata records and AuditEvents.
- Evidence belongs to exactly one Case and owns zero or more EvidenceHashes and append-oriented
  ChainOfCustodyEntries. AuditEvents may optionally reference Evidence.
- Evidence files are referenced by paths; binary evidence is not stored in PostgreSQL.
- Foreign keys use `ON DELETE RESTRICT`. ORM relationships do not cascade deletions.
- Case status and evidence type are enforced by database check constraints.
- PostgreSQL UUID columns identify every entity, and AuditEvent details use JSONB.

Apply revision `0001_phase1_core` with `alembic upgrade head`. A downgrade removes the five Phase 1
tables in dependency-safe reverse order. Use downgrade tests only against a disposable test database.

## Phase 2 case management

Case routes are mounted under `/api/cases`. Creation, metadata update, close, and archive operations
write `CASE_CREATED`, `CASE_UPDATED`, `CASE_CLOSED`, and `CASE_ARCHIVED` audit events in the same
database transaction. `case_number_seq` supplies concurrency-safe sequence values for
`CASE-YYYY-NNNN`; gaps are valid when a transaction rolls back. Case status changes are limited to
`OPEN → CLOSED → ARCHIVED` and use row locks to serialize concurrent lifecycle requests.

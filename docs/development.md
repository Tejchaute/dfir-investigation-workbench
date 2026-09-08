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

## Phase 3 evidence integrity and custody

Evidence registration streams a controlled copy beneath `EVIDENCE_ROOT` while calculating its
authoritative acquisition SHA-256. PostgreSQL stores metadata, acquisition and verification hashes,
custody history, and audit events; it never stores evidence bytes. Generated relative storage
references are resolved by the storage boundary, and API clients cannot submit source paths.

## Phase 4 parser framework

The parser framework contains no Windows artifact parser. Production parser registration is explicit
and deterministic; dynamic imports, filesystem discovery, and client-selected executable code are
not supported. A duplicate artifact-type claim fails registration.

```text
Evidence
   ↓
Parser Registry
   ↓
Parser
   ↓
Parser Result
   ↓
Artifact
   ↓
Artifact Records
```

`ForensicParser` is the small extension contract: immutable name/version metadata, declared
`ArtifactType` capabilities, and `parse(ParserContext)`. The context contains identifiers, evidence
type, and an already-opened read-only binary stream. It contains no filesystem path. Future parsers
must return a validated `ParserResult` containing a terminal controlled status, typed normalized
records, warnings, fatal errors, metadata, and numeric statistics.

Results distinguish `COMPLETED`, `COMPLETED_WITH_WARNINGS`, `FAILED`, and `UNSUPPORTED`. Warnings
are preserved and cannot appear in plain completed results. Failed and unsupported results require a
diagnostic error and cannot masquerade as successful empty output. Parser exceptions and malformed
contracts become auditable failed executions without exposing a stack trace through the API.

Each execution creates a new `Artifact`; re-running the same parser never replaces an earlier run.
Each normalized `ArtifactRecord` references exactly one Artifact. Nullable `event_time` remains a
queryable timestamp for later timeline construction, but Phase 4 implements no timeline behavior.
Record retrieval orders by event time, source record identifier, and UUID, with null event times
last, and is bounded by pagination.

```text
ArtifactRecord
   ↓ foreign key
Artifact
   ↓ foreign key
Evidence
   ↓ relationship
SHA-256 acquisition hash
```

The execution service resolves evidence by UUID, requires an acquisition SHA-256, resolves the
controlled copy through `EvidenceStorage`, opens it read-only, selects an explicitly registered
parser, persists the Artifact and records, and writes `PARSER_EXECUTED` through the existing audit
system. No client path is accepted. The `REFERENCE` artifact category and reference parser are used
only by isolated tests; production starts with no concrete parsers registered.

Phase 5 will explicitly register EVTX and Registry parsers. Phase 6 will add Prefetch, LNK, and NTFS
parsers. Those parsers and all timeline, correlation, findings, reporting, and frontend integration
remain outside Phase 4.

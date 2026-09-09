# Development notes

The authoritative product, architecture, and implementation constraints remain `PRD.md`,
`architecture.md`, and `rules.md` at the repository root.

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
only by isolated tests; Phase 5 production registration is described below.

## Phase 5 EVTX and Registry parsers

Phase 5 explicitly registers `DFIR_EVTX` and `DFIR_REGISTRY`, both implementation version `1.0.0`,
in the Phase 4 registry. It uses `python-evtx==0.8.1` and `python-registry==1.3.1`; both are
Apache-2.0, offline, read-only format libraries with Python 3.12-compatible releases. No new schema
is needed because both parsers emit the existing generic Artifact and ArtifactRecord models.

The EVTX adapter validates the EVTX signature, memory-maps the controlled file read-only, traverses
records in file order, and normalizes provider, event ID, channel, computer, level, task, opcode,
keywords, version, record ID, structured EventData, and source XML. Malformed records and chunks
become retained warnings when traversal can continue; an unreadable file is a failed result. An
aware source timestamp populates `event_time` without local-time conversion. A naive timestamp is
preserved as source text with `event_timestamp_timezone_known=false`, while `event_time` remains
null so the application does not invent a timezone.

The Registry adapter validates the `regf` signature and traverses an offline hive deterministically.
It supports library-identified NTUSER, SYSTEM, and SOFTWARE hives; unknown identity is retained as
`UNKNOWN` with a warning instead of being inferred from a filename. Key records preserve paths,
parent paths, and key last-write timestamps. Value records preserve names, library value types,
native structured values, raw bytes, and key provenance. Binary values use base64. Their preview is
bounded to 4096 bytes while original byte length and full-value SHA-256 are retained. Registry key
timestamps populate `event_time` only when timezone-aware; naive values are preserved as text and
explicitly marked as lacking timezone information.

Both parsers receive only the already-opened controlled read-only stream and evidence identifiers.
They accept no client path, run no subprocess, do not dynamically load code, and never write to the
evidence copy. Every run creates a new Artifact, retains warnings/errors and parser/library metadata,
and writes the existing `PARSER_EXECUTED` audit event. Normalized records retain source identifiers
and evidence provenance; no observation is converted into an investigative conclusion.

Deterministic Apache-2.0 upstream regression fixtures are stored as gzip/base64 text and decoded
only into pytest temporary directories. They contain no case data or forensic conclusions; their
origins and hashes are documented beside the fixtures.

Phase 5 is EVTX and generic Registry hive ingestion only. Phase 6 adds Prefetch, LNK, and NTFS;
Phase 7 adds the Timeline Engine; Phase 8 adds Correlation and Findings. Reporting, frontend
integration, authentication, and all higher-level interpretation remain outside Phase 5.

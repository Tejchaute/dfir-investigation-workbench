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

Phase 5 is EVTX and generic Registry hive ingestion only.

## Phase 6 Prefetch, LNK, and focused NTFS/$MFT parsing

Phase 6 explicitly registers `DFIR_PREFETCH`, `DFIR_LNK`, and `DFIR_NTFS_MFT`, each at version
`1.0.0`. They are focused Python structure parsers and add no runtime dependency, native extension,
external executable, subprocess, network access, or dynamic loading. This keeps parsing offline and
inside the Phase 4 read-only `ParserContext` boundary.

The Prefetch parser supports uncompressed versions 17, 23, 26, 30, and 31. It preserves the
application name, format version, executable hash, run count, all available execution FILETIMEs,
referenced paths, and volume metadata. Compressed MAM Prefetch is recognized but returns
`UNSUPPORTED`; decompression is intentionally not approximated. Optional damaged path or volume
structures produce warnings when the core record remains usable. A 64 MiB structural limit prevents
unbounded allocation; real Prefetch files are expected to be substantially smaller.

The Shell Link parser follows MS-SHLLINK structures for the header, LinkTargetIDList, local or
network LinkInfo, Unicode/ANSI StringData, VolumeID, CommonNetworkRelativeLink, and TrackerData. It
preserves target metadata, three target timestamp fields, arguments, descriptions, volume/network
information, and bounded Shell Item headers. Network targets are represented only; they are never
resolved or accessed. Unknown Shell Item classes and damaged optional blocks produce warnings. LNK
timestamps remain distinct metadata observations and are not described as execution times.

The NTFS parser has two explicit input contracts. An MFT-record stream is parsed record by record
using its declared record allocation size and update-sequence geometry. A raw NTFS volume yields
boot geometry and the first MFT record at the boot-sector-defined MFT LCN. Raw-volume mode does not
claim to enumerate a fragmented `$MFT`. Each FILE record requires a valid signature, record bounds,
and update-sequence fixup. The parser recognizes attribute types and extracts
`$STANDARD_INFORMATION`, `$FILE_NAME`, and resident/non-resident `$DATA` metadata. It preserves
data-run allocation metadata but never reconstructs or recovers file content.

NTFS `$STANDARD_INFORMATION` and `$FILE_NAME` creation, modification, MFT-change, and access
timestamps remain separate, with both ISO UTC and raw FILETIME representations. No single “file
timestamp” is selected, and no timestomping inference is made. LNK timestamp families likewise
remain distinct. Prefetch execution history retains every nonzero source timestamp. `event_time` is
used only where one source meaning is unambiguous; Phase 6 performs no timeline normalization.

Revision `0005_ntfs_mft_type` adds the controlled `NTFS_MFT` value while retaining the earlier
unimplemented `NTFS` category for compatibility. The downgrade maps any `NTFS_MFT` Artifact label
back to `NTFS` before restoring the former check constraint. Artifact/ArtifactRecord tables remain
the persistence model, and every rerun creates a new auditable Artifact.

Deterministic binary fixture builders are documented in `backend/tests/fixtures/phase6`. They encode
real format structures with generic synthetic values and no personal or sensitive evidence.

Phase 6 does not implement timeline analysis, timestomping detection, correlation, findings,
reporting, deleted-file recovery, file carving, or full NTFS reconstruction. Phase 7 adds the
Timeline Engine; Phase 8 adds Correlation and Findings. Later-phase frontend and reporting work also
remain outside Phase 6.

## Phase 7 Timeline Engine

Phase 7 consumes persisted ArtifactRecords; it never reopens or reparses evidence. Explicit
normalizers produce canonical `TimelineEvent` rows for EVTX event timestamps, Registry key
LastWrite timestamps, every Prefetch execution-related timestamp, separate LNK creation/access/
modification metadata timestamps, and all distinct NTFS `$STANDARD_INFORMATION` and `$FILE_NAME`
creation/modification/MFT-change/access timestamps.

Each event stores Case, Evidence, Artifact, and ArtifactRecord foreign keys together with parser
identity, artifact and event types, normalized `event_time`, original `raw_time`, exact
`time_source`, source-specific semantics, precision, description, selected correlation-ready
metadata, and provenance identifiers. An aware source timestamp is retained without local-time
conversion. A naive or semantically unknown timestamp retains its raw representation and leaves
`event_time` null; no timezone is invented. Precision is recorded as second, millisecond,
microsecond, 100ns, or unknown according to the source representation.

The event vocabulary is observation-only: `EVTX_EVENT`, `REGISTRY_KEY_LAST_WRITE`,
`PREFETCH_EXECUTION`, three LNK metadata event types, and eight distinct NTFS SI/FN event types.
Descriptions use deterministic templates and contain no suspicion, intent, causality, or user
attribution.

`POST /api/cases/{case_id}/timeline/generate` scans the case's parsed records, inserts only missing
logical events, reports bounded statistics and diagnostics, and records `TIMELINE_GENERATED` using
the existing local application audit actor. Logical identity is enforced by the database across
ArtifactRecord, event type, timestamp source, and event ordinal. Re-running generation does not
duplicate events; a newly parsed Artifact remains a distinct historical source.

`GET /api/cases/{case_id}/timeline` supports bounded `limit`/`offset` pagination plus start/end,
event type, artifact type, evidence, and exact source-identifier filters. Ordering is explicit:
event time ascending with nulls last, then stable provenance/type/ordinal/UUID tie-breakers.

Revision `0006_timeline_events` creates the persistent timeline model, provenance constraints,
indexes, and the idempotency constraint. All foreign keys use `ON DELETE RESTRICT`.

Phase 7 does not perform correlation, findings, timestomping detection, suspiciousness scoring,
maliciousness detection, user attribution, or causality analysis. Those analytical conclusions are
outside the Timeline Engine; Phase 8 adds Correlation and Findings.

### EVTX process-identity compatibility metadata

For Phase 8 compatibility, the EVTX timeline mapping recognizes only Windows Security Event 4688
as a process-creation observation. When its structured EventData contains the exact
`NewProcessName` field with a non-empty value, timeline metadata records a separator-normalized
`process_path`, its deterministic Windows basename as `process_name`, and a
`process_identity_source` object containing the original field name, original value, and event ID.
No identity is inferred when the channel, event ID, field name, or value does not match this
explicit contract.

Timeline generation also applies the same extractor to pre-existing EVTX timeline rows and enriches
only their metadata. This backfill is idempotent and does not modify timestamps, timestamp
semantics, provenance, ArtifactRecords, evidence hashes, or custody history. The extracted identity
is a source observation; it does not establish user intent, maliciousness, or causality. Broader
process-creation normalization is outside this compatibility correction.

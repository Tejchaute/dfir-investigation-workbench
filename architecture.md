# Architecture Document

# DFIR Investigation Workbench

**Document:** architecture.md  
**Version:** 1.0  
**Status:** Approved for MVP Implementation  
**Architecture Style:** Modular Monolith  
**Primary Goal:** Provide Codex with an explicit technical blueprint for implementation.

---

# 1. Architecture Overview

DFIR Investigation Workbench is a **local-first, modular monolith** composed of:

```text
React Frontend
       │
       │ REST / JSON
       ▼
FastAPI Application
       │
       ├── Case Management
       ├── Evidence Management
       ├── Artifact Processing
       ├── Timeline Engine
       ├── Correlation Engine
       ├── Findings
       ├── Reporting
       └── Audit Services
       │
       ├───────────────┐
       ▼               ▼
 PostgreSQL       Local Evidence Storage
```

The application must remain a single deployable system for MVP.

Do **not** introduce microservices.

Do **not** introduce Kubernetes.

Do **not** introduce message brokers such as Kafka or RabbitMQ.

Do **not** introduce cloud dependencies.

The architecture should be modular internally so that services can be separated in the future if the product grows.

---

# 2. Architectural Principles

The architecture follows these principles.

## 2.1 Evidence First

The original evidence is the source of truth.

Everything else is derived data.

```text
Original Evidence
       ↓
Artifact Extraction
       ↓
Normalized Data
       ↓
Timeline
       ↓
Correlation
       ↓
Finding
       ↓
Report
```

---

## 2.2 Immutable Original Evidence

The application must never modify original evidence.

Evidence files should be treated as:

```text
READ ONLY
```

All derived data is stored separately.

---

## 2.3 Provenance Everywhere

Every derived forensic object should be traceable back to its source.

```text
Finding
   ↓
Timeline Event
   ↓
Artifact Record
   ↓
Evidence
   ↓
SHA-256
```

---

## 2.4 Modular Parsers

Parsers must be independent from the API and UI.

A parser must not know about React.

A parser must not contain HTTP logic.

A parser must not directly manipulate frontend state.

The parser layer emits normalized domain objects.

---

## 2.5 Transparent Correlation

Correlation rules must be deterministic and explainable.

The system must be able to answer:

> Why did this finding appear?

---

## 2.6 No Fabricated Evidence

The application must never invent:

- timestamps
- users
- paths
- event IDs
- forensic conclusions
- confidence
- artifact values

Unknown information remains unknown.

---

## 2.7 Local-First

The MVP operates locally.

```text
Evidence ──> Local Storage
Database ──> Local PostgreSQL
Processing ─> Local Python
UI ────────> Local React
```

No evidence should be sent to external APIs.

---

# 3. Technology Stack

## 3.1 Frontend

```text
React
TypeScript
Vite
Tailwind CSS
shadcn/ui
React Router
TanStack Query
Recharts
```

React will be used with TypeScript to improve type safety across the UI. React's official documentation supports TypeScript integration directly in React applications.

### Frontend responsibilities

- Render investigation UI.
- Manage navigation.
- Fetch API data.
- Handle filters/search.
- Render timeline.
- Render findings.
- Display provenance.
- Trigger evidence processing.
- Trigger report generation.

The frontend must not implement forensic parsing logic.

---

# 4. Backend Stack

```text
Python 3.x
FastAPI
Pydantic
SQLAlchemy 2.x
Alembic
psycopg
pytest
```

FastAPI is responsible for the HTTP/API boundary.

Pydantic models are responsible for request/response validation and domain-facing schemas.

SQLAlchemy is the database abstraction layer. SQLAlchemy 2.x provides the modern ORM and Core APIs used for application persistence.

Alembic manages database schema migrations and should be used for all schema changes. Alembic provides migration generation and migration execution around SQLAlchemy metadata.

---

# 5. Database

The MVP uses:

```text
PostgreSQL
```

PostgreSQL stores:

```text
Cases
Evidence Metadata
Artifact Records
Timeline Events
Findings
Correlation Rules
Chain of Custody
Investigation Notes
Processing Jobs
Audit Events
Reports
```

PostgreSQL must not be used as a binary repository for large evidence images.

---

# 6. Evidence Storage

Raw evidence is stored on the local filesystem.

Recommended structure:

```text
data/
└── cases/
    ├── CASE-2026-001/
    │   ├── evidence/
    │   │   ├── EVD-001/
    │   │   │   └── source.evtx
    │   │   └── EVD-002/
    │   │       └── NTUSER.DAT
    │   ├── reports/
    │   ├── exports/
    │   └── metadata/
    │
    └── CASE-2026-002/
```

Database records contain references to these locations.

---

# 7. Repository Structure

The project root should follow this structure:

```text
dfir-investigation-workbench/
│
├── PRD.md
├── architecture.md
├── rules.md
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   ├── dependencies.py
│   │   │   │
│   │   │   └── routes/
│   │   │       ├── cases.py
│   │   │       ├── evidence.py
│   │   │       ├── artifacts.py
│   │   │       ├── timeline.py
│   │   │       ├── findings.py
│   │   │       ├── correlation.py
│   │   │       ├── reports.py
│   │   │       └── custody.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── case.py
│   │   │       ├── evidence.py
│   │   │       ├── artifact.py
│   │   │       ├── timeline.py
│   │   │       ├── finding.py
│   │   │       ├── custody.py
│   │   │       ├── note.py
│   │   │       ├── job.py
│   │   │       ├── audit.py
│   │   │       └── report.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── case.py
│   │   │   ├── evidence.py
│   │   │   ├── artifact.py
│   │   │   ├── timeline.py
│   │   │   ├── finding.py
│   │   │   ├── custody.py
│   │   │   ├── job.py
│   │   │   └── report.py
│   │   │
│   │   ├── services/
│   │   │   ├── case_service.py
│   │   │   ├── evidence_service.py
│   │   │   ├── hashing_service.py
│   │   │   ├── custody_service.py
│   │   │   ├── artifact_service.py
│   │   │   ├── timeline_service.py
│   │   │   ├── correlation_service.py
│   │   │   ├── finding_service.py
│   │   │   ├── report_service.py
│   │   │   ├── audit_service.py
│   │   │   └── job_service.py
│   │   │
│   │   ├── forensic/
│   │   │   ├── interfaces/
│   │   │   │   ├── parser.py
│   │   │   │   └── normalizer.py
│   │   │   │
│   │   │   ├── parsers/
│   │   │   │   ├── evtx/
│   │   │   │   ├── registry/
│   │   │   │   ├── prefetch/
│   │   │   │   ├── lnk/
│   │   │   │   └── ntfs/
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── artifact_record.py
│   │   │   │   └── timeline_event.py
│   │   │   │
│   │   │   ├── timeline/
│   │   │   │   ├── normalizer.py
│   │   │   │   ├── builder.py
│   │   │   │   └── query.py
│   │   │   │
│   │   │   └── correlation/
│   │   │       ├── engine.py
│   │   │       ├── rule.py
│   │   │       └── rules/
│   │   │           ├── usb_activity.py
│   │   │           ├── powershell_sequence.py
│   │   │           ├── execution_activity.py
│   │   │           └── timestamp_anomaly.py
│   │   │
│   │   └── reporting/
│   │       ├── generator.py
│   │       ├── templates/
│   │       └── components/
│   │
│   └── tests/
│       ├── unit/
│       ├── integration/
│       ├── forensic/
│       └── fixtures/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       │
│       ├── api/
│       │   ├── client.ts
│       │   ├── cases.ts
│       │   ├── evidence.ts
│       │   ├── timeline.ts
│       │   ├── findings.ts
│       │   └── reports.ts
│       │
│       ├── components/
│       │   ├── layout/
│       │   ├── cases/
│       │   ├── evidence/
│       │   ├── timeline/
│       │   ├── findings/
│       │   ├── custody/
│       │   └── reports/
│       │
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Cases.tsx
│       │   ├── CaseOverview.tsx
│       │   ├── Evidence.tsx
│       │   ├── Timeline.tsx
│       │   ├── Findings.tsx
│       │   ├── Custody.tsx
│       │   └── Report.tsx
│       │
│       ├── hooks/
│       ├── types/
│       ├── utils/
│       └── styles/
│
├── data/
│   ├── cases/
│   ├── samples/
│   └── exports/
│
├── docs/
│   ├── demo-case.md
│   ├── development.md
│   └── forensic-methodology.md
│
└── scripts/
    ├── dev.sh
    ├── test.sh
    └── seed_demo_case.py
```

---

# 8. Backend Architectural Layers

The backend follows:

```text
HTTP Layer
    ↓
API Routes
    ↓
Application Services
    ↓
Domain / Forensic Services
    ↓
Persistence
```

The layers should remain separated.

---

# 9. API Layer

Location:

```text
backend/app/api/
```

Responsibilities:

- HTTP request handling.
- Authentication/authorization boundary if introduced later.
- Request validation.
- Response serialization.
- Calling application services.

API routes must not contain complex forensic logic.

Bad:

```python
@router.post("/parse")
def parse():
    # 300 lines of EVTX parsing
```

Good:

```python
@router.post("/parse")
def parse(...):
    return artifact_service.process_evidence(...)
```

---

# 10. Service Layer

Location:

```text
backend/app/services/
```

Services coordinate application behavior.

Example:

```text
EvidenceService
      ↓
HashingService
      ↓
CustodyService
      ↓
JobService
```

Services may coordinate multiple domain modules.

They should not contain parser-specific implementation.

---

# 11. Forensic Processing Layer

Location:

```text
backend/app/forensic/
```

This is the core forensic analysis layer.

Responsibilities:

- Parser interfaces.
- Parser implementations.
- Artifact normalization.
- Timeline construction.
- Correlation.
- Forensic domain models.

This layer should be as independent from FastAPI as practical.

Ideally, a parser can be executed from a Python test without starting the web server.

---

# 12. Parser Plugin Architecture

Every parser must implement a common interface.

Conceptually:

```python
class ArtifactParser(Protocol):
    parser_name: str
    parser_version: str

    def can_parse(self, source: Path) -> bool:
        ...

    def parse(self, source: Path) -> ParseResult:
        ...
```

The actual implementation may use an abstract base class instead of `Protocol` if that produces a cleaner design.

Parser output:

```text
ParseResult
├── parser_name
├── parser_version
├── source
├── artifact_records[]
├── timeline_events[]
├── warnings[]
└── errors[]
```

---

# 13. Parser Lifecycle

The processing lifecycle is:

```text
Evidence
   ↓
Evidence Validation
   ↓
Artifact Detection
   ↓
Parser Selection
   ↓
Parser Execution
   ↓
Artifact Records
   ↓
Timeline Events
   ↓
Persistence
   ↓
Processing Result
```

---

# 14. Parser Isolation

A parser must:

- Never modify evidence.
- Never delete evidence.
- Never modify the source file.
- Never execute arbitrary content from evidence.
- Report malformed input explicitly.
- Preserve provenance.
- Produce deterministic output for deterministic input where possible.

---

# 15. Artifact Detection

The system should determine which parser is appropriate based on evidence type and/or file characteristics.

Example:

```text
Security.evtx
      ↓
EVTX Parser

NTUSER.DAT
      ↓
Registry Parser

*.pf
      ↓
Prefetch Parser

*.lnk
      ↓
LNK Parser

Disk Image
      ↓
NTFS / MFT Parser
```

Parser detection should be extensible.

---

# 16. Artifact Record Model

An `ArtifactRecord` represents extracted forensic information before or alongside timeline normalization.

Conceptually:

```text
ArtifactRecord
├── record_id
├── case_id
├── evidence_id
├── artifact_type
├── parser_name
├── parser_version
├── source_reference
├── extracted_at
├── raw_data
└── normalized_data
```

The exact database representation may use JSON columns for parser-specific information.

---

# 17. Normalized Timeline Model

Different artifacts contain different field structures.

The timeline engine converts them into a common model.

```text
Artifact-Specific Data
        ↓
Timestamp Extraction
        ↓
Event Classification
        ↓
Field Normalization
        ↓
TimelineEvent
```

Example:

```text
EVTX
Registry
Prefetch
LNK
MFT

     ↓

Normalized TimelineEvent
```

---

# 18. Timeline Event Architecture

A timeline event should contain:

```text
event_id
case_id
evidence_id
artifact_id
timestamp_utc
original_timestamp
timezone
timestamp_precision
event_type
artifact_type
source
user
path
description
metadata
parser_name
parser_version
source_reference
confidence
```

---

# 19. Timestamp Architecture

Store at least:

```text
original_timestamp
timestamp_utc
timezone_offset
timestamp_precision
timezone_status
```

Examples of timezone status:

```text
KNOWN
UNKNOWN
INFERRED
```

MVP should prefer:

```text
KNOWN
UNKNOWN
```

Do not silently infer timezone unless the source explicitly provides enough information.

The original timestamp must always remain available.

---

# 20. Timestamp Precision

Not all forensic timestamps have equal precision.

Support:

```text
MICROSECOND
MILLISECOND
SECOND
MINUTE
DATE
UNKNOWN
```

This prevents the platform from falsely implying greater precision than the source provides.

---

# 21. Timeline Ordering

The primary sorting key is:

```text
timestamp_utc
```

Secondary deterministic keys may be:

```text
event_type
event_id
```

This ensures stable ordering when timestamps are equal.

---

# 22. Timeline Query Architecture

Timeline queries should be database-backed.

Example:

```text
GET /api/cases/{case_id}/events
```

Supported filters:

```text
start_time
end_time
artifact_type
event_type
user
keyword
confidence
finding_status
```

Pagination must be supported.

The system must not retrieve millions of events into the frontend in one request.

---

# 23. Correlation Architecture

The correlation engine operates on normalized timeline events.

```text
Timeline Events
       ↓
Rule Engine
       ↓
Matched Conditions
       ↓
Correlation Result
       ↓
Finding
```

---

# 24. Rule Interface

Conceptual interface:

```python
class CorrelationRule:
    rule_id: str
    name: str
    description: str

    def evaluate(
        self,
        events: list[TimelineEvent]
    ) -> CorrelationResult:
        ...
```

The architecture should allow individual rules to be tested independently.

---

# 25. Correlation Rule Output

A rule result should contain:

```text
rule_id
matched
confidence
severity
explanation
related_event_ids
limitations
```

The rule must never silently create a finding with no explanation.

---

# 26. Finding Architecture

The correlation engine produces findings through the Finding Service.

```text
Correlation Result
        ↓
Finding Service
        ↓
Finding
        ↓
Database
```

A finding must retain:

```text
finding_id
case_id
title
description
severity
confidence
status
rule_id
created_at
related_events
related_evidence
analyst_notes
```

---

# 27. Severity and Confidence

Severity:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Confidence:

```text
LOW
MEDIUM
HIGH
```

These values must remain independent.

Do not convert confidence directly into severity.

---

# 28. Chain-of-Custody Architecture

Chain of custody is part of the evidence domain.

```text
Evidence
    │
    └── ChainOfCustodyEntry[]
```

Each record contains:

```text
entry_id
evidence_id
timestamp
person
action
location
notes
```

The system should use append-oriented operations.

---

# 29. Hashing Architecture

Hash calculation belongs in:

```text
HashingService
```

Evidence hashing must use streaming reads.

Conceptually:

```text
Evidence File
     ↓
Read Chunk
     ↓
SHA-256 Update
     ↓
Read Next Chunk
     ↓
...
     ↓
Final Digest
```

Do not load large evidence files completely into RAM simply to hash them.

---

# 30. Evidence Verification

Evidence verification flow:

```text
Stored SHA-256
       +
New SHA-256
       ↓
Comparison
       ↓
VERIFIED / MISMATCH
```

The original digest must never be overwritten automatically after a mismatch.

---

# 31. Processing Job Architecture

Long-running parsing operations should be represented by `ProcessingJob`.

```text
QUEUED
   ↓
RUNNING
   ↓
COMPLETED
```

Failure:

```text
RUNNING
   ↓
FAILED
```

Cancellation may be supported later.

For MVP, jobs may initially execute using FastAPI background processing or a lightweight application-managed worker.

Do not introduce Celery, RabbitMQ, Kafka, or Redis unless performance requirements later justify them.

---

# 32. Job Flow

```text
User clicks "Parse Evidence"
            ↓
POST /evidence/{id}/parse
            ↓
Create ProcessingJob
            ↓
Parser Service
            ↓
Parse
            ↓
Persist artifacts/events
            ↓
Update job
            ↓
COMPLETED
```

The frontend can poll job status.

---

# 33. Reporting Architecture

Reporting is isolated from the API layer.

```text
Report API
    ↓
Report Service
    ↓
Report Data Aggregation
    ↓
Report Generator
    ↓
PDF
```

The report generator should not query the database independently in an uncontrolled way.

It should receive a structured report model.

---

# 34. Report Generation Flow

```text
Case
 ↓
Evidence Summary
 ↓
Custody Summary
 ↓
Timeline Summary
 ↓
Findings
 ↓
Investigator Notes
 ↓
Report Model
 ↓
Report Generator
 ↓
PDF
```

---

# 35. Report Structure

```text
Title Page
   ↓
Case Summary
   ↓
Methodology
   ↓
Evidence Inventory
   ↓
Hash Verification
   ↓
Chain of Custody
   ↓
Timeline Summary
   ↓
Notable Events
   ↓
Findings
   ↓
Conclusion
   ↓
Appendix
```

---

# 36. Frontend Architecture

The React application is organized around feature domains.

```text
pages/
components/
hooks/
api/
types/
utils/
```

The UI must consume the REST API through a centralized API client.

Do not allow individual components to construct raw `fetch()` calls everywhere.

---

# 37. Frontend Data Flow

Example:

```text
Timeline Page
     ↓
useTimeline()
     ↓
timeline API client
     ↓
FastAPI
     ↓
Timeline Service
     ↓
PostgreSQL
     ↓
JSON
     ↓
React
```

---

# 38. Frontend Screen Flow

Primary navigation:

```text
Dashboard
   │
   ├── Cases
   │     └── Case Overview
   │            ├── Evidence
   │            ├── Timeline
   │            ├── Findings
   │            ├── Chain of Custody
   │            └── Reports
   │
   └── Global Search
```

---

# 39. Case Investigation Flow

A typical UI sequence:

```text
Cases
  ↓
Open Case
  ↓
Case Overview
  ↓
Evidence
  ↓
Run Parser
  ↓
Timeline
  ↓
Select Event
  ↓
Inspect Provenance
  ↓
Findings
  ↓
Review Finding
  ↓
Generate Report
```

---

# 40. Provenance UI

When viewing a timeline event, the examiner should be able to see:

```text
Timeline Event
      ↓
Artifact
      ↓
Evidence
      ↓
Evidence SHA-256
```

When viewing a finding:

```text
Finding
 ├── Rule
 ├── Supporting Events
 │      ├── Event A
 │      ├── Event B
 │      └── Event C
 └── Supporting Evidence
```

This is a core differentiator of the application.

---

# 41. API Response Design

API responses should be predictable.

Example:

```json
{
  "data": {},
  "meta": {},
  "errors": []
}
```

For lists:

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total": 421
  },
  "errors": []
}
```

The exact response envelope may be simplified if it adds unnecessary complexity, but the API should remain consistent.

---

# 42. Error Architecture

Errors are handled in layers.

```text
Parser Exception
      ↓
Forensic Error
      ↓
Service Error
      ↓
API Error
      ↓
Frontend Error Display
```

The API must not expose raw stack traces to users.

Detailed exceptions should be logged server-side.

---

# 43. Logging Architecture

Use structured application logging.

Log:

```text
timestamp
level
service
operation
case_id
evidence_id
job_id
message
error
```

Do not log entire evidence contents.

Do not log secrets.

Do not unnecessarily log sensitive artifact values.

---

# 44. Audit Architecture

Application audit events are separate from evidence chain of custody.

### Audit

Records software actions:

```text
USER_CREATED_CASE
EVIDENCE_ADDED
HASH_VERIFIED
PARSER_STARTED
PARSER_FINISHED
CORRELATION_EXECUTED
REPORT_GENERATED
```

### Chain of Custody

Records evidence handling:

```text
RECEIVED
TRANSFERRED
STORED
ANALYZED
EXPORTED
```

These must remain conceptually separate.

---

# 45. Database Relationship Model

Conceptual relationships:

```text
CASE
 │
 ├────< EVIDENCE
 │         │
 │         ├────< CUSTODY_ENTRY
 │         │
 │         ├────< ARTIFACT
 │         │
 │         └────< PROCESSING_JOB
 │
 ├────< TIMELINE_EVENT
 │
 ├────< FINDING
 │         │
 │         └────< FINDING_EVENT
 │
 ├────< INVESTIGATION_NOTE
 │
 ├────< AUDIT_EVENT
 │
 └────< REPORT
```

---

# 46. Many-to-Many Finding/Event Relationship

A finding can reference multiple events.

An event may support multiple findings.

Therefore:

```text
FINDING
   │
   └── FINDING_EVENT
           │
           └── TIMELINE_EVENT
```

This should be modeled explicitly rather than storing arbitrary event IDs in an unstructured string.

---

# 47. Evidence/Event Relationship

An event should reference the evidence that produced it.

```text
EVIDENCE
   │
   └──< TIMELINE_EVENT
```

If an event is derived through multiple stages, provenance metadata can additionally identify the originating artifact record.

---

# 48. Parser-to-Database Flow

The parser must not be tightly coupled to SQLAlchemy.

Preferred:

```text
Parser
  ↓
ParseResult
  ↓
Artifact Service
  ↓
Persistence Adapter
  ↓
SQLAlchemy
```

This makes parser unit tests much easier.

---

# 49. Database Transaction Boundaries

A parser operation should not create one giant transaction containing an entire disk image analysis.

Prefer controlled batches.

Conceptually:

```text
Parse Batch
   ↓
Validate
   ↓
Persist
   ↓
Commit
```

This prevents one failure from invalidating a huge processing run.

Exact batching strategy can be implemented after measuring actual dataset sizes.

---

# 50. Configuration

Application configuration should come from environment variables.

Example:

```text
DATABASE_URL
EVIDENCE_ROOT
REPORT_ROOT
LOG_LEVEL
API_HOST
API_PORT
CORS_ORIGINS
```

Never hardcode credentials.

`.env` must never be committed.

Provide:

```text
.env.example
```

instead.

---

# 51. Docker Architecture

MVP Docker setup:

```text
docker-compose.yml
       │
       ├── backend
       ├── frontend
       └── postgres
```

Conceptually:

```text
Browser
   ↓
Frontend
   ↓
Backend
   ↓
PostgreSQL

Backend
   ↓
Local Evidence Volume
```

Evidence must remain on a controlled host-mounted volume.

Do not containerize the evidence itself.

---

# 52. Docker Volumes

Example:

```text
postgres_data
evidence_data
reports_data
```

The evidence volume must be mounted into the backend as a controlled path.

---

# 53. Development Environment

Recommended development environment:

```text
Windows host
+
WSL2 / Linux-compatible development environment
+
Docker Desktop
+
VS Code
+
Codex
```

The architecture itself should remain platform-conscious because forensic parsing libraries may have differing platform dependencies.

---

# 54. CLI Architecture

CLI commands should reuse application services.

```text
CLI
 ↓
Application Services
 ↓
Domain / Forensic Services
 ↓
Database / Storage
```

Never create:

```text
CLI Logic
+
API Logic
```

as two independent implementations.

---

# 55. Future Module Architecture

Future modules must plug into the same domain architecture.

Example malware module:

```text
Malware Analyzer
      ↓
Analysis Result
      ↓
Artifact
      ↓
Finding
      ↓
Timeline
      ↓
Report
```

Steganography:

```text
Stego Analyzer
      ↓
Analysis Result
      ↓
Artifact
      ↓
Finding
      ↓
Report
```

Anti-forensics:

```text
Anomaly Detector
      ↓
Timeline / Finding
      ↓
Report
```

Therefore, the core architecture must avoid assuming that every artifact comes from a Windows event log.

---

# 56. Future Module Interfaces

Future modules should be able to produce a common result type:

```text
AnalysisResult
├── analyzer_name
├── analyzer_version
├── status
├── observations[]
├── indicators[]
├── timeline_events[]
├── findings[]
├── warnings[]
└── provenance
```

This is an extension point rather than an MVP implementation requirement.

---

# 57. Security Boundary

The highest-risk input is forensic evidence.

Treat:

```text
Evidence Files
Artifact Content
Metadata
Extracted Strings
Paths
Registry Values
Event Messages
```

as untrusted input.

Never assume artifact content is safe.

Do not execute:

```text
.exe
.dll
.ps1
.bat
.cmd
.vbs
.js
```

as part of forensic parsing.

---

# 58. Path Security

All evidence paths must be validated.

The application must prevent:

```text
../
..\ 
absolute path escape
symlink escape
```

from accessing arbitrary files outside the evidence root.

---

# 59. External Process Rules

External forensic utilities may be introduced later where necessary.

When external processes are used:

- Arguments must be constructed from validated values.
- `shell=True` must be avoided.
- Executable paths must be trusted and configured.
- Timeouts should exist.
- Exit codes must be checked.
- stdout/stderr must be captured safely.

MVP should minimize subprocess usage.

---

# 60. Performance Architecture

The MVP is not designed for enterprise-scale forensic processing.

However:

### Hashing

Use streaming.

### Parsing

Process records incrementally where possible.

### Database

Use bulk inserts for large event sets.

### Timeline

Use indexed timestamp fields.

### API

Use pagination.

### Frontend

Render only the currently required event set.

Do not load the entire timeline at once.

---

# 61. Database Index Strategy

Important indexes should include:

```text
cases.case_id
evidence.case_id
timeline_events.case_id
timeline_events.timestamp_utc
timeline_events.evidence_id
timeline_events.event_type
timeline_events.artifact_type
findings.case_id
findings.severity
findings.status
processing_jobs.case_id
processing_jobs.status
```

Composite indexes can be introduced after observing real query patterns.

---

# 62. API Pagination

Timeline endpoints must be paginated.

Example:

```text
?page=1&page_size=100
```

or cursor-based pagination if later required.

For MVP, offset/page pagination is acceptable.

---

# 63. Testing Architecture

Testing structure:

```text
tests/
├── unit/
│   ├── hashing/
│   ├── services/
│   └── schemas/
│
├── forensic/
│   ├── evtx/
│   ├── registry/
│   ├── prefetch/
│   ├── lnk/
│   └── ntfs/
│
├── integration/
│   ├── evidence_flow/
│   ├── timeline_flow/
│   └── report_flow/
│
└── fixtures/
```

---

# 64. Parser Tests

Every parser should contain tests for:

```text
Valid input
Malformed input
Empty input
Unsupported input
Expected fields
Timestamp handling
Provenance
```

---

# 65. Timeline Tests

Test:

```text
Timestamp normalization
Timezone handling
Ordering
Equal timestamps
Unknown timestamps
Filtering
Search
Pagination
Provenance
```

---

# 66. Correlation Tests

For every correlation rule:

```text
Positive case
Negative case
Boundary case
Insufficient evidence case
```

The objective is to reduce false positives.

---

# 67. Integration Test

At least one end-to-end path must work:

```text
Evidence
  ↓
Hash
  ↓
Parse
  ↓
Artifact
  ↓
Timeline
  ↓
Correlation
  ↓
Finding
  ↓
Report
```

---

# 68. Demo Dataset Architecture

The repository should provide a reproducible demo case.

Example:

```text
data/samples/demo-case/
├── Security.evtx
├── System.evtx
├── PowerShell.evtx
├── NTUSER.DAT
├── SYSTEM
├── SOFTWARE
├── sample.pf
└── sample.lnk
```

If real datasets cannot be redistributed, the repository should provide instructions for obtaining or creating equivalent test data.

Do not commit confidential forensic evidence.

---

# 69. Git Architecture

Use logical commits.

Example:

```text
feat: initialize backend architecture
feat: implement case management
feat: implement evidence integrity
feat: add EVTX parser
feat: add registry parser
feat: implement timeline engine
feat: add correlation engine
feat: implement report generation
test: add integration coverage
docs: add demo investigation
```

Avoid huge commits containing unrelated generated code.

---

# 70. Codex Implementation Strategy

Codex should implement the system incrementally.

Never ask Codex:

```text
"Build the entire DFIR platform."
```

Instead:

```text
Architecture
   ↓
Database
   ↓
Case
   ↓
Evidence
   ↓
Hashing
   ↓
Custody
   ↓
Parser Framework
   ↓
EVTX
   ↓
Registry
   ↓
Prefetch
   ↓
LNK
   ↓
NTFS
   ↓
Timeline
   ↓
Correlation
   ↓
Findings
   ↓
Reporting
   ↓
Frontend
   ↓
Integration
```

Each stage must be tested before moving to the next.

---

# 71. Codex Context Files

Codex should always have access to:

```text
PRD.md
architecture.md
rules.md
```

These are the authoritative project documents.

Hierarchy:

```text
PRD.md
   ↓
What the product must do

architecture.md
   ↓
How the product is structured

rules.md
   ↓
What implementation constraints must never be violated
```

---

# 72. Implementation Priority

Priority order:

```text
P0
Project foundation
Database
Case
Evidence
Hashing
Custody

P1
Parser framework
EVTX
Registry
Prefetch
LNK
NTFS

P2
Timeline
Filtering
Search
Provenance

P3
Correlation
Findings

P4
Reporting

P5
Frontend refinement

P6
Testing
Documentation
Demo
```

---

# 73. Vertical Slice Strategy

Whenever practical, implement complete vertical slices.

Example:

```text
Case API
    +
Case DB
    +
Case UI
```

instead of building every database model first and every frontend screen later.

This lets the application become demonstrably functional earlier.

---

# 74. Recommended Development Sequence

## Stage 1 — Foundation

```text
Repository
Docker
PostgreSQL
FastAPI
React
Environment configuration
```

## Stage 2 — Evidence Core

```text
Case
Evidence
Hashing
Custody
```

## Stage 3 — Forensic Engine

```text
Parser interface
EVTX
Registry
Prefetch
LNK
NTFS
```

## Stage 4 — Timeline

```text
Normalized event model
Timestamp normalization
Timeline queries
Frontend timeline
```

## Stage 5 — Intelligence

```text
Correlation rules
Findings
Provenance
```

## Stage 6 — Reporting

```text
Report model
PDF generation
Report UI
```

## Stage 7 — Finalization

```text
Testing
Demo
Documentation
UI polish
```

---

# 75. Dependency Direction

Dependencies should generally point inward:

```text
API
 ↓
Services
 ↓
Domain / Forensic Logic
 ↓
Infrastructure
```

The forensic parser layer should not depend on React.

The database layer should not contain forensic reasoning.

The frontend should not implement business rules.

---

# 76. Avoid Overengineering

The MVP must not introduce:

```text
Microservices
Event-driven distributed architecture
Kubernetes
Kafka
RabbitMQ
Redis
Elasticsearch
Graph databases
ML pipelines
Cloud object storage
Complex IAM
Multi-tenancy
```

unless a specific requirement later justifies them.

The goal is a strong forensic engineering project, not infrastructure complexity.

---

# 77. Architecture Quality Bar

A technically "working" system is insufficient.

The architecture is considered successful when:

```text
Parser modules can be added independently.
        +
Timeline code does not depend on specific parser internals.
        +
Findings retain provenance.
        +
Evidence remains immutable.
        +
Reporting consumes structured investigation data.
        +
Frontend remains independent from forensic logic.
```

---

# 78. Final Architecture

The complete MVP flow is:

```text
                    ┌──────────────────────┐
                    │     React / UI       │
                    └──────────┬───────────┘
                               │
                            REST API
                               │
                    ┌──────────▼───────────┐
                    │       FastAPI        │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
                 ▼             ▼             ▼
             Case/Evidence  Timeline    Reporting
               Services      Service      Service
                 │             ▲             ▲
                 │             │             │
                 ▼             │             │
          ┌─────────────┐      │             │
          │  Forensic   │──────┘             │
          │   Engine    │                    │
          └──────┬──────┘                    │
                 │                           │
       ┌─────────┼─────────┐                 │
       ▼         ▼         ▼                 │
     EVTX     Registry   Prefetch            │
       │         │         │                 │
       ├─────────┼─────────┤                 │
       │         │         │                 │
       ▼         ▼         ▼                 │
      LNK       NTFS    Artifacts             │
                 │                            │
                 └──────────┐                 │
                            ▼                 │
                       Timeline Events       │
                            │                 │
                            ▼                 │
                     Correlation Engine       │
                            │                 │
                            ▼                 │
                        Findings ─────────────┤
                                              │
                                              ▼
                                      Report Generator
                                              │
                                              ▼
                                          PDF Report

             ┌────────────────────────────────────┐
             │            PostgreSQL              │
             │ Cases / Evidence / Events / etc.  │
             └────────────────────────────────────┘

             ┌────────────────────────────────────┐
             │        Local Evidence Store        │
             │        Original Evidence           │
             └────────────────────────────────────┘
```

---

# 79. Architecture Summary

The MVP is intentionally designed as a **modular monolith**.

The most important separation is:

```text
Evidence
   ↓
Forensic Processing
   ↓
Normalized Investigation Data
   ↓
Investigator Intelligence
   ↓
Reporting
```

The system should therefore be thought of as:

> **A forensic investigation pipeline with a web-based investigator interface.**

Not:

> A web dashboard containing forensic scripts.

That distinction should guide all implementation decisions.

---

# 80. Architectural End State for MVP

At the end of the MVP, the repository should contain:

```text
PRD.md
architecture.md
rules.md

backend/
├── API
├── Services
├── Forensic Engine
├── Database
├── Reporting
└── Tests

frontend/
├── Dashboard
├── Cases
├── Evidence
├── Timeline
├── Findings
├── Custody
└── Reports

data/
└── reproducible demo evidence
```

The architecture must remain simple enough to complete quickly while providing clear extension points for:

```text
Malware Triage
Steganography Analysis
Anti-Forensics Detection
Memory Forensics
Network Forensics
Browser Forensics
```

Those modules should extend the existing forensic pipeline rather than create independent applications.
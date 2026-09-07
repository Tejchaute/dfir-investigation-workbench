# Development & AI Rules

# DFIR Investigation Workbench

**Document:** rules.md  
**Version:** 1.0  
**Status:** Mandatory  
**Applies To:** Codex, developers, contributors, automated agents, and future implementation tasks

---

# 1. Purpose

This document defines the mandatory engineering, forensic, security, architectural, dependency, testing, and AI-development rules for the DFIR Investigation Workbench.

These rules exist to prevent:

- Architectural drift
- Scope creep
- Unsafe evidence handling
- Fabricated forensic results
- Unnecessary dependencies
- Overengineering
- Unverified AI-generated code
- Weak forensic provenance
- Silent parser failures
- Misleading investigative conclusions

These rules are mandatory unless explicitly superseded by a later project decision.

---

# 2. Authority Hierarchy

When making implementation decisions, follow this priority:

```text
1. Explicit user instruction
        ↓
2. PRD.md
        ↓
3. architecture.md
        ↓
4. rules.md
        ↓
5. Existing project implementation
        ↓
6. General engineering conventions
```

When documents conflict:

1. Stop and identify the conflict.
2. Do not silently choose an interpretation.
3. Follow the higher-priority instruction.
4. Preserve compatibility where reasonably possible.

Do not invent requirements.

---

# 3. Scope Lock

The MVP scope is strictly defined in `PRD.md`.

Codex must not automatically add:

```text
Browser forensics
Recycle Bin
Scheduled Tasks
Memory forensics
Network forensics
Malware execution
Malware sandboxing
Steganography
Anti-forensics
Machine learning
Cloud analysis
Cloud storage
Multi-tenancy
Enterprise authentication
Kubernetes
Microservices
Kafka
RabbitMQ
Large-scale distributed processing
```

unless explicitly requested.

When a possible improvement falls outside the current scope:

```text
Identify
→ Explain
→ Do not implement automatically
→ Record as future work if appropriate
```

---

# 4. Do Not Overengineer

This project is intentionally a modular monolith.

Do not introduce complexity merely because it is technically possible.

Avoid adding:

```text
Microservices
Event buses
Message queues
Kubernetes
Service meshes
Graph databases
Elasticsearch
Redis
Celery
Terraform
Cloud infrastructure
Complex IAM
```

unless a demonstrated requirement makes them necessary.

The project must remain understandable to a single developer.

---

# 5. Core Architecture Rule

The architecture must remain:

```text
Frontend
    ↓
API
    ↓
Application Services
    ↓
Forensic / Domain Services
    ↓
Infrastructure
    ↓
Database / Filesystem
```

Do not bypass layers without a strong reason.

---

# 6. Frontend Rules

The frontend must be responsible for:

```text
Presentation
Navigation
User interaction
API communication
Filtering
Visualization
Client-side UI state
```

The frontend must NOT:

```text
Parse EVTX
Parse Registry hives
Parse NTFS
Calculate forensic findings
Implement correlation rules
Modify evidence
Generate forensic conclusions
```

Forensic logic belongs in the backend/domain layer.

---

# 7. Backend API Rules

FastAPI routes must remain thin.

Routes should:

```text
Validate request
→ Call service
→ Return response
```

Routes must not contain:

```text
Large parser implementations
Database-heavy business logic
Correlation algorithms
PDF layout logic
Hashing loops
Complex forensic analysis
```

Bad:

```python
@router.post("/parse")
def parse():
    # Hundreds of lines of forensic parsing
```

Preferred:

```python
@router.post("/parse")
def parse():
    return evidence_service.process(...)
```

---

# 8. Service Layer Rules

Application services coordinate business workflows.

Services may call:

```text
Repositories
Domain services
Forensic processors
Hashing service
Reporting service
Job service
```

Services must not become giant "god classes."

Prefer small services with clear responsibilities.

Examples:

```text
CaseService
EvidenceService
HashingService
CustodyService
ArtifactService
TimelineService
CorrelationService
FindingService
ReportService
AuditService
JobService
```

---

# 9. Forensic Layer Independence

The forensic layer must remain as independent from FastAPI as practical.

A parser should be runnable from:

```text
Unit tests
CLI
Application services
Background jobs
```

without requiring an HTTP request.

---

# 10. Evidence Handling — Absolute Rules

These are non-negotiable.

## Rule 10.1 — Never Modify Original Evidence

The application must never:

```text
Edit
Rewrite
Normalize
Rename
Compress
Re-encode
Delete
Overwrite
```

an original evidence file.

---

## Rule 10.2 — Original Evidence Is Read-Only

Treat original evidence as:

```text
READ_ONLY
```

All analysis must operate against a read-only source.

---

## Rule 10.3 — Derived Data Must Be Separate

Parser output, normalized events, findings, reports, and indexes are derived data.

They must never overwrite the source evidence.

---

## Rule 10.4 — Never Silently Repair Evidence

If an artifact is malformed:

```text
Do not silently repair it.
```

Instead:

```text
Record error/warning
Continue where safe
Preserve original evidence
Document what happened
```

---

# 11. Hashing Rules

SHA-256 is the primary evidence integrity hash for MVP.

Hashing must:

- Use streaming reads.
- Avoid loading huge files entirely into memory.
- Record the algorithm.
- Record the resulting digest.
- Record when hashing occurred.
- Associate the digest with the evidence ID.

Example:

```text
Evidence:
EVD-001

Algorithm:
SHA-256

Digest:
<digest>

Status:
VERIFIED
```

---

# 12. Hash Mismatch Rules

When recalculated evidence does not match its recorded hash:

```text
Do NOT overwrite the original hash.
Do NOT automatically "fix" the record.
Do NOT mark the evidence verified.
```

Instead:

```text
Status → MISMATCH
```

and record an audit event.

---

# 13. Chain of Custody Rules

Chain of custody is forensic evidence handling data.

It must remain separate from application audit logs.

### Chain of custody:

```text
Evidence
→ Received
→ Stored
→ Transferred
→ Analyzed
→ Exported
```

### Application audit:

```text
User created case
User added evidence
Parser started
Parser completed
Report generated
```

Do not merge these concepts merely to simplify the database.

---

# 14. Provenance Rules

Every derived forensic result must retain provenance whenever technically possible.

Minimum desired relationship:

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

A result without provenance should never be presented as fully traceable.

---

# 15. No Fabricated Forensic Data

Codex must never create fake:

```text
Timestamps
Users
Paths
Event IDs
Registry values
Hashes
Artifact values
Evidence
Findings
Confidence
```

for the purpose of making the UI appear complete.

Development fixtures must be clearly labeled:

```text
DEMO
SYNTHETIC
TEST
FIXTURE
```

and must never be presented as real forensic evidence.

---

# 16. Uncertainty Rules

Unknown information must remain unknown.

Use:

```text
UNKNOWN
NOT_AVAILABLE
NOT_PARSED
UNVERIFIED
UNSUPPORTED
```

where appropriate.

Do not replace missing values with:

```text
null → guessed value
missing timezone → UTC
missing user → SYSTEM
missing timestamp → current time
```

unless the source explicitly justifies that transformation.

---

# 17. Timestamp Rules

Every normalized timeline event should retain:

```text
Original Timestamp
Normalized UTC Timestamp
Timezone / Offset
Timestamp Precision
Timezone Status
```

Do not discard the original representation.

---

# 18. Timezone Rules

Acceptable status:

```text
KNOWN
UNKNOWN
```

An explicit timezone may be normalized to UTC.

An unknown timezone must remain unknown.

Do not silently assume:

```text
UTC
Local machine time
IST
Windows local time
```

without evidence.

---

# 19. Timestamp Interpretation Rules

Normalization is not alteration.

The system may transform:

```text
2026-09-07 15:00:00 +05:30
```

into:

```text
2026-09-07T09:30:00Z
```

for timeline ordering.

But the original timestamp must remain available.

---

# 20. Forensic Conclusion Rules

The system must distinguish:

```text
Evidence
Observation
Correlation
Inference
Examiner Conclusion
```

Never collapse them into one concept.

Example:

BAD:

```text
Timestomping detected.
```

Preferred:

```text
Potential timestamp anomaly observed.

Confidence: LOW

Reason:
Timestamp relationships are unusual and require
examiner validation.
```

---

# 21. Confidence Rules

Confidence describes how strongly the available evidence supports a correlation or analytical observation.

Confidence does NOT mean:

```text
Probability the suspect is guilty
Probability malware exists
Legal certainty
```

Never present heuristic confidence as proof.

---

# 22. Severity Rules

Severity and confidence must remain independent.

Example:

```text
Severity: HIGH
Confidence: LOW
```

is valid.

It means:

> The potential significance is high, but the available evidence is insufficient for a strong conclusion.

---

# 23. Correlation Rules

Correlation must be deterministic and explainable for MVP.

Each rule must define:

```text
Rule ID
Rule name
Trigger conditions
Time window
Required conditions
Severity
Confidence logic
Explanation
Related events
Limitations
```

---

# 24. Correlation Engine Restrictions

The correlation engine must not:

- Invent missing events.
- Modify source timestamps.
- Claim maliciousness without evidence.
- Automatically declare an attack.
- Automatically attribute activity to a person.
- Produce findings with no supporting events.

Every finding must reference its supporting events.

---

# 25. Parser Rules

Every parser must:

1. Declare its name.
2. Declare its version.
3. Validate input where practical.
4. Parse only supported formats.
5. Preserve provenance.
6. Report malformed input.
7. Avoid modifying source evidence.
8. Produce structured output.
9. Have automated tests.

---

# 26. Parser Interface Rules

All parsers should follow a common interface.

Conceptual structure:

```python
class ArtifactParser:
    parser_name: str
    parser_version: str

    def can_parse(self, source):
        ...

    def parse(self, source):
        ...
```

The exact implementation may use:

```text
ABC
Protocol
Strategy pattern
```

as long as the contract remains clear.

---

# 27. Parser Failure Rules

A single malformed record must not necessarily destroy an entire processing operation.

Prefer:

```text
Successful Records
+
Warnings
+
Failed Records
```

rather than:

```text
One bad record
→ Entire case fails
```

unless continuing would make the output unsafe or misleading.

---

# 28. Partial Parsing Rules

If a parser successfully extracts:

```text
12,481 records
```

but fails on:

```text
3 records
```

the result should communicate that fact.

Do not report:

```text
12,484 successfully parsed
```

---

# 29. Library Selection Rules

Use mature, focused libraries where they reduce implementation risk.

Preferred MVP tooling:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
PostgreSQL
pytest
python-evtx
python-registry
LnkParse3
Appropriate Prefetch parser
pytsk3 / Sleuth Kit where appropriate
ReportLab
React
TypeScript
Vite
Tailwind CSS
shadcn/ui
TanStack Query
React Router
Recharts
```

Library versions must be verified before installation.

---

# 30. Dependency Philosophy

Prefer:

```text
One mature library
```

over:

```text
Five overlapping libraries
```

Do not add a dependency merely because it is convenient for one small function.

---

# 31. Do Not Duplicate Established Parsers

Do not write custom implementations of complex forensic formats when a reliable library already provides the required functionality.

Examples:

```text
EVTX
NTFS
LNK
Registry
```

Use established libraries where they satisfy the MVP requirement.

Custom code should focus on:

```text
Integration
Normalization
Correlation
Provenance
Investigation workflow
```

rather than recreating mature forensic parsers.

---

# 32. Dependency Verification

Before adopting a new dependency, Codex should verify:

```text
Is it actively maintained?
Does it support the required Python version?
Is the license compatible?
Does it actually provide the required functionality?
Does it introduce unnecessary dependencies?
Does it work on the intended development environment?
```

Do not blindly trust package names or README descriptions.

---

# 33. Avoid Abandoned Libraries

If a proposed library appears:

```text
Unmaintained
Broken
Incompatible
Poorly documented
Unsafe
```

do not automatically integrate it.

Instead:

```text
Research alternative
Evaluate implementation cost
Prefer the smallest reliable solution
```

---

# 34. No Dependency Sprawl

Do not add packages for features that can be handled cleanly by the standard library.

Examples:

```text
hashlib
pathlib
datetime
json
sqlite3
logging
uuid
typing
```

Use Python standard-library functionality where appropriate.

---

# 35. Database Rules

Use PostgreSQL for structured application data.

SQLAlchemy is the ORM/database abstraction.

Alembic is mandatory for schema migrations.

Do not modify database structure manually in development without creating the corresponding migration.

---

# 36. Migration Rules

Every schema change must be represented by an Alembic migration.

Never rely on:

```text
Auto-create tables on startup
```

as the long-term schema management strategy.

---

# 37. ORM Rules

Keep ORM models focused on persistence.

Do not place large forensic algorithms inside SQLAlchemy models.

Avoid:

```python
class TimelineEvent:
    def_detect_attacker():
        ...
```

Prefer:

```text
TimelineEvent
+
TimelineService
+
CorrelationEngine
```

---

# 38. Raw SQL Rules

SQLAlchemy ORM/Core should be preferred.

Raw SQL is allowed when it materially improves:

```text
Performance
Complexity
Database-specific functionality
```

but must be parameterized.

Never construct SQL with string concatenation from user input.

---

# 39. File Storage Rules

Raw evidence is stored outside PostgreSQL.

The database stores:

```text
Evidence ID
Metadata
Path/reference
Hash
Status
```

The filesystem stores:

```text
Actual evidence
Reports
Exports
```

---

# 40. Path Validation

All paths originating from users or evidence metadata must be validated.

Prevent:

```text
../
..\
absolute path escape
unexpected symlink traversal
```

The application must keep evidence processing inside approved storage boundaries.

---

# 41. Evidence Filename Rules

Never use an uploaded filename directly as a trusted filesystem path.

Use controlled generated storage locations.

Conceptually:

```text
Evidence ID
    ↓
Controlled directory
    ↓
Stored source
```

---

# 42. Evidence Execution Rules

The platform must never execute evidence.

Never execute:

```text
.exe
.dll
.ps1
.bat
.cmd
.vbs
.js
.msi
```

from evidence as part of MVP processing.

Opening/parsing a file is not the same as executing it.

---

# 43. Subprocess Rules

External tools may be used only where justified.

When invoking an external process:

```text
Use argument arrays.
Do not use shell=True.
Validate inputs.
Use timeouts where appropriate.
Check exit codes.
Capture stderr.
Handle process failure.
```

Never construct shell commands by concatenating untrusted strings.

---

# 44. Error Handling Philosophy

Errors must be:

```text
Explicit
Actionable
Traceable
Non-destructive
```

Avoid:

```python
except Exception:
    pass
```

unless there is a documented reason.

---

# 45. Exception Handling

Catch specific exceptions whenever practical.

Bad:

```python
try:
    ...
except Exception:
    return []
```

This can convert a serious parser failure into an apparently successful empty result.

Preferred:

```text
Known parse error
→ Record warning/error
→ Continue if safe
```

Unexpected programming errors should remain visible during development.

---

# 46. API Error Responses

API errors should be structured.

Example:

```json
{
  "error": {
    "code": "EVIDENCE_NOT_FOUND",
    "message": "Evidence item was not found.",
    "details": {}
  }
}
```

Do not expose:

```text
Python stack traces
Database credentials
Filesystem internals
Secrets
```

to normal users.

---

# 47. Logging Rules

Application logging should record:

```text
Timestamp
Level
Operation
Case ID
Evidence ID
Job ID
Message
Error details where appropriate
```

Do not log:

```text
Passwords
API keys
Tokens
Entire evidence contents
Sensitive files unnecessarily
```

---

# 48. Audit Logging Rules

Important application actions must be auditable.

Examples:

```text
CASE_CREATED
EVIDENCE_ADDED
HASH_CALCULATED
HASH_VERIFIED
HASH_MISMATCH
PARSER_STARTED
PARSER_COMPLETED
PARSER_FAILED
CORRELATION_RUN
FINDING_CREATED
FINDING_UPDATED
REPORT_GENERATED
```

---

# 49. Frontend Security Rules

Never trust frontend validation alone.

All critical validation must occur on the backend.

Frontend validation is for:

```text
UX
Early feedback
```

Backend validation is for:

```text
Actual enforcement
```

---

# 50. Sensitive Data Rules

Never send evidence data to:

```text
Third-party analytics
Tracking services
External AI APIs
Unnecessary cloud APIs
```

unless explicitly added to the architecture and approved later.

MVP should not depend on external forensic processing services.

---

# 51. AI / Codex Rules

Codex is an implementation assistant, not the project's decision-maker.

Codex must:

```text
Read PRD.md
Read architecture.md
Read rules.md
Inspect existing code
Understand current state
Implement incrementally
Run tests
Review failures
Make minimal changes
```

Codex must not:

```text
Redesign the system without instruction
Expand scope automatically
Replace the architecture casually
Delete working functionality unnecessarily
Invent forensic behavior
Create fake data
Skip tests
Hide errors
```

---

# 52. Codex Must Inspect Before Editing

Before changing an existing module, Codex should inspect:

```text
Relevant source files
Related tests
Configuration
Database models
API contracts
Imports
Existing patterns
```

Never overwrite an existing implementation blindly.

---

# 53. Codex Must Prefer Incremental Changes

Prefer:

```text
Small change
→ Test
→ Review
→ Next change
```

over:

```text
Generate hundreds of files
→ Hope everything works
```

---

# 54. Codex Must Not Rewrite Working Architecture

Do not:

```text
Replace FastAPI with Django
Replace React with another framework
Replace PostgreSQL without justification
Replace SQLAlchemy
Rewrite entire frontend
Regenerate the repository
```

just because another implementation might look cleaner.

---

# 55. Codex Must Preserve Existing Functionality

When adding functionality:

```text
Existing behavior
        +
New behavior
```

must both work.

Do not solve one feature by breaking unrelated functionality.

---

# 56. Codex Must Ask Only When Necessary

Codex should make reasonable implementation decisions from:

```text
PRD.md
architecture.md
rules.md
existing code
```

It should not stop for trivial choices such as:

```text
Variable naming
Small component organization
Basic test naming
Straightforward implementation details
```

However, genuine architectural conflicts must not be silently resolved.

---

# 57. Codex Validation Loop

After each substantial implementation:

```text
Implement
   ↓
Run formatter/linter
   ↓
Run type checks
   ↓
Run unit tests
   ↓
Run integration tests where relevant
   ↓
Inspect git diff
   ↓
Fix failures
   ↓
Continue
```

---

# 58. Never Trust Generated Code Blindly

All Codex-generated forensic logic must be reviewed.

Particularly inspect:

```text
Parser behavior
Timestamp conversion
Hash calculation
File access
SQL queries
Path validation
Exception handling
Correlation rules
Confidence calculations
```

---

# 59. Forensic Code Requires Evidence-Based Validation

A parser is not considered correct because:

```text
It runs
```

It is correct only when:

```text
Known input
+
Expected forensic output
+
Automated test
```

match.

---

# 60. Testing Rule

Every major capability must have tests.

Required coverage:

```text
Case
Evidence
Hashing
Custody
Parser framework
Each parser
Timeline normalization
Timeline filtering
Correlation rules
Findings
Reporting
```

---

# 61. Do Not Reduce Tests to Make Them Pass

Never modify a test merely to accommodate incorrect implementation.

First determine:

```text
Is the code wrong?
Is the test wrong?
Is the requirement ambiguous?
```

Then resolve the actual issue.

---

# 62. Test Fixture Rules

Fixtures must be:

```text
Synthetic
Public
Legally distributable
Non-sensitive
Reproducible
```

Do not commit confidential forensic evidence.

---

# 63. Demo Data Rules

Demo data must be explicitly identified.

Example:

```text
data/samples/demo-case/
```

must be documented as:

```text
Synthetic laboratory evidence
```

Never present synthetic data as a real criminal or corporate investigation.

---

# 64. Test Determinism

Tests should be deterministic.

Avoid tests that depend on:

```text
Current time
Machine-specific paths
Internet availability
Random external state
External APIs
```

unless deliberately mocked.

---

# 65. Date and Time Testing

Include test cases for:

```text
UTC
Positive offsets
Negative offsets
Missing timezone
DST transitions where relevant
Equal timestamps
Different timestamp precision
Invalid timestamps
```

---

# 66. Correlation Testing

Every correlation rule must have at least:

```text
Positive case
Negative case
Boundary case
Insufficient evidence case
```

Example:

```text
USB + file activity
→ triggers

USB only
→ does not trigger

Events outside allowed time window
→ does not trigger
```

---

# 67. No False Success

Do not return success when an operation actually failed.

Bad:

```text
Parser failed
→ API returns "success"
```

Good:

```text
Parser completed with warnings
```

or:

```text
Parser failed
```

depending on actual state.

---

# 68. Processing Job Rules

Every parser operation should have an observable processing state.

Valid states:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
```

The system must not leave jobs indefinitely appearing to be running after failure.

---

# 69. Frontend Data Rules

Do not hardcode:

```text
Fake event counts
Fake findings
Fake hash values
Fake evidence records
Fake dashboard metrics
```

unless they are clearly loaded from a demo fixture.

Production UI values must come from the backend.

---

# 70. UI State Rules

Loading, empty, success, warning, and failure states must be distinguishable.

Example:

```text
Loading...
No evidence found.
Evidence found.
Parsing...
Parsing completed.
Parsing failed.
```

Do not display empty arrays as successful forensic analysis.

---

# 71. Report Integrity Rules

Generated reports must reflect actual database state at generation time.

Do not:

```text
Invent findings
Invent event counts
Invent evidence
Invent hash results
```

The report should identify what data was actually analyzed.

---

# 72. Report Methodology Rules

The report must not claim the examiner:

```text
Acquired a disk
Used FTK
Used Autopsy
Performed memory analysis
Recovered deleted files
```

unless the application actually performed or recorded those actions.

Never generate fictional methodology.

---

# 73. Report Conclusion Rules

The report's conclusion should be evidence-grounded.

Use wording such as:

```text
Observed
Identified
Indicated
Correlated
Potential
Consistent with
Requires further validation
```

when certainty is limited.

---

# 74. UI Language Rules

Avoid sensational or unsupported security language.

Avoid:

```text
HACKER DETECTED
ATTACK CONFIRMED
MALWARE FOUND
USER IS GUILTY
DATA WAS DEFINITELY STOLEN
```

unless the underlying feature and evidence genuinely support such a conclusion.

Prefer:

```text
Potential suspicious activity
Observed execution activity
Potential removable-media sequence
Timestamp anomaly indicator
Evidence requires examiner review
```

---

# 75. Performance Rules

Optimize only where needed.

First ensure:

```text
Correctness
Then
Reliability
Then
Maintainability
Then
Performance
```

Do not prematurely introduce:

```text
Caching layers
Distributed queues
Elasticsearch
Database sharding
```

for hypothetical scale.

---

# 76. Large File Handling

Evidence processing must use streaming or incremental processing where practical.

Do not use patterns like:

```python
data = evidence.read()
```

for arbitrarily large evidence files when streaming is possible.

---

# 77. Database Query Rules

Avoid N+1 query patterns in major endpoints.

Use appropriate:

```text
Indexes
Pagination
Eager loading
Aggregations
```

where justified.

Do not fetch millions of events simply to display the first page.

---

# 78. Timeline Pagination

Timeline APIs must be paginated.

The frontend must not request an entire massive timeline simply to render the first screen.

---

# 79. API Contract Stability

Once an API contract is used by the frontend:

```text
Do not casually break it.
```

If a breaking change is required:

```text
Update backend
Update frontend
Update tests
Update documentation
```

together.

---

# 80. Type Safety Rules

Use type hints throughout Python code.

Use TypeScript types/interfaces throughout the frontend.

Avoid:

```python
Any
```

unless genuinely necessary.

Avoid excessive:

```typescript
any
```

in TypeScript.

---

# 81. Naming Rules

Use clear names.

Prefer:

```text
TimelineEvent
EvidenceRecord
ProcessingJob
CorrelationFinding
```

over ambiguous names such as:

```text
Data
Info
Thing
Result2
Temp
```

---

# 82. Function Size Rules

Avoid enormous functions.

If a function is responsible for:

```text
File validation
Parsing
Database insertion
Correlation
Logging
```

all at once, split it.

---

# 83. Comments

Comments should explain:

```text
Why
```

rather than merely:

```text
What
```

Avoid comments such as:

```python
# increment i
i += 1
```

Useful comments explain forensic assumptions, format quirks, or deliberate security decisions.

---

# 84. Documentation Rules

Publicly meaningful components should have documentation.

Document:

```text
Parser purpose
Input format
Output format
Timestamp assumptions
Limitations
Known edge cases
```

---

# 85. Parser Documentation

Each parser should document:

```text
Supported files
Supported artifact versions
Extracted fields
Timestamp source
Known limitations
Dependencies
Test fixtures
```

---

# 86. No Hidden Behavior

Important transformations must be discoverable.

Do not silently:

```text
Change timestamps
Change severity
Change confidence
Drop events
Change paths
Normalize values
```

without recording or documenting the transformation.

---

# 87. Event Deletion Rules

Parsed forensic events must not be silently deleted because they appear uninteresting.

Filtering is a presentation/query concern.

Stored evidence-derived events should remain available unless an explicit data-retention feature is implemented later.

---

# 88. Finding Deletion Rules

Do not permanently delete findings merely because an analyst dismisses them.

Prefer:

```text
DISMISSED
```

with the original finding preserved.

---

# 89. Audit Event Immutability

Audit records should be append-oriented.

Avoid allowing routine UI operations to silently rewrite historical audit entries.

---

# 90. Versioning Rules

Parser output should identify:

```text
Parser Name
Parser Version
```

This helps explain why derived data may differ between software versions.

---

# 91. Reproducibility Rules

A demo investigation should be reproducible.

Given:

```text
Same evidence
+
Same application version
+
Same parser versions
+
Same rules
```

the resulting investigation should be substantially consistent.

---

# 92. Git Rules

Make focused commits.

Preferred:

```text
feat: add evidence model
feat: implement sha256 hashing
feat: add custody service
feat: add evtx parser
feat: add timeline normalization
feat: add correlation rules
feat: add report generator
test: add parser fixtures
```

Avoid giant commits such as:

```text
build entire application
```

---

# 93. Generated Code Review

Before accepting a large Codex change:

```text
Review git diff
Review changed files
Review database changes
Review dependencies
Review security-sensitive code
Review tests
```

Do not accept a generated change simply because:

```text
Build passes
```

---

# 94. No Destructive Commands

Codex must not use destructive commands without explicit necessity.

Avoid casual use of:

```text
rm -rf
git reset --hard
git clean -fd
database drop
database reset
```

especially when existing work may be lost.

---

# 95. Preserve User Work

Before major migrations or refactors:

```text
Inspect current git status
Inspect current diff
Understand existing changes
```

Do not delete uncommitted user work.

---

# 96. Environment Rules

Secrets belong in environment variables.

Never commit:

```text
.env
Passwords
API keys
Tokens
Private certificates
Credentials
```

Provide:

```text
.env.example
```

instead.

---

# 97. Dependency Locking

The final project should lock or constrain dependency versions sufficiently to make builds reproducible.

Do not rely on:

```text
latest
```

for production dependency installation.

---

# 98. Internet Dependency Rules

Runtime MVP behavior should not require internet access.

The system should work with:

```text
Local evidence
Local database
Local parsers
Local report generator
```

after dependencies have been installed.

---

# 99. External AI Rules

The forensic application itself must not depend on external AI APIs for core forensic conclusions.

AI may be used during development assistance.

The resulting application should remain functional without an AI service.

---

# 100. Future Feature Rules

When adding future modules such as:

```text
Malware Triage
Steganography
Anti-Forensics
Memory Forensics
Network Forensics
```

they must integrate through the existing forensic architecture.

Do not create separate unrelated applications inside the same repository.

---

# 101. Malware Future-Phase Safety

When malware triage is later implemented:

```text
Static analysis first.
```

Do not add malware execution to the core platform casually.

Any future dynamic execution environment must be separately designed and isolated.

---

# 102. Steganography Future-Phase Rule

The future steganography module is an analysis/steganalysis component.

Its primary purpose is:

```text
Detection
Analysis
Evidence interpretation
Reporting
```

not an arbitrary payload-hiding utility.

---

# 103. Anti-Forensics Future-Phase Rule

Anti-forensics detection should produce:

```text
Indicators
Anomalies
Evidence relationships
Confidence
```

not unsupported definitive accusations.

---

# 104. Architecture Change Rule

An architecture change requires a reason.

Before introducing a major architectural change, document:

```text
Current limitation
Proposed change
Benefits
Costs
Alternatives
Impact on PRD
Impact on existing code
```

Do not replace architecture for stylistic preference.

---

# 105. New Library Rule

Before adding a dependency, answer:

```text
1. What problem does it solve?
2. Why can't the current stack solve it?
3. Is the library mature?
4. Is it compatible?
5. Is its license acceptable?
6. Does it increase maintenance burden?
7. Does it work in the local/offline design?
```

If these questions cannot be answered, do not add it automatically.

---

# 106. Feature Completion Rule

A feature is only complete when:

```text
Implemented
+
Integrated
+
Tested
+
Error-handled
+
Documented
```

A UI placeholder does not count.

A parser stub does not count.

A hardcoded demo result does not count.

---

# 107. "Done" Is Not "Build Passes"

The following are insufficient:

```text
npm run build passes
pytest passes
API starts
UI renders
```

A feature must also perform its intended real behavior.

---

# 108. Review Before Expansion

Before starting a new feature, verify:

```text
Current feature works
Tests pass
No major regressions
Architecture remains consistent
Scope remains within PRD
```

Only then move forward.

---

# 109. Priority Rule

When time is limited, prioritize:

```text
1. Forensic correctness
2. Evidence integrity
3. Provenance
4. Core workflow
5. Reliability
6. Testing
7. Usability
8. Visual polish
9. Optional features
```

Do not sacrifice forensic correctness for UI polish.

---

# 110. Two-Week MVP Rule

The project is being developed as a focused portfolio MVP.

If a feature threatens the 14-day target:

```text
Reduce scope.
Do not reduce integrity.
```

Example:

GOOD:

```text
Support 5 high-value artifact families well.
```

BAD:

```text
Support 15 artifact families poorly.
```

---

# 111. Breadth vs Depth Rule

For MVP:

```text
Fewer reliable parsers
>
Many unreliable parsers
```

The project should demonstrate deep understanding of the investigation workflow.

---

# 112. Portfolio Quality Rule

The project must be defensible during an interview.

For every major feature, the developer should be able to explain:

```text
What it does
Why it exists
What evidence it uses
How it works
What assumptions it makes
What its limitations are
How it was tested
```

Codex-generated functionality that cannot be explained should be reviewed before inclusion.

---

# 113. No "Magic AI" Rule

Do not market deterministic forensic rules as:

```text
AI-powered forensic intelligence
```

unless a real AI/ML component is later implemented and documented.

For MVP, call the system:

```text
Rule-based correlation
```

or:

```text
Evidence correlation
```

---

# 114. No Fake Accuracy

Never claim:

```text
99% malware detection
98% forensic accuracy
100% attack detection
```

unless supported by a properly designed evaluation.

---

# 115. Demo Rules

The demonstration should tell a coherent forensic story.

Recommended sequence:

```text
Create Case
→ Add Evidence
→ Verify Hash
→ Parse Artifacts
→ Open Timeline
→ Find Related Events
→ Review Correlation
→ Inspect Provenance
→ Generate Report
```

The demo should show actual data flowing through the system.

---

# 116. Documentation Hierarchy

The repository should maintain:

```text
PRD.md
    ↓
Product requirements

architecture.md
    ↓
Technical design

rules.md
    ↓
Implementation constraints

README.md
    ↓
Developer/user-facing overview

docs/
    ↓
Detailed supporting documentation
```

---

# 117. Final AI Rule

Codex must behave as a disciplined senior software engineer working under a forensic specification.

It must prioritize:

```text
Correctness
Safety
Traceability
Maintainability
Simplicity
Testability
```

over:

```text
Speed at any cost
Feature count
Visual complexity
Novel architecture
Unnecessary dependencies
```

---

# 118. Final Forensic Rule

The platform follows this principle:

```text
RAW EVIDENCE
     ↓
OBSERVATION
     ↓
NORMALIZATION
     ↓
CORRELATION
     ↓
FINDING
     ↓
EXAMINER REVIEW
     ↓
CONCLUSION
```

Never reverse this process.

The application must never decide the conclusion first and then manufacture or selectively present evidence to support it.

---

# 119. Final Development Rule

When uncertain, choose the implementation that is:

```text
More explicit
More traceable
Less destructive
Less magical
Easier to test
Easier to explain
Easier to replace
```

---

# 120. Final Command to Codex

Before every significant implementation task:

```text
1. Read PRD.md.
2. Read architecture.md.
3. Read rules.md.
4. Inspect the current repository.
5. Identify relevant existing code.
6. Implement the smallest correct change.
7. Preserve evidence integrity.
8. Preserve provenance.
9. Add or update tests.
10. Run relevant validation.
11. Review the resulting diff.
12. Do not expand scope without explicit instruction.
```

The project should evolve incrementally, with each change leaving the system in a working and explainable state.

---

# 121. Governing Principle

> **Build a forensic investigation system, not a collection of impressive-looking features.**

Every implementation decision should improve the path:

```text
Evidence
   ↓
Trust
   ↓
Understanding
   ↓
Correlation
   ↓
Finding
   ↓
Report
```

That is the standard against which the project should be evaluated.
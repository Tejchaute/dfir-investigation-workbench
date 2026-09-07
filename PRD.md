# Product Requirements Document (PRD)

# DFIR Investigation Workbench

**Document:** PRD.md  
**Version:** 1.0  
**Status:** Approved for MVP Planning  
**Target MVP Duration:** 14 days  
**Primary Implementation Agent:** OpenAI Codex  
**Primary Developer:** Solo developer  
**Product Type:** Local-first Digital Forensics / DFIR investigation platform

---

# 1. Product Overview

## 1.1 Product Name

**DFIR Investigation Workbench**

Working name for the project.

The product is a modular digital forensic investigation platform designed to help an examiner collect, preserve, analyze, correlate, visualize, and report forensic evidence from Windows systems.

The MVP combines three major capabilities:

1. **Evidence Triage**
2. **Timeline Reconstruction**
3. **Investigation Reporting**

A lightweight **Correlation Engine** connects these three capabilities by identifying relationships between forensic events and producing evidence-backed findings.

The platform is not intended to replace mature forensic suites such as Autopsy, FTK, EnCase, or commercial DFIR products.

The goal is to demonstrate a practical, technically credible forensic investigation workflow that can be extended over time.

---

# 2. Product Vision

The long-term vision is to create a modular DFIR workbench in which multiple forensic analysis capabilities operate around a shared case, evidence, timeline, and reporting model.

The architecture must therefore support future modules without requiring a redesign of the core system.

Long-term platform direction:

```text
                    DFIR INVESTIGATION WORKBENCH
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
    Evidence Triage      Timeline Engine      Reporting
          |                   |                   |
          +-------------------+-------------------+
                              |
                       Correlation Engine
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
       Malware Triage   Steganography   Anti-Forensics
                          Analysis          Detection
```

Only the first four components are part of the MVP.

Future modules must be able to consume the same normalized evidence and timeline models.

---

# 3. Problem Statement

Digital forensic investigations frequently require an examiner to work across many artifacts, parsers, analysis utilities, spreadsheets, timelines, and reporting tools.

This creates several problems:

- Evidence metadata becomes fragmented.
- Artifact findings are difficult to correlate.
- Timeline events come from different timestamp formats and sources.
- Important relationships between artifacts may be missed.
- Investigation notes and findings can become disconnected from their underlying evidence.
- Reporting requires manually collecting information from multiple tools.

The DFIR Investigation Workbench addresses this by providing a unified workflow:

```text
Evidence
   ↓
Integrity Verification
   ↓
Artifact Identification
   ↓
Artifact Parsing
   ↓
Normalized Events
   ↓
Unified Timeline
   ↓
Correlation
   ↓
Findings
   ↓
Investigator Review
   ↓
Forensic Report
```

---

# 4. Target Users

## 4.1 Primary User — Digital Forensic Examiner

A forensic examiner investigating a Windows endpoint or collection of forensic artifacts.

Typical activities:

- Review evidence metadata.
- Verify evidence hashes.
- Examine Windows artifacts.
- Reconstruct activity timelines.
- Identify suspicious sequences.
- Document findings.
- Produce a case report.

---

## 4.2 Secondary User — DFIR / Incident Response Analyst

An analyst performing endpoint triage during a security investigation.

Typical activities:

- Rapidly ingest available artifacts.
- Identify suspicious activity.
- Search events.
- Correlate activity across multiple artifacts.
- Export findings for investigation documentation.

---

## 4.3 Secondary User — Cybersecurity Student / Junior Analyst

A learner who wants to understand the relationship between Windows forensic artifacts and incident timelines.

The UI should therefore expose the source of a finding rather than hiding the forensic reasoning behind a black-box score.

---

## 4.4 Non-Target Users

The MVP is not designed for:

- Large enterprise SOC deployments.
- Multi-tenant SaaS environments.
- Cloud-scale evidence processing.
- Court-certified forensic acquisition.
- Automated legal conclusions.
- Real-time endpoint monitoring.
- Malware execution or sandboxing.

---

# 5. Product Goals

## 5.1 Primary Goals

The MVP must:

1. Allow an examiner to create and manage forensic cases.
2. Allow evidence items to be registered against a case.
3. Calculate and store evidence integrity hashes.
4. Maintain chain-of-custody information.
5. Ingest selected Windows forensic artifacts.
6. Parse those artifacts through modular parser components.
7. Convert parser output into a common timeline-event model.
8. Normalize timestamps consistently.
9. Display events through a searchable and filterable timeline.
10. Correlate selected event patterns.
11. Create evidence-backed findings.
12. Generate a structured forensic PDF report.
13. Preserve provenance between findings and source evidence.
14. Provide a clean extension point for future forensic modules.

---

# 6. Non-Goals for MVP

The following are explicitly excluded from the 14-day MVP.

## 6.1 Full Forensic Suite Replacement

The project must not attempt to become a replacement for Autopsy, FTK, EnCase, X-Ways, or Plaso.

---

## 6.2 Complete Windows Artifact Coverage

The MVP will not support every Windows artifact.

The first release will intentionally support a small set of high-value artifact families.

---

## 6.3 Malware Execution

The platform must never execute suspicious binaries as part of the MVP.

Future malware analysis must initially remain static-analysis-oriented.

---

## 6.4 Machine Learning Correlation

No ML-based threat detection or anomaly detection is required for MVP.

---

## 6.5 Enterprise Authentication and Authorization

Complex RBAC, SSO, OAuth, MFA, tenant management, and enterprise identity infrastructure are outside MVP scope.

A local single-examiner workflow is sufficient.

---

## 6.6 Cloud Evidence Storage

Evidence must remain local during MVP.

No dependency on AWS S3, Azure Blob Storage, GCP Storage, or other cloud storage is required.

---

## 6.7 Kubernetes / Distributed Processing

No Kubernetes cluster, microservice deployment, or distributed processing architecture is required.

---

## 6.8 Full Disk Forensic Acquisition

The platform does not acquire evidence from live systems.

It analyzes already-created forensic evidence or exported artifact collections.

---

# 7. MVP Scope

The MVP consists of the following modules.

```text
MVP
│
├── Case Management
├── Evidence Management
├── Evidence Integrity
├── Chain of Custody
├── Artifact Detection / Ingestion
│   ├── EVTX
│   ├── Registry
│   ├── Prefetch
│   ├── LNK
│   └── NTFS / MFT Metadata
├── Timeline Engine
├── Correlation Engine
├── Findings
├── Investigation Dashboard
└── PDF Reporting
```

---

# 8. Core User Workflow

The intended investigator workflow is:

```text
1. Create Case
        ↓
2. Add Evidence
        ↓
3. Calculate SHA-256
        ↓
4. Record Acquisition / Custody Metadata
        ↓
5. Inspect Evidence
        ↓
6. Run Artifact Parsers
        ↓
7. Generate Normalized Timeline Events
        ↓
8. Review Timeline
        ↓
9. Run Correlation Rules
        ↓
10. Review Findings
        ↓
11. Add Examiner Notes
        ↓
12. Generate Investigation Report
```

The workflow must be understandable without requiring the user to know the internal software architecture.

---

# 9. Functional Requirements

# 9.1 Case Management

The system shall allow an examiner to:

- Create a case.
- View existing cases.
- Open a case.
- Edit case metadata.
- Close/archive a case.
- View case statistics.

A case should contain:

```text
Case ID
Case Name
Description
Investigator
Status
Created At
Updated At
Notes
```

Supported case states:

```text
OPEN
IN_REVIEW
CLOSED
ARCHIVED
```

---

# 9.2 Evidence Management

Each case can contain multiple evidence items.

The examiner shall be able to:

- Add an evidence item.
- Assign a unique evidence ID.
- Record evidence type.
- Record original filename.
- Record acquisition metadata.
- Record source path.
- Record description.
- Record collector.
- Calculate SHA-256.
- View hash verification status.
- View evidence processing status.
- View chain-of-custody history.

Example evidence types:

```text
DISK_IMAGE
EVTX
REGISTRY_HIVE
PREFETCH
LNK
EVIDENCE_DIRECTORY
OTHER
```

The system must not modify original evidence files.

---

# 9.3 Evidence Integrity

The application must calculate SHA-256 hashes for evidence files.

The system must store:

```text
Algorithm
Hash
Hash Calculation Timestamp
Evidence ID
Verification Status
```

Example:

```text
Algorithm: SHA-256
Digest:
8e0c...ab7f
Status:
VERIFIED
```

The application should support recalculating the hash and comparing the result with the originally recorded digest.

Possible states:

```text
NOT_VERIFIED
VERIFIED
MISMATCH
```

A hash mismatch must be prominently surfaced.

---

# 9.4 Chain of Custody

The system must provide an append-oriented chain-of-custody record for each evidence item.

The record should capture at minimum:

```text
Entry ID
Evidence ID
Timestamp
Person / Examiner
Action
Location
Notes
```

Typical actions:

```text
ACQUIRED
RECEIVED
TRANSFERRED
STORED
HASH_VERIFIED
ANALYZED
EXPORTED
REPORTED
```

The chain-of-custody history must be displayed chronologically.

The underlying report design should preserve traceability of evidence handling; chain-of-custody records are an important part of demonstrating evidence continuity.

---

# 9.5 Artifact Processing

The MVP will contain a modular parser framework.

Each parser must have a predictable lifecycle:

```text
Input
 ↓
Validate
 ↓
Parse
 ↓
Normalize
 ↓
Emit Artifact Records
 ↓
Emit Timeline Events
 ↓
Persist Provenance
```

The parser framework must allow additional parsers to be added later without rewriting the timeline system.

---

# 10. MVP Artifact Support

## 10.1 Windows Event Logs — EVTX

Priority: **Critical**

Supported initial inputs:

```text
*.evtx
```

Initial channels:

- Security
- System
- PowerShell Operational

The parser should extract useful event-level information such as:

```text
Record ID
Event ID
Channel
Provider
Timestamp
Computer
User
Message / Rendered Data
Event XML reference
```

The parser must preserve raw or source-specific fields where practical.

The resulting normalized events must reference the originating EVTX evidence item.

---

# 10.2 Windows Registry

Priority: **Critical**

Initial hive support:

```text
NTUSER.DAT
SYSTEM
SOFTWARE
```

Initial artifact areas:

```text
Run Keys
USBSTOR
MountedDevices
UserAssist
ShellBags
```

Registry parsing must be read-only.

The system must preserve:

```text
Hive
Registry Path
Value Name
Value Data
Last Write Time
Source Evidence
```

The selected Registry areas provide enough breadth for meaningful Windows forensic demonstrations without attempting complete Registry coverage.

The chosen read-only approach is consistent with forensic handling of offline Registry hives.

---

# 10.3 Prefetch

Priority: **High**

Initial extraction should include:

```text
Executable Name
Execution Timestamps
Run Count
Referenced Files / DLLs where available
Source File
```

Prefetch events should contribute execution-related events to the timeline.

---

# 10.4 LNK Files

Priority: **High**

The parser should extract available information including:

```text
Target Path
Creation Time
Modification Time
Access Time
Volume Information
Target Metadata
Source File
```

LNK-derived timeline events must retain provenance back to the originating `.lnk` file.

---

# 10.5 NTFS / MFT Metadata

Priority: **High**

The MVP must not attempt to implement a custom NTFS filesystem parser.

Use an established forensic library layer where practical.

The MVP should extract a useful subset of filesystem metadata:

```text
Path
Filename
Size
MFT Record / Identifier where available
Created Time
Modified Time
Accessed Time
Metadata Changed Time where available
Deleted State where available
Source Evidence
```

The platform is using filesystem metadata for timeline and triage purposes, not implementing a replacement for The Sleuth Kit.

---

# 11. Deferred Artifact Support

The following may be added after MVP:

```text
Browser History
Recycle Bin
Scheduled Tasks
Additional Registry artifacts
Windows Defender artifacts
WMI artifacts
SRUM
Amcache
Shimcache
Jump Lists
ShellBags expansion
Sysmon
Additional NTFS structures
VSS analysis
ESE databases
```

The original research report identified many of these as possible artifact sources, but implementing all of them during the initial sprint would make the MVP too broad.

---

# 12. Timeline Reconstruction

The timeline engine is one of the most important components of the product.

Its responsibility is to transform events produced by multiple artifact parsers into a consistent investigation timeline.

The conceptual model is:

```text
EVTX -----------\
Registry --------\
Prefetch ---------\
LNK ---------------> Normalized Timeline
MFT --------------/
                   \
                    → Correlation
```

Autopsy's timeline model is also event-oriented, where an event has a timestamp, type, and description. The project adopts the same general event-centric design without attempting to replicate Autopsy.

---

# 13. Timeline Event Requirements

Every normalized event should contain at minimum:

```text
Event ID
Case ID
Evidence ID
Timestamp UTC
Original Timestamp
Timezone / Offset
Event Type
Artifact Type
Source
Description
User
Path / Filename where applicable
Metadata
Parser Name
Parser Version
Source Reference
Confidence
```

Example:

```json
{
  "event_id": "EVT-000184",
  "case_id": "CASE-2026-001",
  "evidence_id": "EVD-004",
  "timestamp_utc": "2026-09-07T10:23:45Z",
  "original_timestamp": "2026-09-07T15:53:45+05:30",
  "event_type": "PROCESS_EXECUTION",
  "artifact_type": "PREFETCH",
  "source": "C:\\Windows\\Prefetch\\POWERSHELL.EXE-123.pf",
  "user": null,
  "description": "PowerShell execution observed through Prefetch",
  "confidence": "MEDIUM"
}
```

---

# 14. Timestamp Handling

The system must distinguish between:

```text
Original Artifact Timestamp
Normalized UTC Timestamp
Timezone / Offset Information
```

The original value must never be silently discarded.

All sortable timeline events should have a normalized UTC representation.

For timestamps where timezone information is unavailable, the system must mark the timezone as:

```text
UNKNOWN
```

rather than inventing a timezone.

Timestamp conversion is for normalization and ordering. It must not automatically modify the underlying forensic evidence.

The research design explicitly emphasizes retaining original timestamp information while normalizing timeline values to UTC/ISO 8601.

---

# 15. Timeline Features

The UI must support:

- Chronological event list.
- Time-range filtering.
- Artifact-type filtering.
- Event-type filtering.
- Keyword search.
- User filtering where available.
- Severity/finding filtering.
- Event detail inspection.
- Source/provenance inspection.

Optional visualizations:

```text
Event count by time
Events by artifact
Events by type
Finding density
```

The user must be able to click an event and inspect its source data.

---

# 16. Correlation Engine

The correlation engine connects individual timeline events into higher-level investigative findings.

It must use deterministic, transparent rules.

The system should not present heuristic correlations as confirmed facts.

---

# 17. Correlation Rule Model

Each rule should define:

```text
Rule ID
Rule Name
Description
Required Event Types
Time Window
Conditions
Severity
Confidence Calculation
Explanation
```

Example:

```text
Rule:
USB_ACTIVITY_SEQUENCE

Trigger:
USB connection event

Then:
File activity occurs within configured time window

Then:
Additional suspicious file activity occurs

Result:
Potential removable-media activity sequence

Confidence:
Calculated from observed conditions
```

---

# 18. Initial Correlation Rules

The MVP should contain a small number of high-value rules.

## Rule 1 — Removable Media Activity

Potential pattern:

```text
USB-related activity
        ↓
File activity
        ↓
Additional file modification/deletion activity
```

This should create a finding only when sufficient supporting events exist.

---

## Rule 2 — PowerShell Activity Sequence

Potential pattern:

```text
PowerShell execution
        ↓
File activity
```

The finding should state that the sequence is noteworthy rather than declaring malicious behavior.

---

## Rule 3 — Execution + Artifact Activity

Potential pattern:

```text
Executable execution evidence
        ↓
Related file activity
```

This is designed to demonstrate cross-artifact correlation.

---

## Rule 4 — Timestamp Anomaly Indicator

Potential pattern:

```text
Unusual timestamp relationships
```

This must be labeled as an anomaly indicator.

The system must not claim:

```text
Timestomping detected.
```

It should instead use wording such as:

```text
Potential timestamp anomaly requiring examiner validation.
```

This distinction is mandatory.

---

# 19. Confidence Model

The system may use confidence values such as:

```text
LOW
MEDIUM
HIGH
```

or:

```text
0–100
```

The confidence represents the confidence in the **correlation rule**, not proof that malicious activity occurred.

Every finding must explain:

```text
Why it triggered
Which events support it
Which evidence items support those events
What limitations apply
```

---

# 20. Findings

A finding is a human-reviewable investigative observation created from one or more forensic events.

Each finding should contain:

```text
Finding ID
Case ID
Title
Description
Severity
Confidence
Status
Created At
Related Events
Related Evidence
Rule ID
Analyst Notes
Conclusion / Assessment
```

Finding status:

```text
NEW
UNDER_REVIEW
CONFIRMED
DISMISSED
```

The application must allow the examiner to change the status manually.

---

# 21. Severity Model

Use:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Severity and confidence are separate concepts.

Example:

```text
Severity: HIGH
Confidence: MEDIUM
```

means:

> The potential impact is significant, but the evidence correlation is not sufficiently strong to treat it as established fact.

This distinction should be reflected throughout the UI and reports.

---

# 22. Evidence Provenance

Every derived object must maintain traceability.

The minimum chain should be:

```text
Finding
   ↓
Timeline Event
   ↓
Parser Result
   ↓
Source Evidence
   ↓
Evidence Hash
```

The examiner should be able to navigate from a finding to its supporting events and evidence.

This is one of the most important characteristics of the platform.

---

# 23. Investigation Notes

The examiner must be able to add notes to:

- Case
- Evidence
- Timeline event
- Finding

Notes should include:

```text
Author
Timestamp
Content
```

Notes should be append-oriented where practical.

---

# 24. Reporting

The reporting module must generate a professional PDF investigation report.

The report should contain:

## Title Page

```text
Case Name
Case ID
Investigator
Report Date
Report Version
```

---

## Executive Summary

Summary of:

```text
Case purpose
Evidence examined
Major findings
Overall assessment
```

---

## Methodology

Describe:

```text
Evidence handling
Hashing
Artifact parsing
Timeline reconstruction
Correlation
Reporting
```

The report must avoid claiming procedures that were not actually performed.

---

## Evidence Inventory

For each evidence item:

```text
Evidence ID
Filename
Type
Size
SHA-256
Collection metadata
Status
```

---

## Chain of Custody

Include chronological custody entries.

---

## Timeline Summary

Include:

```text
Time range
Event count
Major event categories
Important event sequence(s)
```

---

## Notable Events

List selected events with:

```text
Event ID
Timestamp
Artifact
Description
Source
Related evidence
```

---

## Findings

For each finding:

```text
Finding ID
Title
Severity
Confidence
Reason
Supporting Events
Supporting Evidence
Assessment
Examiner Notes
```

---

## Conclusion

The conclusion must be based only on the evidence represented inside the report.

It must not overstate heuristic findings.

---

## Appendices

Optional:

```text
Detailed event tables
Parser summary
Evidence hash verification
Additional evidence references
```

---

# 25. Frontend Requirements

The frontend should be designed as an investigator-focused interface.

The UI should prioritize:

```text
Clarity
Traceability
Fast navigation
Dense information presentation
Readable forensic data
```

It should not look like a generic SaaS dashboard.

---

# 26. Required Screens

## 26.1 Case Dashboard

Display:

```text
Cases
Status
Evidence Count
Event Count
Finding Count
Last Updated
```

Actions:

```text
Create Case
Open Case
Search Cases
```

---

## 26.2 Case Overview

Display:

```text
Case information
Evidence count
Artifact count
Timeline events
Findings
Recent activity
```

---

## 26.3 Evidence Page

Display:

```text
Evidence ID
Filename
Type
Size
SHA-256
Hash status
Collection information
Processing status
Chain of custody
```

Actions:

```text
Verify Hash
Run Parser
View Results
Add Note
```

---

## 26.4 Artifact Results

Display extracted artifacts in a table.

Required capabilities:

```text
Search
Filter
Sort
View details
View provenance
```

---

## 26.5 Timeline

Primary investigation screen.

Layout should support:

```text
Timeline visualization
Event table
Filters
Search
Event details
Source evidence
```

Selecting an event must reveal:

```text
Event metadata
Original timestamp
Normalized timestamp
Source
Evidence
Parser
Description
Raw/source data where available
Related events
```

---

## 26.6 Findings

Display:

```text
Finding ID
Severity
Confidence
Title
Rule
Status
Supporting Event Count
```

Clicking a finding should reveal all supporting evidence.

---

## 26.7 Chain of Custody

Display chronological custody records.

The history must be easy to export into reports.

---

## 26.8 Report

The user should be able to:

```text
Review report summary
Generate report
Download report
Open generated report
```

---

# 27. API Requirements

The backend should expose a REST API.

Minimum API surface:

```text
POST   /api/cases
GET    /api/cases
GET    /api/cases/{case_id}
PATCH  /api/cases/{case_id}

POST   /api/cases/{case_id}/evidence
GET    /api/evidence/{evidence_id}
POST   /api/evidence/{evidence_id}/verify

GET    /api/evidence/{evidence_id}/custody
POST   /api/evidence/{evidence_id}/custody

POST   /api/evidence/{evidence_id}/parse

GET    /api/cases/{case_id}/events
GET    /api/events/{event_id}

POST   /api/cases/{case_id}/correlate

GET    /api/cases/{case_id}/findings
GET    /api/findings/{finding_id}

POST   /api/cases/{case_id}/report
GET    /api/reports/{report_id}
```

The API design may evolve during implementation, but the underlying responsibilities must remain consistent.

---

# 28. CLI Requirements

A CLI is desirable but secondary to the web UI.

Initial commands may include:

```text
dfir case create
dfir evidence add
dfir evidence verify
dfir parse
dfir timeline
dfir correlate
dfir report
```

The CLI should reuse the same backend/domain services rather than implement a second business-logic layer.

---

# 29. Data Storage Requirements

The MVP should use:

```text
PostgreSQL
```

for structured application data.

Raw evidence should remain in local filesystem storage.

Conceptual structure:

```text
data/
└── cases/
    └── CASE-2026-001/
        ├── evidence/
        ├── reports/
        ├── exports/
        └── metadata/
```

PostgreSQL should store metadata and derived analysis results rather than large raw evidence blobs.

---

# 30. Core Data Entities

The MVP must support at least:

```text
Case
Evidence
ChainOfCustodyEntry
Artifact
TimelineEvent
CorrelationRule
Finding
InvestigationNote
ProcessingJob
AuditEvent
Report
```

Relationships:

```text
Case
 ├── Evidence
 │    ├── ChainOfCustodyEntry
 │    └── Artifact
 │
 ├── TimelineEvent
 │
 ├── Finding
 │    ├── TimelineEvent references
 │    └── Evidence references
 │
 ├── Notes
 └── Reports
```

---

# 31. Processing Jobs

Artifact parsing may take time.

The application must therefore represent parsing as a processing job.

Example statuses:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
```

Each processing job should record:

```text
Job ID
Case ID
Evidence ID
Parser
Started At
Completed At
Status
Records Produced
Error Message
```

This creates a clean extension point for future background processing.

---

# 32. Audit Events

Application-level audit logging should record important operations such as:

```text
CASE_CREATED
EVIDENCE_ADDED
HASH_VERIFIED
PARSER_STARTED
PARSER_COMPLETED
PARSER_FAILED
CORRELATION_RUN
FINDING_CREATED
FINDING_STATUS_CHANGED
REPORT_GENERATED
```

This audit trail is separate from forensic chain of custody.

Chain of custody describes evidence handling.

Application audit logs describe actions performed inside the software.

---

# 33. Security Requirements

Although the MVP is local-first, basic security requirements still apply.

The application must:

- Never execute uploaded evidence.
- Treat evidence as untrusted data.
- Use read-only parsing wherever possible.
- Avoid modifying original evidence.
- Validate file paths.
- Prevent path traversal.
- Restrict evidence storage locations.
- Avoid arbitrary command execution.
- Avoid shelling out to untrusted values.
- Sanitize report content.
- Keep secrets outside source control.
- Use environment variables for configuration.
- Pin dependencies where practical.

---

# 34. Privacy Requirements

Forensic evidence may contain highly sensitive information.

Therefore:

- Evidence must remain local in MVP.
- No external telemetry should be required.
- No evidence content should be sent to third-party APIs.
- No cloud AI analysis should be required for forensic conclusions.
- Logs must not unnecessarily expose sensitive evidence content.

The product should operate successfully without internet connectivity after dependencies are installed.

---

# 35. Forensic Integrity Principles

The application must follow these principles:

### Principle 1 — Original Evidence Is Sacred

Never modify the original evidence file.

### Principle 2 — Derived Data Is Not Original Evidence

Parsed records and timeline events are derived data.

### Principle 3 — Provenance Must Be Preserved

Every derived finding must be traceable to its source.

### Principle 4 — Heuristics Must Not Become Facts

A correlation rule produces an investigative observation, not automatic proof.

### Principle 5 — Missing Evidence Must Remain Missing

The system must not invent timestamps, users, file paths, or conclusions.

### Principle 6 — Uncertainty Must Be Explicit

Use values such as:

```text
UNKNOWN
NOT_AVAILABLE
UNVERIFIED
LOW_CONFIDENCE
```

where appropriate.

---

# 36. Future Architecture Extension Points

The MVP must leave clean interfaces for future modules.

Future modules:

```text
Malware Triage
Steganography Forensics
Anti-Forensics Detection
Browser Forensics
Memory Forensics
Network Forensics
Cloud Forensics
```

Each future module should ideally produce standardized objects that can feed the same timeline and finding systems.

For example:

```text
Malware Parser
       ↓
Artifact
       ↓
Timeline Event
       ↓
Finding
       ↓
Report
```

and:

```text
Steganography Analyzer
       ↓
Analysis Result
       ↓
Finding
       ↓
Report
```

The core case/report architecture should not need to be redesigned for this.

---

# 37. Technical Direction

The preferred technology stack is:

## Frontend

```text
React
TypeScript
Tailwind CSS
shadcn/ui
```

Optional:

```text
Recharts
Framer Motion
```

---

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

---

## Database

```text
PostgreSQL
```

---

## Forensic Processing

Initial libraries may include:

```text
python-evtx
python-registry
LnkParse3
Prefetch parsing library
pytsk3 / Sleuth Kit
```

Library choice must be validated during implementation and must not force the architecture to depend on a single parser implementation.

The research report identified python-evtx for EVTX, python-registry for offline Registry parsing, LnkParse3 for Windows shortcut analysis, and pytsk3/dfVFS as filesystem-analysis options.

---

## Reporting

Preferred initial implementation:

```text
ReportLab
```

The report generator should remain isolated behind a reporting service so that another PDF or document backend can be introduced later.

---

# 38. Testing Requirements

Testing is mandatory.

Every major forensic component must have automated tests.

Required test categories:

```text
Unit Tests
Parser Tests
Normalization Tests
Correlation Tests
API Tests
Integration Tests
End-to-End Tests
```

---

# 39. Parser Testing

Each parser should have known input and expected output.

Example:

```text
Input EVTX
    ↓
Parser
    ↓
Expected Event ID
Expected Timestamp
Expected Channel
Expected Fields
```

Parser failures must be explicit rather than silently producing incomplete data.

---

# 40. Timeline Testing

Tests must verify:

- Events sort correctly.
- UTC conversion works correctly.
- Original timestamps remain available.
- Missing timezone does not become a fabricated timezone.
- Events with equal timestamps remain deterministic.
- Filtering returns expected events.
- Provenance survives normalization.

---

# 41. Correlation Testing

Each rule must have:

```text
Positive Test
Negative Test
Boundary Test
Incomplete Evidence Test
```

Example:

```text
Scenario A
USB + file activity
→ Rule triggers

Scenario B
USB only
→ Rule does not trigger

Scenario C
USB activity outside time window
→ Rule does not trigger
```

---

# 42. End-to-End Demo Case

The MVP must include at least one synthetic or lab-generated investigation scenario.

Example:

```text
CASE-2026-001
"Potential Removable Media Activity"
```

Scenario:

```text
User logs in
      ↓
USB device activity occurs
      ↓
File activity occurs
      ↓
PowerShell activity occurs
      ↓
Additional file changes occur
```

The system should reconstruct the event chain and produce a report showing the supporting artifacts.

The demo scenario should be reproducible.

---

# 43. Performance Expectations

The MVP does not need enterprise-scale throughput.

However, the application should remain responsive for reasonable lab datasets.

Target characteristics:

```text
Case creation: near instant
Evidence metadata: near instant
SHA-256: streaming / non-blocking where practical
Timeline queries: interactive for normal test datasets
Filtering: interactive
Report generation: asynchronous or visibly processed
```

The application should avoid loading arbitrarily large evidence files entirely into memory.

---

# 44. Error Handling

Failures must be understandable to the examiner.

Example:

```text
Parser failed

Parser: EVTX
Evidence: Security.evtx
Reason:
Malformed or unsupported event structure.

Records successfully extracted: 12,482
Records failed: 3
```

A single malformed artifact must not unnecessarily destroy the entire case.

---

# 45. User Experience Principles

The UI should follow these principles:

### Investigator First

Important evidence should be visible quickly.

### Traceability First

Every important conclusion should lead back to supporting evidence.

### Explainability First

Rules must explain why a finding exists.

### No Fake Certainty

The application should distinguish evidence, inference, and examiner conclusion.

### Dense but Readable

Forensic applications need to display substantial information without overwhelming the examiner.

### Professional

The interface should look like an investigation tool rather than a generic admin dashboard.

---

# 46. MVP Acceptance Criteria

The MVP is considered complete when an examiner can perform the following successfully:

```text
Create a case
    ↓
Add at least one evidence item
    ↓
Calculate SHA-256
    ↓
Record chain-of-custody
    ↓
Run supported parsers
    ↓
Produce normalized events
    ↓
Open timeline
    ↓
Filter/search events
    ↓
Open event provenance
    ↓
Run correlation
    ↓
Review findings
    ↓
Generate PDF
    ↓
Trace findings back to evidence
```

All major steps must work using a reproducible test case.

---

# 47. MVP Quality Bar

The project is not considered complete merely because the pages and APIs exist.

A feature counts as complete only when:

```text
Implemented
+
Tested
+
Integrated
+
Demonstrated
+
Documented
```

A parser returning fabricated or placeholder data does not qualify as implemented.

A dashboard showing static sample numbers does not qualify as implemented.

A "threat score" without traceable supporting events does not qualify as implemented.

---

# 48. 14-Day Product Delivery Target

## Days 1–2

Foundation:

```text
Repository
Backend
Frontend
Database
Environment
Initial models
```

## Days 3–4

Case and evidence:

```text
Case management
Evidence records
SHA-256
Chain of custody
```

## Days 5–6

Core parsers:

```text
EVTX
Registry
```

## Day 7

Additional parsers:

```text
Prefetch
LNK
```

## Day 8

Filesystem metadata:

```text
NTFS / MFT
```

## Days 9–10

Timeline:

```text
Normalization
Filtering
Search
Event details
Provenance
```

## Day 11

Correlation:

```text
Rules
Findings
Confidence
Severity
```

## Day 12

Reporting:

```text
PDF
Evidence
Timeline
Findings
Chain of custody
```

## Day 13

Testing:

```text
Parser tests
Timeline tests
Correlation tests
Integration testing
```

## Day 14

Finalization:

```text
Bug fixing
UI polish
Demo case
README
Screenshots
Demo video
GitHub cleanup
```

---

# 49. Future Roadmap

## Phase 2 — Malware Triage

Potential capabilities:

```text
PE metadata
Hashing
Entropy
Imports
Strings
IOC extraction
YARA
MITRE ATT&CK mapping
Static risk assessment
```

No malware execution in the initial implementation.

---

## Phase 3 — Steganography Forensics

Potential capabilities:

```text
PNG analysis
JPEG/DCT analysis
BMP analysis
GIF analysis
Metadata analysis
Entropy analysis
Bit-plane analysis
Histogram analysis
LSB analysis
Steganalysis scoring
```

---

## Phase 4 — Anti-Forensics Detection

Potential capabilities:

```text
Timestamp anomalies
Log clearing indicators
Artifact inconsistencies
Deletion indicators
Evidence gaps
Persistence cleanup indicators
```

---

# 50. Portfolio Objective

The project must be suitable for presentation in a professional portfolio and resume.

It should demonstrate:

```text
Digital Forensics
Windows Forensics
Artifact Analysis
Evidence Integrity
Timeline Reconstruction
Correlation
Python Development
FastAPI Development
React Development
Database Design
Forensic Reporting
Software Engineering
```

The project should complement rather than duplicate the developer's existing **Fragmented File Recovery & Visualization Tool**, which already demonstrates file carving, cluster mapping, fragment analysis, visualization, and recovery.

This project instead demonstrates the broader investigation workflow.

---

# 51. Resume Positioning

Recommended project title:

**DFIR Investigation Workbench**

Suggested resume description:

> Developed a modular digital forensics investigation platform for Windows evidence triage, artifact analysis, timeline reconstruction, event correlation, evidence integrity verification, chain-of-custody tracking, and automated forensic reporting.

Potential additional bullet:

> Implemented modular parsers for EVTX, Registry, Prefetch, LNK, and NTFS/MFT metadata, normalizing heterogeneous forensic artifacts into a unified investigation timeline with evidence-backed correlation findings.

Potential third bullet:

> Built a React/FastAPI investigation interface with searchable timelines, provenance-aware findings, SHA-256 evidence verification, chain-of-custody tracking, and automated PDF report generation.

---

# 52. Definition of Done

The MVP is done only when:

### Product

- [ ] Case management works.
- [ ] Evidence management works.
- [ ] SHA-256 verification works.
- [ ] Chain of custody works.
- [ ] Supported parsers work on real test artifacts.
- [ ] Timeline reconstruction works.
- [ ] Timeline filtering/search works.
- [ ] Correlation rules work.
- [ ] Findings work.
- [ ] PDF reporting works.
- [ ] Provenance links findings to evidence.
- [ ] Demo investigation can be reproduced.

### Engineering

- [ ] Backend tests pass.
- [ ] Frontend builds successfully.
- [ ] Integration tests pass.
- [ ] No critical lint/type errors.
- [ ] No obvious security vulnerabilities from unsafe input handling.
- [ ] Configuration is documented.
- [ ] Database migrations work.

### Forensic Quality

- [ ] Original evidence is not modified.
- [ ] Evidence hashes are recorded.
- [ ] Original timestamps are retained.
- [ ] Unknown values remain unknown.
- [ ] Findings explain their supporting evidence.
- [ ] Heuristics are clearly labeled.
- [ ] No unsupported forensic conclusions are generated.

### Documentation

- [ ] README completed.
- [ ] Architecture documented.
- [ ] Development setup documented.
- [ ] Test case documented.
- [ ] Demo investigation documented.
- [ ] Screenshots included.
- [ ] Sample report included.

---

# 53. Critical Scope Lock

This section is mandatory.

Codex and future contributors must treat this PRD as the scope authority for the MVP.

### Do not expand the MVP automatically.

Do not implement:

```text
Browser history
Recycle Bin
Scheduled Tasks
Malware analysis
Steganography
Anti-forensics
Memory forensics
Network forensics
ML detection
Enterprise authentication
Multi-tenancy
Cloud storage
Kubernetes
```

unless explicitly requested.

When a feature request appears outside this PRD:

1. Identify it as out-of-scope.
2. Do not implement it automatically.
3. Suggest where it belongs in the future roadmap.
4. Continue working within the current MVP scope.

---

# 54. Product Success Criteria

The MVP is successful if an interviewer can watch a short demonstration and understand:

```text
This application receives forensic evidence,
preserves its integrity,
extracts useful Windows artifacts,
reconstructs a timeline,
connects related activity,
shows why a finding was produced,
and generates a traceable investigation report.
```

The product should communicate that the developer understands both:

```text
Digital Forensics
        +
Software Engineering
```

rather than merely demonstrating a UI or a collection of scripts.

---

# 55. Final Product Principle

The central philosophy of the DFIR Investigation Workbench is:

> **Evidence first. Correlation second. Conclusion last.**

The platform must help the examiner move from raw evidence to supported investigative conclusions without hiding the evidence chain or overstating certainty.

That principle governs all MVP features and all future modules.
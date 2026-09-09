from enum import StrEnum


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class EvidenceType(StrEnum):
    DISK_IMAGE = "DISK_IMAGE"
    LOG_FILE = "LOG_FILE"
    MEMORY_DUMP = "MEMORY_DUMP"
    REGISTRY_HIVE = "REGISTRY_HIVE"
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"
    OTHER = "OTHER"


class ArtifactType(StrEnum):
    """Controlled artifact categories; REFERENCE is reserved for framework tests."""

    REFERENCE = "REFERENCE"
    EVTX = "EVTX"
    REGISTRY = "REGISTRY"
    PREFETCH = "PREFETCH"
    LNK = "LNK"
    NTFS = "NTFS"
    NTFS_MFT = "NTFS_MFT"


class ParserExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"

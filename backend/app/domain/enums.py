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

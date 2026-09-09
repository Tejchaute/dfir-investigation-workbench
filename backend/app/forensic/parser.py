from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, BinaryIO

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@dataclass(frozen=True)
class ParserContext:
    """Controlled context containing a read-only evidence stream and safe metadata."""

    evidence_id: uuid.UUID
    case_id: uuid.UUID
    evidence_type: EvidenceType
    source: BinaryIO
    source_name: str | None = None


class ParsedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: NonEmptyText
    source_record_identifier: str | None = None
    event_time: datetime | None = None
    data: dict[str, object] = Field(default_factory=dict)
    provenance: dict[str, object] = Field(default_factory=dict)


class ParserResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ParserExecutionStatus
    records: tuple[ParsedRecord, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: dict[str, object] = Field(default_factory=dict)
    statistics: dict[str, int | float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_contract(self) -> ParserResult:
        if self.status in {ParserExecutionStatus.PENDING, ParserExecutionStatus.RUNNING}:
            raise ValueError("a parser result must represent a terminal state")
        if self.status is ParserExecutionStatus.COMPLETED and (self.warnings or self.errors):
            raise ValueError("COMPLETED results cannot contain warnings or errors")
        if self.status is ParserExecutionStatus.COMPLETED_WITH_WARNINGS and (
            not self.warnings or self.errors
        ):
            raise ValueError("warning results require warnings and cannot contain fatal errors")
        if self.status in {
            ParserExecutionStatus.FAILED,
            ParserExecutionStatus.UNSUPPORTED,
        } and (not self.errors or self.records):
            raise ValueError(
                "failed or unsupported results require errors and cannot contain records"
            )
        return self


class ForensicParser(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def supported_artifact_types(self) -> frozenset[ArtifactType]: ...

    def supports(self, artifact_type: ArtifactType) -> bool:
        return artifact_type in self.supported_artifact_types

    @abstractmethod
    def parse(self, context: ParserContext) -> ParserResult: ...

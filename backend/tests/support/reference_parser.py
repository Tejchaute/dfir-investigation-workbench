from datetime import UTC, datetime, timedelta
from typing import cast

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ForensicParser, ParsedRecord, ParserContext, ParserResult


class ReferenceParser(ForensicParser):
    """Deterministic framework fixture. It does not interpret forensic content."""

    def __init__(self, mode: str = "success", version: str = "test-1") -> None:
        self.mode = mode
        self._version = version

    @property
    def name(self) -> str:
        return "TEST_REFERENCE_PARSER"

    @property
    def version(self) -> str:
        return self._version

    @property
    def supported_artifact_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.REFERENCE})

    def parse(self, context: ParserContext) -> ParserResult:
        assert context.source.writable() is False
        while context.source.read(1024):
            pass
        if self.mode == "warning":
            return ParserResult(
                status=ParserExecutionStatus.COMPLETED_WITH_WARNINGS,
                warnings=("Synthetic recoverable warning",),
                records=(self._record("warning", None),),
                statistics={"records_seen": 1},
            )
        if self.mode == "failure":
            return ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=("Synthetic parser failure",),
            )
        if self.mode == "unsupported":
            return ParserResult(
                status=ParserExecutionStatus.UNSUPPORTED,
                errors=("Synthetic unsupported input",),
            )
        if self.mode == "exception":
            raise RuntimeError("synthetic test exception")
        if self.mode == "malformed":
            return cast(ParserResult, {"not": "a parser result"})
        base = datetime(2026, 1, 1, tzinfo=UTC)
        return ParserResult(
            status=ParserExecutionStatus.COMPLETED,
            records=(
                self._record("later", base + timedelta(seconds=1)),
                self._record("undated", None),
                self._record("earlier", base),
            ),
            metadata={"fixture": True},
            statistics={"records_seen": 3},
        )

    @staticmethod
    def _record(identifier: str, event_time: datetime | None) -> ParsedRecord:
        return ParsedRecord(
            record_type="TEST_REFERENCE_RECORD",
            source_record_identifier=identifier,
            event_time=event_time,
            data={"fixture": identifier},
            provenance={"fixture_source": identifier},
        )

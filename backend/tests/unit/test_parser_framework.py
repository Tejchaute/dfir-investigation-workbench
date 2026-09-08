import io
import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ConflictError, ValidationError
from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus
from app.forensic.parser import ParserContext, ParserResult
from app.forensic.registry import ParserRegistry
from tests.support.reference_parser import ReferenceParser


def test_parser_registration_discovery_and_resolution() -> None:
    parser = ReferenceParser()
    registry = ParserRegistry([parser])
    assert registry.supports(ArtifactType.REFERENCE)
    assert registry.get(ArtifactType.REFERENCE) is parser
    assert registry.parsers() == (parser,)
    assert parser.name == "TEST_REFERENCE_PARSER"
    assert parser.version == "test-1"


def test_duplicate_and_unsupported_registration_fail_clearly() -> None:
    registry = ParserRegistry([ReferenceParser()])
    with pytest.raises(ConflictError, match="already have registered parsers"):
        registry.register(ReferenceParser(version="test-2"))
    with pytest.raises(ValidationError, match="No parser is registered"):
        registry.get(ArtifactType.EVTX)


def test_result_contract_accepts_success_warning_failure_and_unsupported() -> None:
    assert (
        ParserResult(status=ParserExecutionStatus.COMPLETED).status
        is ParserExecutionStatus.COMPLETED
    )
    warning = ParserResult(
        status=ParserExecutionStatus.COMPLETED_WITH_WARNINGS, warnings=("recoverable",)
    )
    assert warning.warnings == ("recoverable",)
    assert ParserResult(status=ParserExecutionStatus.FAILED, errors=("fatal",)).errors == ("fatal",)
    unsupported = ParserResult(
        status=ParserExecutionStatus.UNSUPPORTED, errors=("unsupported input",)
    )
    assert unsupported.status is ParserExecutionStatus.UNSUPPORTED


@pytest.mark.parametrize(
    ("status", "warnings", "errors"),
    [
        (ParserExecutionStatus.RUNNING, (), ()),
        (ParserExecutionStatus.COMPLETED, ("not allowed",), ()),
        (ParserExecutionStatus.COMPLETED_WITH_WARNINGS, (), ()),
        (ParserExecutionStatus.FAILED, (), ()),
    ],
)
def test_malformed_results_are_rejected(
    status: ParserExecutionStatus, warnings: tuple[str, ...], errors: tuple[str, ...]
) -> None:
    with pytest.raises(PydanticValidationError):
        ParserResult(status=status, warnings=warnings, errors=errors)


def test_parser_context_contains_read_only_stream_without_path() -> None:
    source = io.BytesIO(b"synthetic")
    context = ParserContext(
        evidence_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        evidence_type=EvidenceType.FILE,
        source=source,
    )
    assert not hasattr(context, "source_path")

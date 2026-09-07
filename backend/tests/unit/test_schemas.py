from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain.enums import EvidenceType
from app.schemas.custody import ChainOfCustodyEntryCreate
from app.schemas.evidence import EvidenceCreate


def test_evidence_size_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        EvidenceCreate(
            evidence_number="TEST-EVIDENCE-1",
            name="Test metadata",
            evidence_type=EvidenceType.FILE,
            size_bytes=-1,
        )


def test_custody_timestamp_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        ChainOfCustodyEntryCreate(
            timestamp=datetime(2026, 1, 1),
            person="Test Actor",
            action="TEST_ACTION",
        )

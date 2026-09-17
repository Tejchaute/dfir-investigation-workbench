import uuid
from datetime import UTC, datetime

from app.domain.enums import ReportType
from app.reporting.renderers import SECTION_ORDER, HtmlRenderer, JsonRenderer, PdfRenderer
from app.schemas.report import CaseReportSection, ReportIdentification, ReportSnapshot


def _snapshot() -> ReportSnapshot:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    return ReportSnapshot(
        report_identification=ReportIdentification(
            report_id=uuid.UUID(int=1),
            report_type=ReportType.FORENSIC_INVESTIGATION_REPORT,
            report_version="1.0.0",
            generated_at=now,
            generated_by="LOCAL_APPLICATION",
            case_number="CASE-2026-0001",
        ),
        case_information=CaseReportSection(
            case_id=uuid.UUID(int=2),
            case_number="CASE-2026-0001",
            status="OPEN",
            name="<script>alert('x')</script>",
            description=None,
            investigator=None,
            created_at=now,
            updated_at=now,
            closed_at=None,
            archived_at=None,
            timestamp_note="UTC",
        ),
        evidence_inventory=(),
        evidence_integrity=(),
        chain_of_custody=(),
        artifact_summary=(),
        timeline_reconstruction=(),
        correlation_analysis=(),
        findings=(),
        methodology=("Deterministic methodology.",),
        limitations=("Correlation does not establish causality.",),
        audit_summary=(),
    )


def test_all_renderers_are_deterministic_and_share_section_order() -> None:
    snapshot = _snapshot()
    for renderer in (JsonRenderer(), HtmlRenderer(), PdfRenderer()):
        first = renderer.render(snapshot)
        assert first == renderer.render(snapshot)
        assert first
    html = HtmlRenderer().render(snapshot).decode()
    positions = [html.index(title) for title, _key in SECTION_ORDER]
    assert positions == sorted(positions)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "http://" not in html and "https://" not in html
    pdf = PdfRenderer().render(snapshot)
    assert pdf.startswith(b"%PDF-")
    assert b"/Page" in pdf


def test_json_is_canonical_utf8_and_contains_all_sections() -> None:
    content = JsonRenderer().render(_snapshot())
    assert content.startswith(b'{"artifact_summary"')
    for _title, key in SECTION_ORDER:
        assert f'"{key}"'.encode() in content

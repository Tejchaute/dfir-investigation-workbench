from __future__ import annotations

import hashlib
import html
import json
from io import BytesIO
from typing import Protocol

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.enums import ReportFormat
from app.schemas.report import ReportSnapshot

SECTION_ORDER = (
    ("Report Identification", "report_identification"),
    ("Case Information", "case_information"),
    ("Evidence Inventory", "evidence_inventory"),
    ("Evidence Integrity", "evidence_integrity"),
    ("Chain of Custody", "chain_of_custody"),
    ("Artifact Summary", "artifact_summary"),
    ("Timeline Reconstruction", "timeline_reconstruction"),
    ("Correlation Analysis", "correlation_analysis"),
    ("Findings", "findings"),
    ("Methodology", "methodology"),
    ("Limitations", "limitations"),
    ("Audit Summary", "audit_summary"),
)


class ReportRenderer(Protocol):
    format: ReportFormat

    def render(self, snapshot: ReportSnapshot) -> bytes: ...


def canonical_json(snapshot: ReportSnapshot) -> bytes:
    return json.dumps(
        snapshot.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class JsonRenderer:
    format = ReportFormat.JSON

    def render(self, snapshot: ReportSnapshot) -> bytes:
        return canonical_json(snapshot)


class HtmlRenderer:
    format = ReportFormat.HTML

    def render(self, snapshot: ReportSnapshot) -> bytes:
        payload = snapshot.model_dump(mode="json")
        sections = []
        for heading, key in SECTION_ORDER:
            value = json.dumps(payload[key], ensure_ascii=False, sort_keys=True, indent=2)
            sections.append(
                f"<section><h2>{html.escape(heading)}</h2><pre>{html.escape(value)}</pre></section>"
            )
        document = "".join(
            (
                '<!doctype html><html><head><meta charset="utf-8">'
                "<title>DFIR Investigation Report</title>",
                "<style>@page{margin:18mm}body{font-family:Arial,sans-serif;color:#111}",
                "h1,h2{page-break-after:avoid}section{margin:0 0 18px}pre{white-space:pre-wrap;",
                "overflow-wrap:anywhere;background:#f5f5f5;padding:10px;"
                "border:1px solid #ddd}</style>",
                "</head><body><h1>DFIR Investigation Report</h1>",
                *sections,
                "</body></html>",
            )
        )
        return document.encode("utf-8")


class PdfRenderer:
    format = ReportFormat.PDF

    def render(self, snapshot: ReportSnapshot) -> bytes:
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="DFIR Investigation Report",
            author=snapshot.report_identification.generated_by,
            invariant=True,
        )
        styles = getSampleStyleSheet()
        story: list[Flowable] = [
            Paragraph("DFIR Investigation Report", styles["Title"]),
            Spacer(1, 8),
        ]
        payload = snapshot.model_dump(mode="json")
        for index, (heading, key) in enumerate(SECTION_ORDER):
            if index:
                story.append(PageBreak())
            story.append(Paragraph(html.escape(heading), styles["Heading1"]))
            rows = _pdf_rows(payload[key])
            table = Table(rows, colWidths=[45 * mm, 120 * mm], repeatRows=0)
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)

        def numbered_page(canvas: object, doc: object) -> None:
            canvas.saveState()  # type: ignore[attr-defined]
            canvas.setFont("Helvetica", 8)  # type: ignore[attr-defined]
            canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")  # type: ignore[attr-defined]
            canvas.restoreState()  # type: ignore[attr-defined]

        document.build(story, onFirstPage=numbered_page, onLaterPages=numbered_page)
        return output.getvalue()


def _pdf_rows(value: object) -> list[list[Paragraph]]:
    if isinstance(value, dict):
        items = [(str(key), value[key]) for key in sorted(value)]
    elif isinstance(value, list):
        items = [(str(index + 1), item) for index, item in enumerate(value)]
    else:
        items = [("Value", value)]
    if not items:
        items = [("Status", "No records available")]
    styles = getSampleStyleSheet()
    return [
        [
            Paragraph(html.escape(label), styles["BodyText"]),
            Paragraph(
                html.escape(json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)),
                styles["BodyText"],
            ),
        ]
        for label, item in items
    ]


RENDERERS: dict[ReportFormat, ReportRenderer] = {
    ReportFormat.JSON: JsonRenderer(),
    ReportFormat.HTML: HtmlRenderer(),
    ReportFormat.PDF: PdfRenderer(),
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

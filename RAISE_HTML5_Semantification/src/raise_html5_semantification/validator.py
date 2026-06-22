from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from raise_html5_semantification.heading_rules import is_plausible_heading_text
from raise_html5_semantification.loader import InputValidationError, load_blocks
from raise_html5_semantification.models import ValidationIssue, ValidationSummary
from raise_html5_semantification.utils import ensure_parent

TRACEABLE_TAGS = {
    "section",
    "h1",
    "h2",
    "h3",
    "p",
    "aside",
    "ul",
    "ol",
    "li",
    "table",
    "caption",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "figure",
    "img",
    "figcaption",
    "pre",
}


def validate_html_string(
    html: str,
    expected_blocks: int = 0,
    *,
    chunk_count: int = 0,
    source_map_entry_count: int = 0,
    input_quality_report: dict | None = None,
) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    soup = BeautifulSoup(html, "lxml")

    main = soup.find("main")
    if not soup.find("html") or not main:
        issues.append(
            ValidationIssue(severity="error", message="HTML document lacks html or main tag.")
        )

    elements = main.find_all(TRACEABLE_TAGS) if main else []
    ids = [element.get("id") for element in soup.find_all(id=True)]
    duplicate_ids = sorted(
        element_id for element_id, count in Counter(ids).items() if count > 1
    )
    for element_id in duplicate_ids:
        issues.append(
            ValidationIssue(severity="error", message=f"Duplicate HTML id found: {element_id}.")
        )

    known_ids = set(ids)
    traceable = 0
    for element in elements:
        has_traceability = (
            element.get("id")
            and element.get("data-source-block")
            and element.get("data-semantic-role")
        )
        if has_traceability:
            traceable += 1
        else:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=(
                        f"Missing id, data-source-block, or data-semantic-role "
                        f"on <{element.name}>."
                    ),
                    block_id=element.get("data-source-block"),
                )
            )
        if element.name in {"h1", "h2", "h3"}:
            heading_text = element.get_text(" ", strip=True)
            if not is_plausible_heading_text(heading_text):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message="Heading text resembles prose, table data, or OCR noise.",
                        block_id=element.get("data-source-block"),
                    )
                )
        if element.name == "section":
            labelled_by = element.get("aria-labelledby")
            if not labelled_by or labelled_by not in known_ids:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message="Section has missing or broken aria-labelledby.",
                        block_id=element.get("data-source-block"),
                    )
                )
            if not element.get("aria-label") or not element.get("data-section-title"):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message="Section lacks accessible label or data-section-title.",
                        block_id=element.get("data-source-block"),
                    )
                )

    if expected_blocks and traceable < expected_blocks:
        issues.append(
            ValidationIssue(
                severity="warning",
                message=(
                    "Traceable element count is lower than input block count; "
                    "empty blocks may have been skipped."
                ),
            )
        )

    heading_counts = {
        level: len(main.find_all(level, attrs={"data-source-block": True})) if main else 0
        for level in ("h1", "h2", "h3")
    }
    outline_count = len(soup.select("#document-outline a"))
    section_count = len(main.find_all("section")) if main else 0
    image_count = len(
        main.find_all("figure", attrs={"data-semantic-role": "image-figure"})
    ) if main else 0
    image_placeholder_count = len(
        main.find_all("figure", attrs={"data-semantic-role": "image-placeholder"})
    ) if main else 0
    if heading_counts["h1"] > 50:
        issues.append(ValidationIssue(severity="warning", message="H1 count is unusually high."))
    if heading_counts["h2"] > 1000:
        issues.append(ValidationIssue(severity="warning", message="H2 count is unusually high."))
    if outline_count > 300:
        issues.append(
            ValidationIssue(severity="warning", message="Document outline exceeds 300 links.")
        )
    if image_placeholder_count:
        issues.append(
            ValidationIssue(
                severity="warning",
                message=(
                    f"{image_placeholder_count} image-like blocks lack an upstream image path."
                ),
            )
        )

    input_quality_status = "unknown"
    if input_quality_report:
        input_quality_status = str(input_quality_report.get("status", "unknown"))
        total = int(input_quality_report.get("total_blocks", 0))
        missing_counts = [
            int(input_quality_report.get(field, 0))
            for field in (
                "blocks_missing_block_id",
                "blocks_missing_page_number",
                "blocks_missing_bbox",
                "blocks_missing_font_size",
                "blocks_missing_confidence",
            )
        ]
        if total and max(missing_counts, default=0) / total > 0.25:
            issues.append(
                ValidationIssue(
                    severity="warning", message="More than 25% of blocks lack key metadata."
                )
            )
        unstructured_tables = len(
            input_quality_report.get("table_like_blocks_without_table_data", [])
        )
        table_like_count = int(input_quality_report.get("table_like_block_count", 0))
        if unstructured_tables >= 10 and (
            not table_like_count or unstructured_tables / table_like_count > 0.25
        ):
            issues.append(
                ValidationIssue(
                    severity="warning", message="Many table-like blocks lack table structure."
                )
            )

    return ValidationSummary(
        ok=not any(issue.severity == "error" for issue in issues),
        input_block_count=expected_blocks,
        html_element_count=len(elements),
        traceable_element_count=traceable,
        heading_count_by_level=heading_counts,
        outline_count=outline_count,
        section_count=section_count,
        chunk_count=chunk_count,
        source_map_entry_count=source_map_entry_count,
        input_quality_status=input_quality_status,
        image_count=image_count,
        image_placeholder_count=image_placeholder_count,
        issues=issues,
    )


def validate_input_file(input_path: str | Path) -> ValidationSummary:
    try:
        blocks = load_blocks(input_path)
    except (InputValidationError, ValueError) as exc:
        return ValidationSummary(
            ok=False,
            issues=[ValidationIssue(severity="error", message=str(exc))],
        )
    return ValidationSummary(ok=True, input_block_count=len(blocks))


def write_validation_report(summary: ValidationSummary, output_path: str | Path) -> None:
    path = Path(output_path)
    ensure_parent(path)
    path.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")

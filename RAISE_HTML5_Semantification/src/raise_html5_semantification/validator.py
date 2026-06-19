from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

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
    "th",
    "td",
    "figure",
}


def validate_html_string(html: str, expected_blocks: int = 0) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    soup = BeautifulSoup(html, "lxml")

    main = soup.find("main")
    if not soup.find("html") or not main:
        issues.append(
            ValidationIssue(severity="error", message="HTML document lacks html or main tag.")
        )

    elements = main.find_all(TRACEABLE_TAGS) if main else []
    ids = [element.get("id") for element in soup.find_all(id=True)]
    duplicate_ids = sorted({element_id for element_id in ids if ids.count(element_id) > 1})
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

    return ValidationSummary(
        ok=not any(issue.severity == "error" for issue in issues),
        input_block_count=expected_blocks,
        html_element_count=len(elements),
        traceable_element_count=traceable,
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

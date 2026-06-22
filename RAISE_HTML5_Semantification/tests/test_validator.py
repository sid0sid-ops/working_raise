from pathlib import Path

from raise_html5_semantification.html_writer import render_document
from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.section_builder import build_section_tree
from raise_html5_semantification.validator import validate_html_string


def test_validation_report_generation() -> None:
    blocks = load_blocks(Path("tests/fixtures/target_blocks.json"))
    html = render_document(build_section_tree(blocks))
    summary = validate_html_string(html, expected_blocks=len(blocks))

    assert summary.ok
    assert summary.input_block_count == 5
    assert summary.traceable_element_count >= 5
    assert summary.heading_count_by_level == {"h1": 0, "h2": 1, "h3": 0}
    assert summary.outline_count == 1
    assert summary.section_count == 1


def test_validator_warns_about_non_semantic_heading_text() -> None:
    html = """<html><body><main>
    <h1 id="h1-noise" data-source-block="noise" data-semantic-role="heading">12345</h1>
    </main></body></html>"""

    summary = validate_html_string(html)

    assert summary.ok
    assert any("OCR noise" in issue.message for issue in summary.issues)


def test_validator_reports_duplicate_ids() -> None:
    html = """<html><body><main>
    <p id="duplicate" data-source-block="one" data-semantic-role="paragraph">One</p>
    <p id="duplicate" data-source-block="two" data-semantic-role="paragraph">Two</p>
    </main></body></html>"""

    summary = validate_html_string(html)

    assert not summary.ok
    assert any("Duplicate HTML id" in issue.message for issue in summary.issues)

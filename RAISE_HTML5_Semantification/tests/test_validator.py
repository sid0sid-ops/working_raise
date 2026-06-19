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

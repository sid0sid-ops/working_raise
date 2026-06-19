from raise_html5_semantification.heading_rules import classify_heading, contains_section_keyword
from raise_html5_semantification.models import Block


def test_respects_heading_guess() -> None:
    block = Block(block_id="h", text="Research Activities", block_type_guess="heading")

    assert classify_heading(block, baseline_font_size=11) == 2


def test_detects_keyword_heading_from_metadata() -> None:
    block = Block(
        block_id="h",
        text="FACULTY AWARDS",
        font_size=16,
        is_bold=True,
        block_type_guess="paragraph",
    )

    assert classify_heading(block, baseline_font_size=11) == 1
    assert contains_section_keyword(block.text)

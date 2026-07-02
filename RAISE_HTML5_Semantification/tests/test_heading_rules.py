from raise_html5_semantification.heading_rules import (
    classify_heading,
    contains_section_keyword,
    is_plausible_heading_text,
    semantic_heading_level,
)
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


def test_rejects_numeric_table_values_and_ocr_noise_as_headings() -> None:
    for text in ("117598500\n117598500\n0\n117598500", "\\ \\ \\", "32795222637"):
        block = Block(
            block_id="table-fragment",
            text=text,
            font_size=18,
            is_bold=True,
            block_type_guess="paragraph",
        )
        assert classify_heading(block, baseline_font_size=11) is None
        assert not is_plausible_heading_text(text)


def test_rejects_contents_dot_leader_as_heading() -> None:
    block = Block(
        block_id="toc-entry",
        text="DEPARTMENTS ........................................................ 42",
        font_size=14,
        is_bold=True,
        block_type_guess="heading",
    )

    assert classify_heading(block, baseline_font_size=11) is None


def test_body_size_keyword_needs_an_additional_heading_signal() -> None:
    plain = Block(block_id="plain", text="Research", font_size=11)
    bold = Block(block_id="bold", text="Research", font_size=11, is_bold=True)

    assert classify_heading(plain, baseline_font_size=11) is None
    assert classify_heading(bold, baseline_font_size=11) == 2


def test_allows_cover_year_and_ordinal_titles() -> None:
    assert is_plausible_heading_text("102nd")
    assert is_plausible_heading_text("2024-2025")


def test_annual_report_heading_hierarchy() -> None:
    assert semantic_heading_level("FACULTY OF ARTS") == 1
    assert semantic_heading_level("DEPARTMENT OF ENGLISH") == 2
    assert semantic_heading_level("Publications") == 3
    assert semantic_heading_level("Research Projects") == 3
    assert semantic_heading_level("Faculty Strength") == 3
    assert semantic_heading_level("Seminars Organized") == 3
    assert semantic_heading_level("Patents Filed/Granted") == 3


def test_semantic_levels_override_generic_upstream_heading_label() -> None:
    faculty = Block(block_id="faculty", text="FACULTY OF ARTS", block_type_guess="heading")
    department = Block(
        block_id="department", text="DEPARTMENT OF ENGLISH", block_type_guess="heading"
    )
    publications = Block(block_id="publications", text="Publications", block_type_guess="heading")

    assert classify_heading(faculty, baseline_font_size=11) == 1
    assert classify_heading(department, baseline_font_size=11) == 2
    assert classify_heading(publications, baseline_font_size=11) == 3


def test_decimal_headings_assigned_logical_levels() -> None:
    intro = Block(block_id="intro", text="1. Introduction", block_type_guess="heading")
    res = Block(block_id="res", text="3.4 Research at iBRIC", block_type_guess="heading")
    details = Block(block_id="details", text="3.4.1 Mass Spectrometry", block_type_guess="heading")

    assert classify_heading(intro, baseline_font_size=11) == 1
    assert classify_heading(res, baseline_font_size=11) == 2
    assert classify_heading(details, baseline_font_size=11) == 3

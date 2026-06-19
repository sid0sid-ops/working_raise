from pathlib import Path

from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.section_builder import build_section_tree


def test_loader_accepts_nested_alternate_json_shapes() -> None:
    blocks = load_blocks(Path("tests/fixtures/alternate_format.json"))

    assert len(blocks) == 3
    assert blocks[0].block_id == "title-1"
    assert blocks[0].text == "FACULTY PUBLICATIONS"
    assert blocks[1].generated_block_id
    assert blocks[2].table == [["Year", "Count"], ["2024", "14"]]


def test_alternate_json_can_be_semantified() -> None:
    blocks = load_blocks(Path("tests/fixtures/alternate_format.json"))
    nodes = build_section_tree(blocks)

    assert nodes[0].kind == "heading"
    assert {child.kind for child in nodes[0].children} >= {"ordered-list", "table"}


def test_tough_annual_report_json_shapes_load_and_semantify() -> None:
    fixture_names = [
        "tough_annual_report_nested.json",
        "tough_annual_report_tables.json",
        "tough_annual_report_minimal.json",
    ]

    for fixture_name in fixture_names:
        blocks = load_blocks(Path("tests/fixtures") / fixture_name)
        nodes = build_section_tree(blocks)

        assert blocks
        assert nodes
        assert any(node.kind == "heading" for node in nodes)

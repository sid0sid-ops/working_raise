from pathlib import Path

from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.section_builder import build_section_tree


def test_build_section_tree_nests_content_under_heading() -> None:
    blocks = load_blocks(Path("tests/fixtures/target_blocks.json"))
    nodes = build_section_tree(blocks)

    assert nodes[0].kind == "heading"
    assert nodes[0].children
    assert {child.kind for child in nodes[0].children} >= {
        "paragraph",
        "unordered-list",
        "table",
        "aside",
    }

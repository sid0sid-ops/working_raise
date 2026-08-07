from pathlib import Path

from bs4 import BeautifulSoup
from raise_html5_semantification.html_writer import build_source_map, render_document
from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.section_builder import build_section_tree


def test_html_generation_is_semantic_and_traceable() -> None:
    blocks = load_blocks(Path("tests/fixtures/target_blocks.json"))
    html = render_document(build_section_tree(blocks))
    soup = BeautifulSoup(html, "lxml")

    assert soup.find("main")
    assert soup.find("section", attrs={"data-source-block": "b001"})
    assert soup.find("p", attrs={"data-source-block": "b002"})
    assert soup.find("ul", attrs={"data-source-block": "b003"})
    assert soup.find("table", attrs={"data-source-block": "b004"})
    assert soup.find("aside", attrs={"data-source-block": "b005"})


def test_html_generation_adds_advanced_labels_and_child_traceability() -> None:
    blocks = load_blocks(Path("tests/fixtures/target_blocks.json"))
    html = render_document(build_section_tree(blocks))
    soup = BeautifulSoup(html, "lxml")

    assert soup.find("nav", attrs={"id": "document-outline", "aria-label": "Document outline"})
    section = soup.find("section", attrs={"data-source-block": "b001"})
    assert section
    assert section.get("aria-labelledby") == "h2-b001"
    assert section.get("data-section-title") == "RESEARCH ACTIVITIES"
    assert section.get("data-semantic-role") == "section"

    list_item = soup.find("li", attrs={"data-source-block": "b003"})
    assert list_item
    assert list_item.get("id") == "li-b003-1"
    assert list_item.get("data-list-item-index") == "1"

    header_cell = soup.find("th", attrs={"data-source-block": "b004"})
    data_cell = soup.find("td", attrs={"data-source-block": "b004"})
    table_row = soup.find("tr", attrs={"data-source-block": "b004"})
    assert header_cell and header_cell.get("scope") == "col"
    assert data_cell and data_cell.get("data-row-index") == "1"
    assert table_row and table_row.get("data-reading-order") == "4"


def test_source_map_links_every_input_block_to_html_ids() -> None:
    blocks = load_blocks(Path("tests/fixtures/target_blocks.json"))
    nodes = build_section_tree(blocks)
    source_map = build_source_map(nodes, input_block_count=len(blocks))

    assert source_map.input_block_count == len(blocks)
    assert len(source_map.blocks) == len(blocks)
    table_entry = next(entry for entry in source_map.blocks if entry.block_id == "b004")
    assert table_entry.primary_element_id == "table-b004"
    assert "tr-b004-header" in table_entry.html_element_ids

import json
from pathlib import Path

from bs4 import BeautifulSoup

from raise_html5_semantification.artifacts import build_ai_chunks, build_section_map
from raise_html5_semantification.html_writer import render_document, render_outline
from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.main import build_report
from raise_html5_semantification.models import Block, HtmlNode
from raise_html5_semantification.section_builder import build_section_tree

FIXTURE = Path("tests/fixtures/target_blocks.json")


def _hierarchy_nodes() -> list[HtmlNode]:
    blocks = [
        Block(block_id="faculty", text="FACULTY OF ARTS", block_type_guess="heading"),
        Block(block_id="department", text="DEPARTMENT OF ENGLISH", block_type_guess="heading"),
        Block(block_id="publications", text="Publications", block_type_guess="heading"),
        Block(block_id="content", text="A source-traceable publication record."),
    ]
    return build_section_tree(blocks)


def test_default_outline_excludes_h3_but_body_preserves_it() -> None:
    soup = BeautifulSoup(render_document(_hierarchy_nodes()), "lxml")

    assert soup.find("h3", attrs={"data-source-block": "publications"})
    assert not soup.select_one('#document-outline a[data-source-block="publications"]')
    assert len(soup.select("#document-outline a")) == 2


def test_outline_depth_three_includes_h3_for_small_documents() -> None:
    soup = BeautifulSoup(render_document(_hierarchy_nodes(), outline_depth=3), "lxml")

    assert soup.select_one('#document-outline a[data-source-block="publications"]')


def test_large_requested_outline_collapses_h3_and_shows_note() -> None:
    h3_nodes = [
        HtmlNode(
            kind="heading",
            level=3,
            block=Block(block_id=f"subsection-{index}", text=f"Publications {index}"),
        )
        for index in range(301)
    ]
    root = HtmlNode(
        kind="heading",
        level=1,
        block=Block(block_id="faculty", text="FACULTY OF ARTS"),
        children=h3_nodes,
    )
    soup = BeautifulSoup(render_outline([root], outline_depth=3), "lxml")

    assert len(soup.select("a")) == 1
    assert "Detailed subsection headings are preserved" in soup.get_text(" ", strip=True)


def test_section_map_and_chunks_preserve_source_blocks() -> None:
    blocks = load_blocks(FIXTURE)
    nodes = build_section_tree(blocks)

    sections = build_section_map(nodes)
    chunks = build_ai_chunks(nodes)

    assert sections
    assert sections[0].start_block_id == "b001"
    assert set(sections[0].source_block_ids) == {block.block_id for block in blocks}
    assert chunks
    assert set(chunks[0].source_block_ids) == {block.block_id for block in blocks}
    assert 'data-source-block="b002"' in chunks[0].html


def test_build_generates_all_reports_and_validation_metrics(tmp_path: Path) -> None:
    output_paths = {
        "output_path": tmp_path / "report.html",
        "validation_output_path": tmp_path / "validation_report.json",
        "profile_output_path": tmp_path / "semantic_profile.json",
        "source_map_output_path": tmp_path / "source_map.json",
        "section_map_output_path": tmp_path / "section_map.json",
        "ai_chunks_output_path": tmp_path / "ai_chunks.json",
        "input_quality_output_path": tmp_path / "input_quality_report.json",
    }

    build_report(FIXTURE, **output_paths)

    assert all(path.exists() for path in output_paths.values())
    section_map = json.loads(output_paths["section_map_output_path"].read_text())
    chunks = json.loads(output_paths["ai_chunks_output_path"].read_text())
    quality = json.loads(output_paths["input_quality_output_path"].read_text())
    validation = json.loads(output_paths["validation_output_path"].read_text())
    assert section_map[0]["source_block_ids"]
    assert chunks[0]["source_block_ids"]
    assert quality["total_blocks"] == 5
    assert validation["outline_count"] == 1
    assert validation["section_count"] == 1
    assert validation["chunk_count"] == 1
    assert validation["source_map_entry_count"] == 5
    assert validation["input_quality_status"] == quality["status"]

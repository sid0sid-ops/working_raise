import json
from pathlib import Path

from bs4 import BeautifulSoup
from raise_html5_semantification.html_writer import build_source_map, render_document
from raise_html5_semantification.input_quality import build_input_quality_report
from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.models import Block
from raise_html5_semantification.section_builder import build_section_tree
from raise_html5_semantification.validator import validate_html_string


def _render(block: Block) -> tuple[BeautifulSoup, list]:
    nodes = build_section_tree([block])
    return BeautifulSoup(render_document(nodes), "lxml"), nodes


def test_image_block_with_path_renders_traceable_figure_and_img() -> None:
    block = Block(
        block_id="image-1",
        page_number=7,
        reading_order=12,
        block_type_guess="image",
        image_path="images/chart-1.png",
        alt_text="Research funding chart",
        bbox=[10, 20, 300, 240],
        confidence=0.91,
    )

    soup, nodes = _render(block)
    figure = soup.find("figure", attrs={"data-source-block": "image-1"})
    image = figure.find("img") if figure else None

    assert figure and image
    assert image.get("src") == "images/chart-1.png"
    assert image.get("alt") == "Research funding chart"
    for attribute in (
        "id",
        "data-page",
        "data-source-block",
        "data-block-type",
        "data-bbox",
        "data-confidence",
        "data-reading-order",
    ):
        assert figure.has_attr(attribute)
    source_entry = build_source_map(nodes, input_block_count=1).blocks[0]
    summary = validate_html_string(str(soup), expected_blocks=1)
    assert summary.image_count == 1
    assert summary.image_placeholder_count == 0
    assert source_entry.semantic_kind == "image"
    assert source_entry.html_element_ids == [
        "figure-image-1",
        "img-image-1",
        "figcaption-image-1",
    ]


def test_image_caption_renders_figcaption() -> None:
    block = Block(
        block_id="chart-1",
        block_type_guess="chart",
        image_src="assets/chart.svg",
        caption="Figure 1. Research grants by year",
    )

    soup, _ = _render(block)

    assert soup.find("figcaption").get_text(strip=True) == "Figure 1. Research grants by year"


def test_image_without_path_renders_placeholder_and_reports_quality() -> None:
    raw = {
        "block_id": "diagram-1",
        "page_number": 4,
        "reading_order": 8,
        "block_type_guess": "diagram",
        "caption": "Research workflow diagram",
    }
    block = Block.model_validate(raw)

    soup, _ = _render(block)
    figure = soup.find("figure", attrs={"data-block-type": "image-placeholder"})
    summary = validate_html_string(str(soup), expected_blocks=1)
    quality = build_input_quality_report([raw])

    assert figure
    assert figure.find("img") is None
    assert figure.find("figcaption").get_text(strip=True) == (
        "Image detected in source block, but no image file path was provided by upstream parser."
    )
    assert summary.image_placeholder_count == 1
    assert quality["image_like_block_count"] == 1
    assert quality["image_like_blocks_without_image_path"][0]["block_id"] == "diagram-1"


def test_loader_keeps_image_only_block_without_text(tmp_path: Path) -> None:
    input_path = tmp_path / "images.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "block_id": "figure-only",
                    "block_type_guess": "figure",
                    "image_path": "figures/only.png",
                }
            ]
        ),
        encoding="utf-8",
    )

    blocks = load_blocks(input_path)
    nodes = build_section_tree(blocks)

    assert len(blocks) == 1
    assert nodes[0].kind == "image"

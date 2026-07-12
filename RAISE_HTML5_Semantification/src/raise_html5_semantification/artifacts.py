from __future__ import annotations

import json
import math
from pathlib import Path

from bs4 import BeautifulSoup

from raise_html5_semantification.html_writer import render_node
from raise_html5_semantification.models import (
    AiChunk,
    ContentCounts,
    HtmlNode,
    SectionMapEntry,
)
from raise_html5_semantification.utils import ensure_parent, slugify


def _walk(node: HtmlNode) -> list[HtmlNode]:
    return [node, *(descendant for child in node.children for descendant in _walk(child))]


def _section_children(node: HtmlNode) -> list[HtmlNode]:
    return [child for child in node.children if child.kind == "heading"]


def _content_counts(nodes: list[HtmlNode]) -> ContentCounts:
    kinds = [node.kind for node in nodes]
    return ContentCounts(
        paragraphs=kinds.count("paragraph"),
        lists=kinds.count("unordered-list") + kinds.count("ordered-list"),
        tables=kinds.count("table"),
        asides=kinds.count("aside"),
    )


def build_section_map(nodes: list[HtmlNode]) -> list[SectionMapEntry]:
    sections: list[SectionMapEntry] = []

    def visit(node: HtmlNode, parent_section_id: str | None) -> None:
        if node.kind != "heading":
            return
        section_id = f"section-{slugify(node.block.block_id)}"
        descendants = _walk(node)
        pages = [
            item.block.page_number for item in descendants if item.block.page_number is not None
        ]
        child_sections = _section_children(node)
        sections.append(
            SectionMapEntry(
                section_id=section_id,
                heading=" ".join(node.block.text.split()),
                heading_level=min(max(node.level or 2, 1), 3),
                parent_section_id=parent_section_id,
                start_page=pages[0] if pages else None,
                end_page=pages[-1] if pages else None,
                start_block_id=node.block.block_id,
                end_block_id=descendants[-1].block.block_id,
                child_section_ids=[
                    f"section-{slugify(child.block.block_id)}" for child in child_sections
                ],
                source_block_ids=[item.block.block_id for item in descendants],
                content_counts=_content_counts(descendants),
            )
        )
        for child in child_sections:
            visit(child, section_id)

    for node in nodes:
        visit(node, None)
    return sections


def _recommended_task(heading: str) -> str:
    lowered = heading.lower()
    if "publication" in lowered or "journal" in lowered or "book chapter" in lowered:
        return "publication extraction"
    if "patent" in lowered:
        return "patent extraction"
    if "project" in lowered or "grant" in lowered:
        return "research funding extraction"
    if "faculty" in lowered:
        return "faculty information extraction"
    if "seminar" in lowered or "conference" in lowered:
        return "research activity extraction"
    return "semantic section extraction"


def _html_table_to_markdown(table) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""

    headers = rows[0]
    separator = ["---"] * len(headers)
    markdown_rows = []
    for row in rows[1:]:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[: len(headers)]
        markdown_rows.append("| " + " | ".join(row) + " |")
    hdr_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(separator) + " |"
    rows_body = "\n".join(markdown_rows)
    return f"\n{hdr_line}\n{sep_line}\n{rows_body}\n"


def build_ai_chunks(nodes: list[HtmlNode]) -> list[AiChunk]:
    chunks: list[AiChunk] = []

    def visit(node: HtmlNode) -> None:
        if node.kind != "heading":
            return
        direct_content = [child for child in node.children if child.kind != "heading"]
        chunk_node = node.model_copy(update={"children": direct_content})
        html = render_node(chunk_node)

        soup = BeautifulSoup(html, "lxml")
        for table in soup.find_all("table"):
            md_table = _html_table_to_markdown(table)
            table.replace_with(soup.new_string(md_table))
        plain_text = soup.get_text("\n", strip=True)

        chunk_nodes = [node, *direct_content]
        pages = sorted(
            {item.block.page_number for item in chunk_nodes if item.block.page_number is not None}
        )
        source_ids = [item.block.block_id for item in chunk_nodes]
        section_id = f"section-{slugify(node.block.block_id)}"
        chunks.append(
            AiChunk(
                chunk_id=f"chunk-{slugify(node.block.block_id)}",
                section_id=section_id,
                heading=" ".join(node.block.text.split()),
                heading_level=min(max(node.level or 2, 1), 3),
                html=html,
                plain_text=plain_text,
                source_pages=pages,
                source_block_ids=source_ids,
                token_estimate=max(1, math.ceil(len(plain_text) / 4)),
                recommended_task=_recommended_task(node.block.text),
            )
        )
        for child in _section_children(node):
            visit(child)

    for node in nodes:
        visit(node)
    return chunks


def write_models(items: list[SectionMapEntry] | list[AiChunk], output_path: str | Path) -> None:
    path = Path(output_path)
    ensure_parent(path)
    path.write_text(json.dumps([item.model_dump() for item in items], indent=2), encoding="utf-8")

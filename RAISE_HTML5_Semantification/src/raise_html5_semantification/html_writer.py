from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Template

from raise_html5_semantification.image_builder import image_source
from raise_html5_semantification.models import Block, HtmlNode, SourceMap, SourceMapEntry
from raise_html5_semantification.table_builder import table_rows
from raise_html5_semantification.templates import DOCUMENT_TEMPLATE
from raise_html5_semantification.utils import bbox_value, ensure_parent, escape_text, slugify


def block_label(block: Block, fallback: str = "content block") -> str:
    text = " ".join(block.text.split())
    if text:
        return text[:96]
    return fallback


def trace_attrs(
    block: Block,
    element_type: str,
    *,
    suffix: str | int | None = None,
    semantic_role: str | None = None,
    label: str | None = None,
    extra: dict[str, str | int | float | None] | None = None,
) -> str:
    element_id = f"{element_type}-{slugify(block.block_id)}"
    if suffix is not None:
        element_id = f"{element_id}-{slugify(str(suffix))}"
    attrs = {
        "id": element_id,
        "data-page": "" if block.page_number is None else str(block.page_number),
        "data-source-block": block.block_id,
        "data-block-type": block.block_type_guess or element_type,
        "data-bbox": bbox_value(block),
        "data-confidence": "" if block.confidence is None else f"{block.confidence:.3f}",
        "data-reading-order": "" if block.reading_order is None else str(block.reading_order),
        "data-semantic-role": semantic_role or element_type,
        "data-source-file": block.source_file or "",
        "data-font-size": "" if block.font_size is None else str(block.font_size),
        "data-font-name": block.font_name or "",
        "data-generated-block-id": str(block.generated_block_id).lower(),
    }
    if label:
        attrs["aria-label"] = label
    if extra:
        attrs.update({name: "" if value is None else str(value) for name, value in extra.items()})
    return " ".join(f'{name}="{escape_text(value)}"' for name, value in attrs.items())


LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)]|[a-zA-Z][.)])\s+")


def _list_items(text: str) -> list[str]:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not raw_lines:
        return [text.strip()]
    lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if i + 1 < len(raw_lines) and LIST_MARKER_RE.fullmatch(line + " "):
            lines.append(line + " " + raw_lines[i + 1])
            i += 2
        else:
            lines.append(line)
            i += 1
    items: list[str] = []
    for line in lines:
        items.append(LIST_MARKER_RE.sub("", line, count=1))
    return items


def render_table(block: Block) -> str:
    label = block.caption or f"Table on page {block.page_number or 'unknown'}"
    caption_id = f"caption-{slugify(block.block_id)}"
    attrs = trace_attrs(
        block,
        "table",
        semantic_role="table",
        extra={"aria-describedby": caption_id},
    )
    rows = table_rows(block)
    if not rows:
        figure_attrs = trace_attrs(block, "figure", semantic_role="unclear-table", label=label)
        figcaption_attrs = trace_attrs(block, "figcaption", semantic_role="unclear-table-caption")
        pre_attrs = trace_attrs(block, "pre", semantic_role="preserved-table-text")
        return (
            f"<figure {figure_attrs}>"
            f"<figcaption {figcaption_attrs}>"
            "Unclear table-like block preserved as text.</figcaption>"
            f"<pre {pre_attrs}>{escape_text(block.text)}</pre></figure>"
        )

    header = rows[0]
    body_rows = rows[1:]
    caption_attrs = trace_attrs(block, "caption", semantic_role="table-caption")
    thead_attrs = trace_attrs(block, "thead", semantic_role="table-header-group")
    header_row_attrs = trace_attrs(block, "tr", suffix="header", semantic_role="table-header-row")
    tbody_attrs = trace_attrs(block, "tbody", semantic_role="table-body-group")
    parts = [f"<table {attrs}>", f"<caption {caption_attrs}>{escape_text(label)}</caption>"]
    parts.append(f"<thead {thead_attrs}><tr {header_row_attrs}>")
    for column_index, cell in enumerate(header, start=1):
        th_attrs = trace_attrs(
            block,
            "th",
            suffix=column_index,
            semantic_role="table-header-cell",
            extra={"scope": "col", "data-column-index": column_index},
        )
        parts.append(f"<th {th_attrs}>{escape_text(cell)}</th>")
    parts.append(f"</tr></thead><tbody {tbody_attrs}>")
    for row_index, row in enumerate(body_rows, start=1):
        row_attrs = trace_attrs(
            block,
            "tr",
            suffix=f"row-{row_index}",
            semantic_role="table-data-row",
            extra={"data-row-index": row_index},
        )
        parts.append(f"<tr {row_attrs}>")
        for column_index, cell in enumerate(row, start=1):
            td_attrs = trace_attrs(
                block,
                "td",
                suffix=f"{row_index}-{column_index}",
                semantic_role="table-data-cell",
                extra={"data-row-index": row_index, "data-column-index": column_index},
            )
            parts.append(f"<td {td_attrs}>{escape_text(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def render_image(block: Block) -> str:
    source = image_source(block)
    caption = block.caption or block.text or block.alt_text
    figure_role = "image-figure" if source else "image-placeholder"
    figure_attrs = trace_attrs(
        block,
        "figure",
        semantic_role=figure_role,
        label=caption or "Image block",
        extra={"data-block-type": block.block_type_guess or figure_role},
    )
    figcaption_attrs = trace_attrs(
        block,
        "figcaption",
        semantic_role="image-caption" if source else "image-placeholder-caption",
    )
    if not source:
        placeholder_attrs = trace_attrs(
            block,
            "figure",
            semantic_role="image-placeholder",
            label=caption or "Image placeholder",
            extra={"data-block-type": "image-placeholder"},
        )
        message = (
            "Image detected in source block, but no image file path was provided by "
            "upstream parser."
        )
        return (
            f"<figure {placeholder_attrs}>"
            f"<figcaption {figcaption_attrs}>{message}</figcaption></figure>"
        )

    alt_text = block.alt_text or caption or f"Image from source block {block.block_id}"
    image_attrs = trace_attrs(
        block,
        "img",
        semantic_role="image",
        extra={"src": source, "alt": alt_text},
    )
    caption_text = caption or alt_text
    return (
        f"<figure {figure_attrs}><img {image_attrs}>"
        f"<figcaption {figcaption_attrs}>{escape_text(caption_text)}</figcaption></figure>"
    )


def render_node(node: HtmlNode, depth: int = 0, section_path: tuple[int, ...] = ()) -> str:
    block = node.block
    indent = "  " * depth
    if node.kind == "heading":
        level = min(max(node.level or 2, 1), 3)
        heading_id = f"h{level}-{slugify(block.block_id)}"
        label = block_label(block, "section heading")
        section_attrs = trace_attrs(
            block,
            "section",
            semantic_role="section",
            label=label,
            extra={
                "aria-labelledby": heading_id,
                "data-section-level": level,
                "data-section-path": ".".join(str(part) for part in section_path),
                "data-section-title": label,
            },
        )
        heading_attrs = trace_attrs(
            block,
            f"h{level}",
            semantic_role="heading",
            extra={"data-heading-level": level},
        )
        children = "\n".join(
            render_node(child, depth + 1, (*section_path, child_index))
            for child_index, child in enumerate(node.children, start=1)
        )
        heading = f"{indent}<h{level} {heading_attrs}>{escape_text(block.text)}</h{level}>"
        if children:
            return f"{indent}<section {section_attrs}>\n{heading}\n{children}\n{indent}</section>"
        return f"{indent}<section {section_attrs}>\n{heading}\n{indent}</section>"

    if node.kind == "table":
        return indent + render_table(block)
    if node.kind == "image":
        return indent + render_image(block)
    if node.kind == "aside":
        attrs = trace_attrs(
            block,
            "aside",
            semantic_role="low-confidence-note",
            label=block_label(block),
        )
        return f"{indent}<aside {attrs}>{escape_text(block.text)}</aside>"
    if node.kind in {"unordered-list", "ordered-list"}:
        tag = "ol" if node.kind == "ordered-list" else "ul"
        items = []
        for item_index, item in enumerate(_list_items(block.text), start=1):
            li_attrs = trace_attrs(
                block,
                "li",
                suffix=item_index,
                semantic_role="list-item",
                extra={"data-list-item-index": item_index},
            )
            items.append(f"<li {li_attrs}>{escape_text(item)}</li>")
        list_attrs = trace_attrs(
            block,
            tag,
            semantic_role=node.kind,
            label=block_label(block, "list"),
        )
        return f"{indent}<{tag} {list_attrs}>{''.join(items)}</{tag}>"
    attrs = trace_attrs(block, "p", semantic_role="paragraph", label=block_label(block))
    return f"{indent}<p {attrs}>{escape_text(block.text)}</p>"


def _outline_items(nodes: list[HtmlNode], max_level: int) -> str:
    parts: list[str] = []
    for node in nodes:
        if node.kind != "heading":
            continue
        level = min(max(node.level or 2, 1), 3)
        if level > max_level:
            continue
        heading_id = f"h{level}-{slugify(node.block.block_id)}"
        label = block_label(node.block, "Untitled section")
        parts.append(
            f'<li><a href="#{escape_text(heading_id)}" data-source-block="'
            f'{escape_text(node.block.block_id)}">{escape_text(label)}</a>'
        )
        nested = _outline_items(node.children, max_level)
        if nested:
            parts.append(f"<ol>{nested}</ol>")
        parts.append("</li>")
    return "".join(parts)


def render_outline(nodes: list[HtmlNode], outline_depth: int = 2) -> str:
    if outline_depth not in {1, 2, 3}:
        raise ValueError("outline_depth must be 1, 2, or 3")
    requested_count = sum(
        1
        for node in _walk_nodes(nodes)
        if node.kind == "heading" and min(max(node.level or 2, 1), 3) <= outline_depth
    )
    effective_depth = 2 if outline_depth == 3 and requested_count > 300 else outline_depth
    items = _outline_items(nodes, effective_depth)
    outline_count = sum(
        1
        for node in _walk_nodes(nodes)
        if node.kind == "heading" and min(max(node.level or 2, 1), 3) <= effective_depth
    )
    total_heading_count = sum(1 for node in _walk_nodes(nodes) if node.kind == "heading")
    note = ""
    if total_heading_count > outline_count and (requested_count > 300 or outline_depth <= 2):
        note = (
            '<p class="outline-note">Detailed subsection headings are preserved in the '
            "document but hidden from the default outline.</p>"
        )
    return (
        '<nav id="document-outline" aria-label="Document outline">'
        f"<details><summary>Document outline ({outline_count} sections)</summary>"
        f'{note}<ol>{items or ""}</ol></details></nav>'
    )


def _walk_nodes(nodes: list[HtmlNode]):
    for node in nodes:
        yield node
        yield from _walk_nodes(node.children)


def render_document(
    nodes: list[HtmlNode], title: str = "RAISE Semantic HTML Report", outline_depth: int = 2
) -> str:
    body = "\n".join(
        render_node(node, 2, (node_index,)) for node_index, node in enumerate(nodes, start=1)
    )
    outline = render_outline(nodes, outline_depth=outline_depth)
    return Template(DOCUMENT_TEMPLATE).render(title=title, body=body, outline=outline)


def _node_element_ids(node: HtmlNode) -> list[str]:
    block_slug = slugify(node.block.block_id)
    if node.kind == "heading":
        level = min(max(node.level or 2, 1), 3)
        return [f"section-{block_slug}", f"h{level}-{block_slug}"]
    if node.kind == "table":
        rows = table_rows(node.block)
        if not rows:
            return [f"figure-{block_slug}", f"figcaption-{block_slug}", f"pre-{block_slug}"]
        element_ids = [
            f"table-{block_slug}",
            f"caption-{block_slug}",
            f"thead-{block_slug}",
            f"tr-{block_slug}-header",
        ]
        element_ids.extend(f"th-{block_slug}-{index}" for index in range(1, len(rows[0]) + 1))
        element_ids.append(f"tbody-{block_slug}")
        for row_index, row in enumerate(rows[1:], start=1):
            element_ids.append(f"tr-{block_slug}-row-{row_index}")
            element_ids.extend(
                f"td-{block_slug}-{row_index}-{column_index}"
                for column_index in range(1, len(row) + 1)
            )
        return element_ids
    if node.kind == "image":
        element_ids = [f"figure-{block_slug}"]
        if image_source(node.block):
            element_ids.append(f"img-{block_slug}")
        element_ids.append(f"figcaption-{block_slug}")
        return element_ids
    if node.kind in {"unordered-list", "ordered-list"}:
        tag = "ol" if node.kind == "ordered-list" else "ul"
        return [f"{tag}-{block_slug}"] + [
            f"li-{block_slug}-{index}" for index, _ in enumerate(_list_items(node.block.text), 1)
        ]
    tag = "aside" if node.kind == "aside" else "p"
    return [f"{tag}-{block_slug}"]


def build_source_map(nodes: list[HtmlNode], input_block_count: int = 0) -> SourceMap:
    entries: list[SourceMapEntry] = []

    def visit(node: HtmlNode, section_path: tuple[int, ...]) -> None:
        element_ids = _node_element_ids(node)
        entries.append(
            SourceMapEntry(
                block_id=node.block.block_id,
                page_number=node.block.page_number,
                reading_order=node.block.reading_order,
                block_type=node.block.block_type_guess,
                semantic_kind=node.kind,
                heading_level=node.level,
                section_path=".".join(str(part) for part in section_path),
                primary_element_id=element_ids[0],
                html_element_ids=element_ids,
            )
        )
        for child_index, child in enumerate(node.children, start=1):
            child_path = (*section_path, child_index) if child.kind == "heading" else section_path
            visit(child, child_path)

    for node_index, node in enumerate(nodes, start=1):
        visit(node, (node_index,))
    source_file = next(
        (node.block.source_file for node in _walk_nodes(nodes) if node.block.source_file), None
    )
    return SourceMap(
        source_file=source_file,
        input_block_count=input_block_count or len(entries),
        blocks=entries,
    )


def write_source_map(
    nodes: list[HtmlNode], output_path: str | Path, input_block_count: int = 0
) -> SourceMap:
    path = Path(output_path)
    ensure_parent(path)
    source_map = build_source_map(nodes, input_block_count=input_block_count)
    path.write_text(json.dumps(source_map.model_dump(), indent=2), encoding="utf-8")
    return source_map


def write_html(nodes: list[HtmlNode], output_path: str | Path, outline_depth: int = 2) -> str:
    path = Path(output_path)
    ensure_parent(path)
    html = render_document(nodes, outline_depth=outline_depth)
    path.write_text(html, encoding="utf-8")
    return html

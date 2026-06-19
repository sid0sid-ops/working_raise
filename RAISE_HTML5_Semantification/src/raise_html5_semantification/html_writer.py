from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from raise_html5_semantification.models import Block, HtmlNode
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


def _list_items(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text.strip()]
    items: list[str] = []
    for line in lines:
        stripped = line.lstrip("-*• ")
        if stripped[:2].rstrip(".").isdigit():
            stripped = stripped.split(" ", 1)[-1]
        items.append(stripped)
    return items


def render_table(block: Block) -> str:
    label = block_label(block, "table block")
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
        return (
            f"<figure {figure_attrs}>"
            f'<figcaption id="{caption_id}">'
            "Unclear table-like block preserved as text.</figcaption>"
            f"<pre>{escape_text(block.text)}</pre></figure>"
        )

    header = rows[0]
    body_rows = rows[1:]
    parts = [f"<table {attrs}>", f'<caption id="{caption_id}">{escape_text(label)}</caption>']
    parts.append("<thead><tr>")
    for column_index, cell in enumerate(header, start=1):
        th_attrs = trace_attrs(
            block,
            "th",
            suffix=column_index,
            semantic_role="table-header-cell",
            extra={"scope": "col", "data-column-index": column_index},
        )
        parts.append(f"<th {th_attrs}>{escape_text(cell)}</th>")
    parts.append("</tr></thead><tbody>")
    for row_index, row in enumerate(body_rows, start=1):
        parts.append("<tr>")
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
            return f'{indent}<section {section_attrs}>\n{heading}\n{children}\n{indent}</section>'
        return f'{indent}<section {section_attrs}>\n{heading}\n{indent}</section>'

    if node.kind == "table":
        return indent + render_table(block)
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


def _outline_items(nodes: list[HtmlNode]) -> str:
    parts: list[str] = []
    for node in nodes:
        if node.kind != "heading":
            continue
        level = min(max(node.level or 2, 1), 3)
        heading_id = f"h{level}-{slugify(node.block.block_id)}"
        label = block_label(node.block, "Untitled section")
        parts.append(
            f'<li><a href="#{escape_text(heading_id)}" data-source-block="'
            f'{escape_text(node.block.block_id)}">{escape_text(label)}</a>'
        )
        nested = _outline_items(node.children)
        if nested:
            parts.append(f"<ol>{nested}</ol>")
        parts.append("</li>")
    return "".join(parts)


def render_outline(nodes: list[HtmlNode]) -> str:
    items = _outline_items(nodes)
    if not items:
        return ""
    return f'<nav id="document-outline" aria-label="Document outline"><ol>{items}</ol></nav>'


def render_document(nodes: list[HtmlNode], title: str = "RAISE Semantic HTML Report") -> str:
    body = "\n".join(
        render_node(node, 2, (node_index,)) for node_index, node in enumerate(nodes, start=1)
    )
    outline = render_outline(nodes)
    return Template(DOCUMENT_TEMPLATE).render(title=title, body=body, outline=outline)


def write_html(nodes: list[HtmlNode], output_path: str | Path) -> str:
    path = Path(output_path)
    ensure_parent(path)
    html = render_document(nodes)
    path.write_text(html, encoding="utf-8")
    return html

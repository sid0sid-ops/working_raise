from __future__ import annotations

import json
import re
from collections import Counter
from contextlib import suppress
from pathlib import Path
from statistics import median
from typing import Any

from raise_html5_semantification.models import FIELD_ALIASES
from raise_html5_semantification.utils import ensure_parent, normalized_type

DOT_LEADER_RE = re.compile(r"\.{4,}")


def _value(raw: dict[str, Any], field: str) -> Any:
    for alias in FIELD_ALIASES[field]:
        value = raw.get(alias)
        if value is not None and value != "":
            return value
    return None


def _reference(raw: dict[str, Any], index: int) -> dict[str, Any]:
    text = str(_value(raw, "text") or "")
    return {
        "block_id": _value(raw, "block_id"),
        "input_index": index,
        "page_number": _value(raw, "page_number"),
        "text_excerpt": " ".join(text.split())[:120],
    }


def _likely_ocr_noise(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    letters = sum(character.isalpha() for character in stripped)
    digits = sum(character.isdigit() for character in stripped)
    symbols = sum(not character.isalnum() and not character.isspace() for character in stripped)
    if digits and not letters and symbols <= 2:
        return False
    return (letters == 0 and symbols > 0) or (
        len(stripped) >= 6 and symbols >= 3 and letters / max(len(stripped), 1) < 0.2
    )


def build_input_quality_report(raw_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(raw_blocks)
    missing_block_id = 0
    missing_page = 0
    missing_bbox = 0
    missing_font = 0
    missing_confidence = 0
    block_ids: list[str] = []
    reading_orders: list[tuple[int, int]] = []
    page_counts: Counter[int] = Counter()
    ocr_noise: list[dict[str, Any]] = []
    toc_blocks: list[dict[str, Any]] = []
    unstructured_tables: list[dict[str, Any]] = []
    table_like_count = 0
    image_like_count = 0
    images_without_source: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_blocks, start=1):
        block_id = _value(raw, "block_id")
        page = _value(raw, "page_number")
        bbox = _value(raw, "bbox")
        if bbox is None and all(raw.get(coord) is not None for coord in ("x0", "y0", "x1", "y1")):
            bbox = [raw[coord] for coord in ("x0", "y0", "x1", "y1")]
        if block_id is None:
            missing_block_id += 1
        else:
            block_ids.append(str(block_id))
        if page is None:
            missing_page += 1
        else:
            try:
                page_counts[int(page)] += 1
            except (TypeError, ValueError):
                missing_page += 1
        missing_bbox += bbox is None
        missing_font += _value(raw, "font_size") is None
        missing_confidence += _value(raw, "confidence") is None

        order = _value(raw, "reading_order")
        if order is not None:
            with suppress(TypeError, ValueError):
                reading_orders.append((index, int(order)))
        text = str(_value(raw, "text") or "")
        if _likely_ocr_noise(text):
            ocr_noise.append(_reference(raw, index))
        if DOT_LEADER_RE.search(text) or text.strip().lower() == "contents":
            toc_blocks.append(_reference(raw, index))

        guess = normalized_type(str(_value(raw, "block_type_guess") or ""))
        has_table_data = _value(raw, "rows") is not None or _value(raw, "table") is not None
        if guess in {"table", "table-candidate"}:
            table_like_count += 1
            if not has_table_data:
                unstructured_tables.append(_reference(raw, index))
        has_image_metadata = any(
            _value(raw, field) is not None
            for field in ("image_path", "image_src", "caption", "alt_text")
        )
        if guess in {"image", "figure", "chart", "diagram"} or has_image_metadata:
            image_like_count += 1
            if _value(raw, "image_path") is None and _value(raw, "image_src") is None:
                images_without_source.append(_reference(raw, index))

    duplicate_ids = sorted(block_id for block_id, count in Counter(block_ids).items() if count > 1)
    order_values = [order for _, order in reading_orders]
    duplicate_orders = sorted(order for order, count in Counter(order_values).items() if count > 1)
    decreases = [
        {"input_index": current[0], "previous_order": previous[1], "current_order": current[1]}
        for previous, current in zip(reading_orders, reading_orders[1:], strict=False)
        if current[1] < previous[1]
    ]
    page_values = list(page_counts.values())
    high_page_threshold = max(100, int(median(page_values) * 3)) if page_values else 100
    high_pages = [
        {"page_number": page, "block_count": count}
        for page, count in sorted(page_counts.items())
        if count > high_page_threshold
    ]
    unique_pages = sorted(page_counts.keys())
    missing_pages_in_sequence = []
    if unique_pages:
        full_range = set(range(unique_pages[0], unique_pages[-1] + 1))
        missing_pages_in_sequence = sorted(full_range - set(unique_pages))

    metadata_missing = (
        missing_block_id + missing_page + missing_bbox + missing_font + missing_confidence
    )
    has_warnings = (
        duplicate_ids
        or decreases
        or metadata_missing
        or unstructured_tables
        or images_without_source
        or missing_pages_in_sequence
    )
    status = "warning" if has_warnings else "ok"
    return {
        "status": status,
        "total_blocks": total,
        "blocks_missing_block_id": missing_block_id,
        "blocks_missing_page_number": missing_page,
        "blocks_missing_bbox": missing_bbox,
        "blocks_missing_font_size": missing_font,
        "blocks_missing_confidence": missing_confidence,
        "duplicate_block_ids": duplicate_ids,
        "reading_order_anomalies": {
            "blocks_missing_reading_order": total - len(reading_orders),
            "duplicate_reading_orders": duplicate_orders,
            "decreasing_sequences": decreases,
        },
        "unusually_high_block_count_threshold": high_page_threshold,
        "pages_with_unusually_high_block_count": high_pages,
        "missing_pages_in_sequence": missing_pages_in_sequence,
        "likely_ocr_noise_blocks": ocr_noise,
        "likely_toc_blocks": toc_blocks,
        "table_like_block_count": table_like_count,
        "table_like_blocks_without_table_data": unstructured_tables,
        "image_like_block_count": image_like_count,
        "image_like_blocks_without_image_path": images_without_source,
    }


def write_input_quality_report(report: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    ensure_parent(path)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from raise_html5_semantification.models import Block
from raise_html5_semantification.utils import slugify


class InputValidationError(ValueError):
    """Raised when target block JSON does not match the expected structure."""


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_schema(schema_path: Path | None = None) -> dict[str, Any]:
    if schema_path is not None:
        return _read_json(schema_path)
    schema_resource = resources.files("raise_html5_semantification").joinpath(
        "semantic_input.schema.json"
    )
    with schema_resource.open("r", encoding="utf-8") as file:
        return json.load(file)


BLOCK_CONTAINER_KEYS = (
    "blocks",
    "target_blocks",
    "content_blocks",
    "pages",
    "items",
    "elements",
    "paragraphs",
    "lines",
    "records",
)

TEXT_KEYS = {"text", "content", "block_text", "raw_text", "value", "line", "paragraph"}
TABLE_KEYS = {"rows", "table", "table_rows", "tableRows", "table_data", "tableData", "cells"}
IMAGE_KEYS = {
    "image_path",
    "imagePath",
    "image_src",
    "imageSrc",
    "caption",
    "image_caption",
    "figure_caption",
    "alt_text",
    "altText",
    "image_alt",
}


def _looks_like_block(value: dict[str, Any]) -> bool:
    keys = set(value)
    if keys & TEXT_KEYS or keys & TABLE_KEYS or keys & IMAGE_KEYS:
        return True
    metadata_keys = {
        "block_id",
        "id",
        "page_number",
        "page",
        "bbox",
        "font_size",
        "type",
        "block_type_guess",
    }
    return bool(keys & metadata_keys)


def _candidate_score(items: list[Any]) -> int:
    return sum(1 for item in items if isinstance(item, dict) and _looks_like_block(item))


def _find_best_block_list(raw: Any) -> list[dict[str, Any]] | None:
    candidates: list[list[Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            if _candidate_score(value):
                candidates.append(value)
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for key in BLOCK_CONTAINER_KEYS:
                nested = value.get(key)
                if isinstance(nested, list) and _candidate_score(nested):
                    candidates.append(nested)
            for nested in value.values():
                visit(nested)

    visit(raw)
    if not candidates:
        return None
    best = max(candidates, key=lambda items: (_candidate_score(items), len(items)))
    return [item for item in best if isinstance(item, dict)]


def extract_blocks(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list) and _candidate_score(raw):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in BLOCK_CONTAINER_KEYS:
            value = raw.get(key)
            if isinstance(value, list) and _candidate_score(value):
                return [item for item in value if isinstance(item, dict)]
        if _looks_like_block(raw):
            return [raw]
    inferred = _find_best_block_list(raw)
    if inferred:
        return inferred
    raise InputValidationError(
        "Input JSON must contain at least one text-like or table-like block."
    )


def validate_raw_input(raw: Any, schema: dict[str, Any] | None = None) -> None:
    active_schema = schema or load_schema()
    validator = Draft202012Validator(active_schema)
    errors = sorted(validator.iter_errors(raw), key=lambda error: list(error.path))
    if errors:
        messages = []
        for error in errors[:10]:
            location = ".".join(str(part) for part in error.path) or "$"
            messages.append(f"{location}: {error.message}")
        raise InputValidationError("; ".join(messages))


def normalize_raw_blocks(
    raw_blocks: list[dict[str, Any]], source_file: str | None = None
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw_block in enumerate(raw_blocks, start=1):
        block = dict(raw_block)
        if not block.get("block_id") and not block.get("id"):
            page = block.get("page_number") or block.get("page") or "unknown"
            text_seed = str(
                block.get("text")
                or block.get("content")
                or block.get("block_text")
                or block.get("raw_text")
                or block.get("caption")
                or block.get("alt_text")
                or "block"
            )
            block["block_id"] = f"generated-p{page}-{index:04d}-{slugify(text_seed[:32])}"
            block["generated_block_id"] = True
        if source_file and not block.get("source_file"):
            block["source_file"] = source_file
        if block.get("reading_order") is None and block.get("order") is None:
            block["reading_order"] = index
        normalized.append(block)
    return normalized


def load_blocks(input_path: str | Path, schema_path: str | Path | None = None) -> list[Block]:
    path = Path(input_path)
    raw = _read_json(path)
    schema = load_schema(Path(schema_path)) if schema_path else load_schema()
    validate_raw_input(raw, schema)
    source_file = raw.get("source_file") if isinstance(raw, dict) else None
    raw_blocks = normalize_raw_blocks(extract_blocks(raw), source_file=source_file)
    blocks = [Block.model_validate(item) for item in raw_blocks]
    return sorted(blocks, key=lambda block: (block.reading_order is None, block.reading_order or 0))


def load_raw_blocks(
    input_path: str | Path, schema_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Load validated blocks without generating IDs or filling metadata."""
    path = Path(input_path)
    raw = _read_json(path)
    schema = load_schema(Path(schema_path)) if schema_path else load_schema()
    validate_raw_input(raw, schema)
    return extract_blocks(raw)

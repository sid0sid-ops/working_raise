from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FIELD_ALIASES = {
    "block_id": ("block_id", "id", "blockId", "blockID", "uid", "uuid"),
    "page_number": ("page_number", "page", "page_num", "pageNumber", "page_no"),
    "text": ("text", "content", "block_text", "raw_text", "value", "line", "paragraph"),
    "bbox": ("bbox", "bounding_box", "bounds", "box"),
    "font_size": ("font_size", "fontsize", "fontSize", "size"),
    "font_name": ("font_name", "font", "fontName", "font_family"),
    "is_bold": ("is_bold", "bold", "isBold"),
    "is_italic": ("is_italic", "italic", "isItalic"),
    "reading_order": ("reading_order", "order", "readingOrder", "sequence", "index"),
    "block_type_guess": ("block_type_guess", "type", "block_type", "label", "category", "role"),
    "confidence": ("confidence", "score", "probability", "ocr_confidence"),
    "section_hint": ("section_hint", "section", "heading_hint", "sectionHint"),
    "source_file": ("source_file", "source", "file", "filename", "document"),
    "rows": ("rows", "table_rows", "tableRows", "cells"),
    "table": ("table", "table_data", "tableData"),
}


class Block(BaseModel):
    """Prepared annual-report content block from upstream modules."""

    model_config = ConfigDict(extra="allow")

    block_id: str = Field(..., min_length=1)
    page_number: int | None = None
    text: str = ""
    bbox: list[float] | tuple[float, ...] | str | None = None
    x0: float | None = None
    y0: float | None = None
    x1: float | None = None
    y1: float | None = None
    font_size: float | None = None
    font_name: str | None = None
    is_bold: bool | None = None
    is_italic: bool | None = None
    reading_order: int | None = None
    block_type_guess: str | None = None
    confidence: float | None = None
    section_hint: str | None = None
    source_file: str | None = None
    rows: list[list[Any]] | None = None
    table: list[list[Any]] | None = None
    generated_block_id: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        for canonical, aliases in FIELD_ALIASES.items():
            if normalized.get(canonical) is not None:
                continue
            for alias in aliases:
                if alias in normalized and normalized[alias] is not None:
                    normalized[canonical] = normalized[alias]
                    break
        return normalized

    @field_validator("text", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("block_type_guess", "section_hint", "font_name", "source_file", mode="before")
    @classmethod
    def normalize_optional_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("confidence")
    @classmethod
    def normalize_confidence(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))


class Document(BaseModel):
    blocks: list[Block]
    source_file: str | None = None


class HtmlNode(BaseModel):
    kind: str
    block: Block
    level: int | None = None
    children: list[HtmlNode] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    severity: str
    message: str
    block_id: str | None = None


class ValidationSummary(BaseModel):
    ok: bool
    input_block_count: int = 0
    html_element_count: int = 0
    traceable_element_count: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)

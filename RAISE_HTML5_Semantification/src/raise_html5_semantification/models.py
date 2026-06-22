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
    "image_path": ("image_path", "imagePath"),
    "image_src": ("image_src", "imageSrc"),
    "caption": ("caption", "image_caption", "figure_caption"),
    "alt_text": ("alt_text", "altText", "image_alt"),
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
    rows: list[Any] | dict[str, Any] | None = None
    table: list[Any] | dict[str, Any] | None = None
    image_path: str | None = None
    image_src: str | None = None
    caption: str | None = None
    alt_text: str | None = None
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

    @field_validator(
        "block_type_guess",
        "section_hint",
        "font_name",
        "source_file",
        "image_path",
        "image_src",
        "caption",
        "alt_text",
        mode="before",
    )
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


class SourceMapEntry(BaseModel):
    block_id: str
    page_number: int | None = None
    reading_order: int | None = None
    block_type: str | None = None
    semantic_kind: str
    heading_level: int | None = None
    section_path: str = ""
    primary_element_id: str
    html_element_ids: list[str] = Field(default_factory=list)


class SourceMap(BaseModel):
    source_file: str | None = None
    input_block_count: int = 0
    blocks: list[SourceMapEntry] = Field(default_factory=list)


class ContentCounts(BaseModel):
    paragraphs: int = 0
    lists: int = 0
    tables: int = 0
    asides: int = 0


class SectionMapEntry(BaseModel):
    section_id: str
    heading: str
    heading_level: int
    parent_section_id: str | None = None
    start_page: int | None = None
    end_page: int | None = None
    start_block_id: str
    end_block_id: str
    child_section_ids: list[str] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    content_counts: ContentCounts = Field(default_factory=ContentCounts)


class AiChunk(BaseModel):
    chunk_id: str
    section_id: str
    heading: str
    heading_level: int
    html: str
    plain_text: str
    source_pages: list[int] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    token_estimate: int = 0
    recommended_task: str = "semantic section extraction"


class ValidationIssue(BaseModel):
    severity: str
    message: str
    block_id: str | None = None


class ValidationSummary(BaseModel):
    ok: bool
    input_block_count: int = 0
    html_element_count: int = 0
    traceable_element_count: int = 0
    heading_count_by_level: dict[str, int] = Field(default_factory=dict)
    outline_count: int = 0
    section_count: int = 0
    chunk_count: int = 0
    source_map_entry_count: int = 0
    input_quality_status: str = "unknown"
    image_count: int = 0
    image_placeholder_count: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)

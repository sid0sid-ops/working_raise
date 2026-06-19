from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "block"


def escape_text(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def bbox_value(block: Any) -> str:
    if getattr(block, "bbox", None) is not None:
        return str(block.bbox)
    coords = [block.x0, block.y0, block.x1, block.y1]
    if all(coord is not None for coord in coords):
        return ",".join(str(coord) for coord in coords)
    return ""


def normalized_type(value: str | None) -> str:
    return (value or "paragraph").strip().lower().replace("_", "-")


def split_nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]

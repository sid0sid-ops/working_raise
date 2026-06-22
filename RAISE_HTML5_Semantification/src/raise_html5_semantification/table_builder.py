from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from raise_html5_semantification.models import Block
from raise_html5_semantification.utils import normalized_type, split_nonempty_lines


def is_table_like(block: Block) -> bool:
    return normalized_type(block.block_type_guess) in {"table", "table-candidate"}


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return "; ".join(f"{key}: {_cell_text(item)}" for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "; ".join(_cell_text(item) for item in value)
    return str(value).strip()


def _structured_rows(raw: list[Any] | dict[str, Any]) -> list[list[str]] | None:
    if isinstance(raw, Mapping):
        return [["Field", "Value"]] + [
            [_cell_text(key), _cell_text(value)] for key, value in raw.items()
        ]
    if not raw:
        return None
    if all(isinstance(row, Mapping) for row in raw):
        headers = list(raw[0].keys())
        if all(set(row.keys()) == set(headers) for row in raw):
            return [headers] + [[_cell_text(row.get(header)) for header in headers] for row in raw]
        return None
    if all(isinstance(row, Sequence) and not isinstance(row, (str, bytes)) for row in raw):
        rows = [[_cell_text(cell) for cell in row] for row in raw if row]
        if not rows:
            return None
        width = max(len(row) for row in rows)
        return [row + [""] * (width - len(row)) for row in rows]
    return None


def table_rows(block: Block) -> list[list[str]] | None:
    raw_rows = block.rows or block.table
    if raw_rows:
        return _structured_rows(raw_rows)

    lines = split_nonempty_lines(block.text)
    if not lines:
        return None

    delimiter = "|" if any("|" in line for line in lines) else None
    if delimiter:
        rows = []
        for line in lines:
            cells = [cell.strip() for cell in line.split("|")]
            if line.startswith("|"):
                cells = cells[1:]
            if line.endswith("|"):
                cells = cells[:-1]
            rows.append(cells)
        width = max(len(row) for row in rows)
        return [row + [""] * (width - len(row)) for row in rows]

    parsed = list(csv.reader(StringIO(block.text)))
    if len(parsed) > 1:
        width = max(len(row) for row in parsed)
        return [[cell.strip() for cell in row] + [""] * (width - len(row)) for row in parsed]

    return None

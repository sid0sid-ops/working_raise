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
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return "; ".join(_cell_text(item) for item in value)
    return str(value).strip()


def merge_text_wrapped_rows(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return rows
    merged: list[list[str]] = []
    for row in rows:
        if not row:
            continue
        if not merged:
            merged.append(row)
            continue

        prev_row = merged[-1]
        # A row is a continuation if the first cell (or multiple leading cells) is empty,
        # but at least one cell has text.
        if len(row) == len(prev_row) and not row[0].strip() and any(cell.strip() for cell in row):
            new_row = []
            for prev_cell, curr_cell in zip(prev_row, row, strict=False):
                c_strip = curr_cell.strip()
                if c_strip:
                    # Append with space
                    new_row.append(f"{prev_cell} {c_strip}".strip())
                else:
                    new_row.append(prev_cell)
            merged[-1] = new_row
            continue
        merged.append(row)
    return merged


def _structured_rows(raw: list[Any] | dict[str, Any]) -> list[list[str]] | None:
    if isinstance(raw, Mapping):
        return [["Field", "Value"]] + [
            [_cell_text(key), _cell_text(value)] for key, value in raw.items()
        ]
    if not raw:
        return None
    if all(isinstance(row, Mapping) for row in raw):
        headers = []
        for row in raw:
            for key in row:
                if key not in headers:
                    headers.append(key)
        rows = [headers] + [[_cell_text(row.get(header)) for header in headers] for row in raw]
        return merge_text_wrapped_rows(rows)
    if all(isinstance(row, Sequence) and not isinstance(row, str | bytes) for row in raw):
        rows = [[_cell_text(cell) for cell in row] for row in raw if row]
        if not rows:
            return None
        width = max(len(row) for row in rows)
        padded = [row + [""] * (width - len(row)) for row in rows]
        return merge_text_wrapped_rows(padded)
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
        padded = [row + [""] * (width - len(row)) for row in rows]
        return merge_text_wrapped_rows(padded)

    parsed = list(csv.reader(StringIO(block.text)))
    if len(parsed) > 1:
        width = max(len(row) for row in parsed)
        padded = [[cell.strip() for cell in row] + [""] * (width - len(row)) for row in parsed]
        return merge_text_wrapped_rows(padded)

    return None

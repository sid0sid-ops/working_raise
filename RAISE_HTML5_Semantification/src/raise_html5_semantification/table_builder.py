from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from raise_html5_semantification.models import Block
from raise_html5_semantification.utils import normalized_type, split_nonempty_lines


def is_table_like(block: Block) -> bool:
    return normalized_type(block.block_type_guess) in {"table", "table-candidate"}


def table_rows(block: Block) -> list[list[str]] | None:
    raw_rows: list[list[Any]] | None = block.rows or block.table
    if raw_rows:
        return [[str(cell).strip() for cell in row] for row in raw_rows if row]

    lines = split_nonempty_lines(block.text)
    if not lines:
        return None

    delimiter = "|" if any("|" in line for line in lines) else None
    if delimiter:
        rows = [[cell.strip() for cell in line.split("|") if cell.strip()] for line in lines]
        return rows if all(len(row) == len(rows[0]) for row in rows) else None

    parsed = list(csv.reader(StringIO(block.text)))
    if len(parsed) > 1 and all(len(row) == len(parsed[0]) for row in parsed):
        return [[cell.strip() for cell in row] for row in parsed]

    return None

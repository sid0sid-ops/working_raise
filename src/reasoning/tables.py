"""
RAISE Table Reasoning & Second-Chance Evidence Layer
Provides resilient table comprehension:
  1. Exact cell coordinate lookup
  2. Semantic row/column header matching (fallback)
  3. Row/column expansion
  4. Resilient numeric extraction
Never abstains immediately on a coordinate miss; provides second-chance semantic retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedTable:
    title: str
    headers: List[str]
    rows: List[List[str]]
    raw_markdown: str = ""
    source_url: str = ""

    def get_cell(self, row_idx: int, col_idx: int) -> Optional[str]:
        if 0 <= row_idx < len(self.rows) and 0 <= col_idx < len(self.headers):
            if col_idx < len(self.rows[row_idx]):
                return self.rows[row_idx][col_idx]
        return None


class TableReasoningEngine:
    """
    Second-chance tabular reasoning and cell extraction engine.
    """

    @classmethod
    def parse_markdown_table(cls, md_text: str, title: str = "", source_url: str = "") -> Optional[ParsedTable]:
        """
        Parses Markdown formatted table lines into a structured ParsedTable object.
        """
        lines = [l.strip() for l in md_text.strip().split("\n") if l.strip().startswith("|")]
        if len(lines) < 2:
            return None

        # Headers
        header_line = lines[0].strip("|")
        headers = [c.strip() for c in header_line.split("|")]

        rows: List[List[str]] = []
        for line in lines[1:]:
            # Skip separator line
            if re.match(r"^\|?[\s\-:|]+\|?$", line):
                continue
            cleaned = line.strip("|")
            cells = [c.strip() for c in cleaned.split("|")]
            if cells:
                rows.append(cells)

        if not headers or not rows:
            return None

        return ParsedTable(
            title=title,
            headers=headers,
            rows=rows,
            raw_markdown=md_text,
            source_url=source_url,
        )

    @classmethod
    def find_cell_with_fallback(
        cls,
        table: ParsedTable,
        row_query: str,
        col_query: str,
    ) -> Tuple[Optional[str], str]:
        """
        Executes second-chance table cell resolution:
        1. Exact row and col header match
        2. Substring row entity match
        3. Token overlap fuzzy match
        4. Row-level fallback
        Returns (cell_value, resolution_method)
        """
        r_lower = row_query.lower().strip()
        c_lower = col_query.lower().strip()

        # Find best column index with robust normalization & semantic overlap
        col_idx = -1
        best_col_overlap = 0.0
        c_tokens = set(re.findall(r"\b\w{3,}\b", c_lower))

        for idx, h in enumerate(table.headers):
            # Strip footnote brackets ([1], [note 1]), currency/unit annotations ($M, US$, in millions)
            h_clean = re.sub(r"\[.*?\]|\(.*?\)", "", h).strip().lower()
            h_clean = re.sub(r"[\$£€]", "", h_clean).strip()

            if c_lower == h_clean or c_lower in h_clean or h_clean in c_lower:
                col_idx = idx
                break

            if c_tokens:
                h_tokens = set(re.findall(r"\b\w{3,}\b", h_clean))
                if h_tokens:
                    col_overlap = len(c_tokens.intersection(h_tokens)) / min(len(c_tokens), len(h_tokens))
                    if col_overlap > best_col_overlap:
                        best_col_overlap = col_overlap
                        if col_overlap >= 0.5:
                            col_idx = idx

        # Find best row index
        row_idx = -1
        best_overlap = 0.0
        r_tokens = set(re.findall(r"\b\w{3,}\b", r_lower))

        for r_i, row in enumerate(table.rows):
            lead_cell = row[0].lower() if row else ""
            row_full = " ".join(row).lower()

            if r_lower in lead_cell or lead_cell in r_lower:
                row_idx = r_i
                break

            if r_tokens:
                row_tokens = set(re.findall(r"\b\w{3,}\b", row_full))
                overlap = len(r_tokens.intersection(row_tokens)) / len(r_tokens)
                if overlap > best_overlap:
                    best_overlap = overlap
                    if overlap >= 0.5:
                        row_idx = r_i

        # 1. Exact coordinate match
        if row_idx != -1 and col_idx != -1:
            val = table.get_cell(row_idx, col_idx)
            if val:
                return val, "EXACT_COORDINATE"

        # 2. Row-level extraction fallback: Return the matched row as structured context
        if row_idx != -1:
            row_content = " | ".join(table.rows[row_idx])
            return row_content, "ROW_FALLBACK"

        # 3. Column-level extraction fallback
        if col_idx != -1:
            col_vals = [r[col_idx] for r in table.rows if col_idx < len(r)]
            return ", ".join(col_vals[:8]), "COL_FALLBACK"

        return None, "NOT_FOUND"

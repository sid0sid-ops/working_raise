"""
RAISE Table Matrix Engine
Treats tables in university reports as first-class matrix objects.
Preserves 2D coordinates, row/column headers, merged cells, units, currencies, and source page provenance.
Provides Cell-Coordinate Binding (e.g., [R{row}:C{col}]) for structured financial table verification.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CellCoordinate:
    row: int
    col: int
    header_col: str
    header_row: str
    raw_value: str
    numeric_value: Optional[float]
    unit: Optional[str] = None

    def to_tag(self) -> str:
        return f"[R{self.row}:C{self.col}]"


@dataclass
class TableMatrixRecord:
    table_id: str
    document_id: str
    university: str
    title: str
    page: int
    headers: List[str]
    matrix: List[List[str]]  # 2D cell text values
    numeric_grid: List[List[Optional[float]]]  # Parsed numeric values
    units: Dict[str, str] = field(default_factory=dict)
    currency: Optional[str] = None
    scale: Optional[float] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_coordinate_bound_markdown(self) -> str:
        """
        Exports a Markdown table with embedded [R{row}:C{col}] cell-coordinate bindings.
        Enables downstream claim verifiers to cross-check exact 2D cell coordinates.
        """
        lines = [f"### Table: {self.title} (Page {self.page})"]
        header_cells = [f"{h} [C{c}]" for c, h in enumerate(self.headers, start=1)]
        lines.append("| " + " | ".join(header_cells) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

        for r_idx, row in enumerate(self.matrix, start=1):
            row_cells = []
            for c_idx, cell_val in enumerate(row, start=1):
                clean_val = cell_val.strip()
                row_cells.append(f"{clean_val} [R{r_idx}:C{c_idx}]")
            lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(lines)

    def lookup_cell(self, row: int, col: int) -> Optional[CellCoordinate]:
        """Lookup structured cell metadata by 1-indexed (row, col) coordinates."""
        if 1 <= row <= len(self.matrix) and 1 <= col <= len(self.headers):
            r_idx = row - 1
            c_idx = col - 1
            h_col = self.headers[c_idx] if c_idx < len(self.headers) else f"Col_{col}"
            h_row = self.matrix[r_idx][0] if self.matrix[r_idx] else f"Row_{row}"
            raw = self.matrix[r_idx][c_idx] if c_idx < len(self.matrix[r_idx]) else ""
            num = self.numeric_grid[r_idx][c_idx] if r_idx < len(self.numeric_grid) and c_idx < len(self.numeric_grid[r_idx]) else None
            return CellCoordinate(
                row=row,
                col=col,
                header_col=h_col,
                header_row=h_row,
                raw_value=raw,
                numeric_value=num,
                unit=self.currency,
            )
        return None


class TableEngine:
    """
    Manages structured table indexing, 2D matrix lookups, and cell retrieval.
    """

    COORDINATE_PATTERN = re.compile(r"\[R(\d+):C(\d+)\]")

    def __init__(self):
        self.tables: Dict[str, TableMatrixRecord] = {}

    def register_table(
        self,
        table_id: str,
        document_id: str,
        university: str,
        title: str,
        page: int,
        headers: List[str],
        rows: List[List[str]],
        currency: Optional[str] = "INR",
        scale: float = 1.0,
    ) -> TableMatrixRecord:
        num_grid: List[List[Optional[float]]] = []

        for row in rows:
            num_row: List[Optional[float]] = []
            for cell in row:
                c_clean = re.sub(r"[^\d.]", "", cell.replace(",", ""))
                try:
                    v = float(c_clean) * scale if c_clean else None
                except ValueError:
                    v = None
                num_row.append(v)
            num_grid.append(num_row)

        record = TableMatrixRecord(
            table_id=table_id,
            document_id=document_id,
            university=university,
            title=title,
            page=page,
            headers=headers,
            matrix=rows,
            numeric_grid=num_grid,
            currency=currency,
            scale=scale,
            provenance={
                "source_document": document_id,
                "page_number": page,
                "table_id": table_id,
            },
        )
        self.tables[table_id] = record
        return record

    def parse_coordinate_markers(self, text: str) -> List[Tuple[int, int]]:
        """Extracts all [R{r}:C{c}] cell coordinates mentioned in text."""
        coords = []
        for m in self.COORDINATE_PATTERN.finditer(text):
            coords.append((int(m.group(1)), int(m.group(2))))
        return coords

    def get_table(self, table_id: str) -> Optional[TableMatrixRecord]:
        return self.tables.get(table_id)

    def search_tables(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 3,
    ) -> List[TableMatrixRecord]:
        """Table-aware retrieval for counts, totals, percentages, and financial matrix records."""
        q_tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower()))
        if not q_tokens or not self.tables:
            return []

        scored_tables = []
        for tbl in self.tables.values():
            if doc_id and tbl.document_id != doc_id:
                continue
            
            # Match against title, headers, and cell values
            header_text = " ".join(tbl.headers).lower()
            title_text = tbl.title.lower()
            cell_sample = " ".join([" ".join(row) for row in tbl.matrix[:5]]).lower()
            
            score = 0
            for t in q_tokens:
                if t in title_text:
                    score += 3.0
                if t in header_text:
                    score += 2.0
                if t in cell_sample:
                    score += 1.0

            if score > 0:
                scored_tables.append((score, tbl))

        scored_tables.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_tables[:top_k]]

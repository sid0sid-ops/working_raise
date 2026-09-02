"""
RAISE Table Matrix Engine
Treats tables in university reports as first-class matrix objects.
Preserves 2D coordinates, row/column headers, merged cells, units, currencies, and source page provenance.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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


class TableEngine:
    """
    Manages structured table indexing, 2D matrix lookups, and cell retrieval.
    """

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
        """
        Store a structured 2D table grid with parsed numeric cells.
        """
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

    def search_tables(
        self,
        query: str,
        university: Optional[str] = None,
        page: Optional[int] = None,
    ) -> List[TableMatrixRecord]:
        """
        Retrieve structured tables matching search terms and institutional filters.
        """
        matches = []
        q_lower = query.lower()

        for rec in self.tables.values():
            if university and university.lower() not in rec.university.lower():
                continue
            if page and rec.page != page:
                continue

            # Check title, headers, and matrix content
            header_str = " ".join(rec.headers).lower()
            if q_lower in rec.title.lower() or q_lower in header_str:
                matches.append(rec)
            else:
                for row in rec.matrix:
                    if any(q_lower in str(c).lower() for c in row):
                        matches.append(rec)
                        break

        return matches

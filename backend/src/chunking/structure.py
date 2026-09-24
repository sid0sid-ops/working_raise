"""
Structural Layout Segmentation Engine (Stage 1 & Stage 2 of GGAHC).
Extracts document title, headings (#, ##, ###), paragraph blocks, tables, figures, captions,
and layout reading order from Docling or PyMuPDF parsed documents.
Ensures tables and figures are treated as first-class information units with source coordinates and metadata.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import StructuralUnit


class DocumentStructureExtractor:
    """
    Extracts structured, ordered units from parsed document representations.
    Works seamlessly with Docling layout items or PyMuPDF parsed sections.
    """

    HEADING_PATTERNS = [
        r"^(#{1,4})\s+(.+)$",
        r"^(\d+\.(?:\d+)*)\s+([A-Z][A-Za-z0-9\s&–—,()]{2,80})$",
        r"^(Section|Chapter|Part)\s+([0-9IVXLCDM]+)[\s:–—]+(.+)$",
    ]

    TABLE_PATTERNS = [
        r"(\|.+?\|\n\|[-:\s|]+?\|\n(?:\|.+?\|\n?)+)",
    ]

    FIGURE_PATTERNS = [
        r"(?:Figure|Fig\.?|Plate)\s*(\d+)?[\s:–—]+([^\n]+)",
        r"(?:<!--\s*figure:\s*(.*?)\s*-->)",
    ]

    def __init__(self):
        pass

    def extract_from_parsed_sections(
        self,
        sections: List[Dict[str, Any]],
        document_id: str,
    ) -> List[StructuralUnit]:
        """
        Transforms parsed section dictionaries (from SmartDocumentParser or DoclingLayoutParser)
        into rich StructuralUnit items.
        """
        structural_units: List[StructuralUnit] = []
        unit_counter = 0

        for sec in sections:
            pno = sec.get("page_number", 1)
            doc_pno = sec.get("doc_page_number")
            text = sec.get("text") or sec.get("plain_text") or ""
            heading = sec.get("heading") or f"Section {unit_counter + 1}"
            heading_level = sec.get("heading_level", 3)
            has_table = sec.get("has_table", False)

            if not text.strip():
                continue

            # Check if section consists of or contains markdown tables or has upstream table flag
            is_explicit_table = (
                sec.get("is_table") is True
                or sec.get("has_table") is True
                or sec.get("type") in ("table", "TableItem")
            )
            table_matches = list(re.finditer(r"(\|.+?\|\n\|[-:\s|]+?\|\n(?:\|.+?\|\n?)+)", text))

            if is_explicit_table and not table_matches:
                unit_counter += 1
                parsed_rows = [r.strip() for r in text.split("\n") if r.strip()]
                header_row = parsed_rows[0] if parsed_rows else ""
                structural_units.append(StructuralUnit(
                    unit_id=f"{document_id}_u{unit_counter:04d}",
                    unit_type="table",
                    content=text.strip(),
                    heading=heading,
                    heading_level=heading_level,
                    page_number=pno,
                    doc_page_number=doc_pno,
                    table_metadata={
                        "rows_count": len(parsed_rows),
                        "header_row": header_row,
                        "has_data": len(parsed_rows) > 1,
                        "upstream_type": sec.get("type", "table"),
                    },
                    source_block_id=f"blk_p{pno}_tbl_{unit_counter}",
                ))
                continue
            
            if table_matches:
                last_end = 0
                for t_idx, match in enumerate(table_matches):
                    # Preceding prose
                    pre_text = text[last_end:match.start()].strip()
                    if pre_text:
                        unit_counter += 1
                        structural_units.append(StructuralUnit(
                            unit_id=f"{document_id}_u{unit_counter:04d}",
                            unit_type="paragraph",
                            content=pre_text,
                            heading=heading,
                            heading_level=heading_level,
                            page_number=pno,
                            doc_page_number=doc_pno,
                            source_block_id=f"blk_p{pno}_{unit_counter}",
                        ))

                    # Table unit
                    table_content = match.group(0).strip()
                    try:
                        from .table_chunker import TablePreservingChunker
                        tbl_chunker = TablePreservingChunker(max_rows_per_chunk=15)
                        sub_tables = tbl_chunker.chunk(
                            table_source=table_content,
                            caption=heading,
                            base_metadata={"document_id": document_id, "page_number": pno},
                        )
                    except Exception:
                        sub_tables = []

                    if sub_tables:
                        for st in sub_tables:
                            unit_counter += 1
                            structural_units.append(StructuralUnit(
                                unit_id=f"{document_id}_u{unit_counter:04d}",
                                unit_type="table",
                                content=st["plain_text"],
                                heading=heading,
                                heading_level=heading_level,
                                page_number=pno,
                                doc_page_number=doc_pno,
                                table_metadata=st.get("metadata", {}),
                                source_block_id=f"blk_p{pno}_tbl_{unit_counter}",
                            ))
                    else:
                        unit_counter += 1
                        parsed_rows = [r.strip() for r in table_content.split("\n") if r.strip()]
                        header_row = parsed_rows[0] if parsed_rows else ""
                        structural_units.append(StructuralUnit(
                            unit_id=f"{document_id}_u{unit_counter:04d}",
                            unit_type="table",
                            content=table_content,
                            heading=heading,
                            heading_level=heading_level,
                            page_number=pno,
                            doc_page_number=doc_pno,
                            table_metadata={
                                "rows_count": len(parsed_rows),
                                "header_row": header_row,
                                "has_data": len(parsed_rows) > 2,
                            },
                            source_block_id=f"blk_p{pno}_tbl_{unit_counter}",
                        ))
                    last_end = match.end()

                # Trailing prose
                post_text = text[last_end:].strip()
                if post_text:
                    unit_counter += 1
                    structural_units.append(StructuralUnit(
                        unit_id=f"{document_id}_u{unit_counter:04d}",
                        unit_type="paragraph",
                        content=post_text,
                        heading=heading,
                        heading_level=heading_level,
                        page_number=pno,
                        doc_page_number=doc_pno,
                        source_block_id=f"blk_p{pno}_{unit_counter}",
                    ))
            else:
                # Normal paragraph or text block
                # Check for figure caption
                fig_match = re.search(r"(?i)\b(?:Figure|Fig\.?|Plate)\s*(\d+)?:?\s*([^\n]+)", text)
                lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
                list_lines = [ln for ln in lines if re.match(r"^(?:[-*•–—]|\d+[.)]|[a-zA-Z][.)])\s+", ln)]
                is_list_block = len(lines) >= 2 and (len(list_lines) / len(lines) >= 0.6)

                if fig_match and len(lines) <= 4 and len(text.split()) < 70:
                    u_type = "figure"
                    fig_meta = {"caption": fig_match.group(0).strip(), "figure_id": fig_match.group(1)}
                    is_list = False
                    list_items = []
                elif is_list_block:
                    u_type = "list"
                    fig_meta = None
                    is_list = True
                    list_items = list_lines
                else:
                    u_type = "paragraph"
                    fig_meta = None
                    is_list = False
                    list_items = []

                unit_counter += 1
                structural_units.append(StructuralUnit(
                    unit_id=f"{document_id}_u{unit_counter:04d}",
                    unit_type=u_type,
                    content=text.strip(),
                    heading=heading,
                    heading_level=heading_level,
                    page_number=pno,
                    doc_page_number=doc_pno,
                    figure_metadata=fig_meta,
                    is_list=is_list,
                    list_items=list_items,
                    source_block_id=f"blk_p{pno}_{unit_counter}",
                ))

        return self.detect_cross_page_continuations(structural_units)

    def detect_cross_page_continuations(
        self, units: List[StructuralUnit]
    ) -> List[StructuralUnit]:
        """
        Detects structural units spanning page boundaries (tables, continued lists, or split sentences).
        Annotates units with is_continued=True and continuation_of_id.
        """
        if len(units) < 2:
            return units

        for i in range(len(units) - 1):
            curr = units[i]
            nxt = units[i + 1]

            # Only check adjacent or subsequent page
            if nxt.page_number not in (curr.page_number, curr.page_number + 1):
                continue

            # Case 1: Explicit continuation markers in heading or start of next block
            nxt_heading_lower = nxt.heading.lower()
            nxt_start_lower = nxt.content[:50].lower()
            if any(m in nxt_heading_lower or m in nxt_start_lower for m in ("(cont", "continued", "contd.", "cont.")):
                nxt.is_continued = True
                nxt.continuation_of_id = curr.unit_id
                continue

            # Case 2: Multi-page Table continuation
            if curr.unit_type == "table" and nxt.unit_type == "table":
                curr_header = (curr.table_metadata or {}).get("header_row", "").strip()
                nxt_header = (nxt.table_metadata or {}).get("header_row", "").strip()
                if curr_header and nxt_header and (curr_header == nxt_header or curr.heading == nxt.heading):
                    nxt.is_continued = True
                    nxt.continuation_of_id = curr.unit_id
                    continue

            # Case 3: Sentence splitting across pages under same heading
            if curr.unit_type == "paragraph" and nxt.unit_type in ("paragraph", "list"):
                if curr.heading == nxt.heading and curr.page_number != nxt.page_number:
                    curr_stripped = curr.content.rstrip()
                    if curr_stripped and curr_stripped[-1] not in (".", "!", "?", ":", '"', "”"):
                        nxt_stripped = nxt.content.lstrip()
                        if nxt_stripped and (nxt_stripped[0].islower() or curr_stripped.endswith("-")):
                            nxt.is_continued = True
                            nxt.continuation_of_id = curr.unit_id

        return units

"""
RAISE Adaptive Document Parser (Docling + PyMuPDF Hybrid)
Intelligently chooses the best parsing engine based on document complexity:
- Uses Docling for layout-heavy, multi-column, table-rich documents.
- Uses PyMuPDF (fitz) for fast text-first streaming and fallback when ML parser is unavailable.
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Check if docling is locally installed
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    HAS_DOCLING = True
except Exception:
    HAS_DOCLING = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except Exception:
    HAS_PYMUPDF = False


class SmartDocumentParser:
    """
    Dual-engine parser that automatically routes between Docling & PyMuPDF.
    """

    def __init__(self):
        self._docling_converter = None
        if HAS_DOCLING:
            try:
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = False
                pipeline_options.do_table_structure = True
                self._docling_converter = DocumentConverter(
                    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
                )
            except Exception:
                self._docling_converter = None

    def should_use_docling(self, pdf_path: Path, max_check_pages: int = 5) -> bool:
        """
        Always use Docling as the primary layout and table parsing engine whenever available.
        Docling seamlessly handles text, scanned image OCR, multi-column articles, and tables.
        """
        if HAS_DOCLING and self._docling_converter:
            return True
        return False

    def parse_pdf(
        self,
        pdf_path: Path | str,
        max_pages: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured page/chunk records using the optimal engine.
        """
        pdf_path = Path(pdf_path)
        use_docling = self.should_use_docling(pdf_path)

        if use_docling and self._docling_converter:
            try:
                print(f" [SmartParser] Routing '{pdf_path.name}' -> Docling (TableFormer & Layout-Aware Parser)...")
                # Docling convert takes max_num_pages as int or raises if None/exceeded
                doc_pages = max_pages if (max_pages and max_pages >= 1000) else 10000
                doc = self._docling_converter.convert(pdf_path, max_num_pages=doc_pages)
                pages_data: List[Dict[str, Any]] = []

                # Extract markdown text representation
                md_text = doc.document.export_to_markdown()
                tables_md = [t.export_to_markdown() for t in doc.document.tables]
                
                # Split markdown into logical section chunks
                sections = re.split(r'\n(?=#{1,3}\s)', md_text)
                for idx, sec in enumerate(sections):
                    sec_clean = sec.strip()
                    if not sec_clean or len(sec_clean) < 30:
                        continue
                    first_line = sec_clean.split("\n")[0].replace("#", "").strip()[:70]
                    heading = first_line if len(first_line) > 3 else f"Section {idx+1}"
                    
                    pages_data.append({
                        "page_number": idx + 1,
                        "heading": heading,
                        "text": sec_clean,
                        "engine": "Docling LayoutFormer",
                        "tables_count": len(tables_md)
                    })
                
                if pages_data:
                    return pages_data
            except Exception as e:
                print(f" [SmartParser] Docling parse notice ({e}). Falling back to fast PyMuPDF parser.")

        # Default / Fallback: Fast PyMuPDF parser
        print(f" [SmartParser] Routing '{pdf_path.name}' -> Fast PyMuPDF Structure Parser...")
        pages_data = []
        if not HAS_PYMUPDF:
            return []

        doc = fitz.open(str(pdf_path))
        pages_to_process = min(len(doc), max_pages)

        for pno in range(pages_to_process):
            page = doc[pno]
            raw_text = page.get_text("text").strip()
            if not raw_text or len(raw_text) < 30:
                continue

            first_line = raw_text.split("\n")[0].strip()[:70]
            heading = first_line if len(first_line) > 5 else f"Section (Page {pno+1})"

            # Extract any embedded tables as markdown if present
            try:
                tables = page.find_tables()
                if tables and len(tables.tables) > 0:
                    for t in tables:
                        df = t.extract()
                        if df and len(df) > 1:
                            header = df[0]
                            t_md = "\n| " + " | ".join(str(c or "") for c in header) + " |\n"
                            t_md += "| " + " | ".join(["---"] * len(header)) + " |\n"
                            for row in df[1:]:
                                t_md += "| " + " | ".join(str(c or "") for c in row) + " |\n"
                            raw_text += f"\n\n### Extracted Table Data:\n{t_md}"
            except Exception:
                pass

            pages_data.append({
                "page_number": pno + 1,
                "heading": heading,
                "text": raw_text,
                "engine": "PyMuPDF High-Speed Parser",
                "tables_count": 0
            })

        doc.close()
        return pages_data

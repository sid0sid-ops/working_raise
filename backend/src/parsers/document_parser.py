"""
RAISE Adaptive Document Parser (Docling + PyMuPDF Hybrid)
Intelligently chooses the best parsing engine based on document complexity:
- Uses Docling for layout-heavy, multi-column, table-rich documents.
- Uses PyMuPDF (fitz) for fast text-first streaming and fallback when ML parser is unavailable.
"""

from __future__ import annotations
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Suppress harmless TableFormer orphan cell recovery logs in production console
logging.getLogger("MatchingPostProcessor").setLevel(logging.ERROR)
logging.getLogger("docling").setLevel(logging.ERROR)

# Check if docling is locally installed
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
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
        self._docling_converter_no_ocr = None
        self._docling_converter_ocr = None

    def _create_converter(self, do_ocr: bool = False):
        if not HAS_DOCLING:
            return None
        try:
            from docling.datamodel.pipeline_options import AcceleratorOptions, AcceleratorDevice
            import torch
            use_cuda = torch.cuda.is_available()
            acc_dev = AcceleratorDevice.CUDA if use_cuda else AcceleratorDevice.CPU

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = do_ocr
            pipeline_options.do_table_structure = True
            pipeline_options.generate_page_images = True
            pipeline_options.accelerator_options = AcceleratorOptions(device=acc_dev)
            
            # Enforce verified cell recovery & accurate table mode
            try:
                pipeline_options.table_structure_options.do_cell_matching = True
                pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
            except Exception:
                pass

            return DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
            )
        except Exception as e:
            print(f" [SmartParser] Notice initializing Docling (do_ocr={do_ocr}): {e}")
            return None

    def get_converter(self, do_ocr: bool = False):
        if do_ocr:
            if self._docling_converter_ocr is None:
                self._docling_converter_ocr = self._create_converter(do_ocr=True)
            return self._docling_converter_ocr
        else:
            if self._docling_converter_no_ocr is None:
                self._docling_converter_no_ocr = self._create_converter(do_ocr=False)
            return self._docling_converter_no_ocr

    def has_scanned_pages(self, pdf_path: Path, max_check: int = 20) -> bool:
        if not HAS_PYMUPDF:
            return True
        try:
            with fitz.open(str(pdf_path)) as doc:
                total = len(doc)
                step = max(1, total // max_check)
                indices = range(0, total, step)
                scanned_count = 0
                for idx in indices:
                    if len(doc[idx].get_text("text").strip()) < 20:
                        scanned_count += 1
                return scanned_count > 0
        except Exception:
            return True

    def should_use_docling(self, pdf_path: Path, max_check_pages: int = 5) -> bool:
        """
        Always use Docling as the primary layout and table parsing engine whenever available.
        Docling seamlessly handles text, scanned image OCR, multi-column articles, and tables.
        """
        return HAS_DOCLING

    def parse_pdf(
        self,
        pdf_path: Path | str,
        max_pages: Optional[int] = None,
        engine: str = "auto",
        full_potential: bool = False,
        extract_tables: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured page/chunk records using the optimal engine.
        - engine: 'auto' | 'fast' (PyMuPDF: ~2s) | 'deep' | 'docling' (Docling TableFormer: neural cell recovery)
        Removes arbitrary max caps to support full-document processing in Deep Vision / Docling mode.
        """
        pdf_path = Path(pdf_path)
        t_parse_start = time.time()
        use_docling = False
        eng_lower = str(engine or "auto").lower()
        if eng_lower in ("deep", "docling") or full_potential:
            use_docling = HAS_DOCLING
        elif eng_lower == "fast":
            use_docling = False
        else:  # auto
            # Route to Docling if document has complex tables/forms
            use_docling = self.should_use_docling(pdf_path)

        # Optimization: Run TableFormer with do_ocr=False for high-speed neural structure (~150ms/page)
        # Targeted GPU OCR is applied strictly to individual scanned pages in post-processing, avoiding whole-document OCR stalls.
        converter = self.get_converter(do_ocr=False) if use_docling else None

        if use_docling and converter:
            temp_slice_path = None
            try:
                cap_label = f"max_pages={max_pages}" if (max_pages and int(max_pages) > 0) else "full document, no cap"
                print(f" [SmartParser] Routing '{pdf_path.name}' -> Docling (TableFormer Accurate, Page-Level OCR, {cap_label})...")
                doc_pages = int(max_pages) if (max_pages and int(max_pages) > 0) else None
                convert_path = pdf_path
                # Only slice if caller explicitly requested a partial page limit
                if doc_pages and HAS_PYMUPDF:
                    try:
                        with fitz.open(str(pdf_path)) as _chk_doc:
                            if len(_chk_doc) > doc_pages:
                                temp_slice_path = pdf_path.parent / f"_temp_docling_slice_{doc_pages}_{pdf_path.name}"
                                sub_doc = fitz.open()
                                for p in range(doc_pages):
                                    sub_doc.insert_pdf(_chk_doc, from_page=p, to_page=p)
                                sub_doc.save(str(temp_slice_path))
                                sub_doc.close()
                                convert_path = temp_slice_path
                    except Exception:
                        pass

                # Convert using Docling without artificial max cap
                doc = converter.convert(str(convert_path))
                pages_data: List[Dict[str, Any]] = []
                page_items_map: Dict[int, List[str]] = {}
                page_headings_map: Dict[int, str] = {}
                table_count = 0

                try:
                    for item, level in doc.document.iterate_items():
                        prov = getattr(item, "prov", None)
                        p_no = prov[0].page_no if (prov and len(prov) > 0) else 1
                        item_type = type(item).__name__
                        if item_type in ["PictureItem"]:
                            continue
                        txt = ""
                        if item_type == "TableItem":
                            table_count += 1
                        if hasattr(item, "export_to_markdown"):
                            try:
                                txt = item.export_to_markdown(doc=doc.document)
                            except Exception:
                                txt = getattr(item, "text", "") or ""
                        elif hasattr(item, "text"):
                            txt = item.text or ""
                        txt = txt.strip()
                        if not txt:
                            continue
                        if p_no not in page_items_map:
                            page_items_map[p_no] = []
                        page_items_map[p_no].append(txt)
                        if item_type == "SectionHeaderItem" and p_no not in page_headings_map:
                            page_headings_map[p_no] = txt.replace("#", "").strip()[:70]
                except Exception as iter_err:
                    print(f" [SmartParser] Notice during Docling iteration: {iter_err}")

                for p_no, lines in sorted(page_items_map.items()):
                    h_default = page_headings_map.get(p_no)
                    coalesced_chunks = self.coalesce_markdown_sections(lines, target_words=450, min_words=100, max_words=700)
                    if not coalesced_chunks:
                        raw_combined = self.normalize_text("\n\n".join(lines))
                        if raw_combined and len(raw_combined) >= 15:
                            coalesced_chunks = [raw_combined]
                    
                    for sub_idx, chunk_text in enumerate(coalesced_chunks):
                        norm_text = self.normalize_text(chunk_text)
                        if not norm_text or len(norm_text) < 15:
                            continue
                        chunk_h = h_default
                        if not chunk_h:
                            first_l = norm_text.split("\n")[0].replace("#", "").strip()[:70]
                            chunk_h = first_l if len(first_l) > 3 else f"Section (Page {p_no})"
                        if len(coalesced_chunks) > 1:
                            chunk_h = f"{chunk_h} (Part {sub_idx+1})"
                        
                        has_tbl = "|" in norm_text and "-|-" in norm_text
                        pages_data.append({
                            "page_number": p_no,
                            "heading": chunk_h,
                            "text": norm_text,
                            "engine": "Docling LayoutFormer",
                            "tables_count": table_count if has_tbl else 0,
                            "has_table": has_tbl
                        })

                if not pages_data:
                    md_text = doc.document.export_to_markdown()
                    if md_text.strip():
                        pages_data.append({
                            "page_number": 1,
                            "heading": "Document Content",
                            "text": self.normalize_text(md_text),
                            "engine": "Docling LayoutFormer",
                            "tables_count": len(doc.document.tables) if hasattr(doc.document, "tables") else 0,
                            "has_table": bool(hasattr(doc.document, "tables") and doc.document.tables)
                        })

                # Page-Continuity & Targeted Page-Level GPU OCR
                if pages_data and HAS_PYMUPDF:
                    try:
                        with fitz.open(str(pdf_path)) as _vdoc:
                            target_total = min(len(_vdoc), int(max_pages)) if (max_pages and int(max_pages) > 0) else len(_vdoc)
                            existing_pages = {p["page_number"] for p in pages_data}
                            for p_num in range(1, target_total + 1):
                                if p_num not in existing_pages:
                                    fb_page = _vdoc[p_num - 1]
                                    fb_text = self.normalize_text(fb_page.get_text("text").strip())
                                    if len(fb_text) < 40 and len(fb_page.get_images()) > 0:
                                        try:
                                            import easyocr, numpy as np
                                            if not hasattr(self, "_easyocr_reader"):
                                                self._easyocr_reader = easyocr.Reader(['en'], gpu=True)
                                            pix = fb_page.get_pixmap(dpi=150)
                                            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                                            ocr_lines = self._easyocr_reader.readtext(img, detail=0)
                                            if ocr_lines:
                                                fb_text = self.normalize_text("\n".join(ocr_lines))
                                        except Exception:
                                            pass
                                    pages_data.append({
                                        "page_number": p_num,
                                        "heading": f"Section (Page {p_num})",
                                        "text": fb_text if fb_text else f"[Page {p_num}]",
                                        "engine": "PyMuPDF Continuity Fallback",
                                        "tables_count": 0,
                                        "has_table": False
                                    })
                            # Check Docling pages with minimal text that are scanned images
                            for p in pages_data:
                                if len(p.get("text", "").strip()) < 40:
                                    p_idx = p["page_number"] - 1
                                    if 0 <= p_idx < len(_vdoc):
                                        cpage = _vdoc[p_idx]
                                        if len(cpage.get_images()) > 0:
                                            try:
                                                import easyocr, numpy as np
                                                if not hasattr(self, "_easyocr_reader"):
                                                    self._easyocr_reader = easyocr.Reader(['en'], gpu=True)
                                                pix = cpage.get_pixmap(dpi=150)
                                                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                                                ocr_lines = self._easyocr_reader.readtext(img, detail=0)
                                                if ocr_lines:
                                                    p["text"] = self.normalize_text("\n".join(ocr_lines))
                                                    p["engine"] = "Docling + Page-Level GPU OCR"
                                            except Exception:
                                                pass
                            pages_data.sort(key=lambda p: p["page_number"])
                    except Exception as _val_err:
                        print(f" [SmartParser] Continuity validator notice: {_val_err}")

                if pages_data:
                    duration = round(time.time() - t_parse_start, 2)
                    tables_total = sum(p.get("tables_count", 0) for p in pages_data)
                    print(f" [SmartParser] Completed '{pdf_path.name}' via Docling: {len(pages_data)} pages in {duration}s ({len(pages_data)/max(duration, 0.01):.1f} p/s, {tables_total} tables)")
                    return pages_data
            except Exception as e:
                print(f" [SmartParser] Docling parse notice ({e}). Falling back to fast PyMuPDF parser.")
            finally:
                if temp_slice_path and temp_slice_path.exists():
                    try:
                        temp_slice_path.unlink()
                    except Exception:
                        pass

        # Default / Fast Engine: High-speed PyMuPDF parser
        pages_label = f"max_pages={max_pages}" if (max_pages and int(max_pages) > 0) else "full document, no cap"
        print(f" [SmartParser] Routing '{pdf_path.name}' -> Fast PyMuPDF Structure Parser ({pages_label})...")
        pages_data = []
        if not HAS_PYMUPDF:
            return []

        doc = fitz.open(str(pdf_path))
        pages_to_process = min(len(doc), int(max_pages)) if (max_pages and int(max_pages) > 0) else len(doc)

        prev_page_raw = ""
        for pno in range(pages_to_process):
            page = doc[pno]
            
            # Extract blocks geometrically (x0, y0, x1, y1)
            blocks = page.get_text("blocks")
            # Sort blocks top-to-bottom, then left-to-right to respect layouts
            blocks.sort(key=lambda b: (b[1], b[0]))
            block_texts = []
            for b in blocks:
                if len(b) >= 5 and b[4] and b[4].strip():
                    block_texts.append(b[4].strip())
            raw_text = "\n\n".join(block_texts) if block_texts else page.get_text("text").strip()
            
            # 1. OCR fallback for scanned report / accounting pages BEFORE length filtering
            if len(raw_text.strip()) < 80 and len(page.get_images()) > 0:
                try:
                    import easyocr
                    import numpy as np
                    if not hasattr(self, "_easyocr_reader"):
                        self._easyocr_reader = easyocr.Reader(['en'], gpu=True)
                    pix = page.get_pixmap(dpi=150)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    ocr_lines = self._easyocr_reader.readtext(img, detail=0)
                    if ocr_lines:
                        raw_text = "\n".join(ocr_lines)
                except Exception:
                    pass

            # Normalize and clean spaced-letter anomalies and corrupt placeholders
            raw_text = self.normalize_text(raw_text)
            if not raw_text or len(raw_text) < 15:
                # Retain page placeholder to preserve page continuity
                raw_text = f"[Page {pno+1} Graphic / Form]"

            # Extract printed document page number from footer zone (bottom 65pt)
            doc_page_number = None
            H = page.rect.height
            for b in reversed(blocks):
                if len(b) >= 5 and (b[1] > H - 65 or b[3] > H - 45):
                    txt_b = b[4].strip()
                    m_p = re.match(r"^(?:page\s*)?([ivxlcdm]+|\d{1,4})$", txt_b, re.IGNORECASE)
                    if m_p:
                        doc_page_number = m_p.group(1)
                        break

            # Fallback check for printed page number in the last two text lines (for OCR pages)
            if not doc_page_number and raw_text:
                for line_cand in reversed([l.strip() for l in raw_text.split("\n") if l.strip()][-2:]):
                    m_p = re.match(r"^(?:page\s*)?([ivxlcdm]+|\d{1,4})$", line_cand, re.IGNORECASE)
                    if m_p:
                        doc_page_number = m_p.group(1)
                        break

            # Extract any embedded tables as markdown if present
            table_count = 0
            try:
                tables = page.find_tables()
                if tables and len(tables.tables) > 0:
                    table_count = len(tables.tables)
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

            has_table = table_count > 0 or ("| --- |" in raw_text)

            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

            # Priority 0: Detect multiple distinct section headings on the same physical page
            sec_matches = list(re.finditer(
                r'\b1[1-9]\s+(?:Board of Governors|Finance Committee|The Senate|Administration|Historical Purview|List of the Departments)|\b\d+\.\d+\s+[A-Z][A-Za-z\s&–—,()]{3,55}',
                raw_text,
                re.IGNORECASE
            ))
            
            # Check if this page is a Table of Contents (many short lines or explicit 'contents' header)
            is_toc = (
                any(line.lower() in {"contents", "table of contents", "index"} for line in lines[:5])
                or len(sec_matches) > 4
            )

            if not is_toc and 2 <= len(sec_matches) <= 4:
                sub_slices = []
                for s_i, s_m in enumerate(sec_matches):
                    s_start = 0 if s_i == 0 else s_m.start()
                    s_end = sec_matches[s_i + 1].start() if s_i + 1 < len(sec_matches) else len(raw_text)
                    sub_text = raw_text[s_start:s_end].strip()
                    sub_slices.append((s_m, sub_text))

                # Verify substantive content in each section (e.g. at least 180 chars)
                if all(len(st) >= 180 for _, st in sub_slices):
                    prev_page_raw = raw_text
                    for s_i, (s_m, sub_text) in enumerate(sub_slices):
                        raw_h = s_m.group(0).strip()
                        ocr_m = re.match(r'^1([1-9])\s+(.*)', raw_h)
                        if ocr_m and "." not in raw_h[:4]:
                            sub_heading = f"1.{ocr_m.group(1)} {ocr_m.group(2)}"
                        else:
                            sub_heading = raw_h
                        sub_heading = re.sub(r"\s+", " ", sub_heading).strip()[:70]

                        pages_data.append({
                            "page_number": pno + 1,
                            "doc_page_number": doc_page_number,
                            "heading": sub_heading,
                            "text": sub_text,
                            "engine": "PyMuPDF High-Speed Parser",
                            "tables_count": table_count if s_i == len(sub_slices) - 1 else 0,
                            "has_table": has_table if s_i == len(sub_slices) - 1 else False
                        })
                    continue

            heading = "Table of Contents" if is_toc else f"Section (Page {pno+1})"

            # Priority 1: High-precision numbered section headers (e.g. "1.3 Board of Governors")
            sec_num_match = re.search(r"\b(\d+\.\d+\s+[A-Z][A-Za-z\s&–—,()]{3,55})\b", raw_text)
            if not is_toc and sec_num_match:
                heading = re.sub(r"\s+", " ", sec_num_match.group(1)).strip()[:70]
            elif not is_toc:
                # Check for OCR variants where decimal dot is omitted (e.g. "13 Board of Governors" -> "1.3 Board of Governors")
                ocr_sec_match = re.search(r"\b1([1-9])\s+((?:Board of Governors|Finance Committee|The Senate|Administration|Historical Purview|List of the Departments)[A-Za-z\s&–—,()]*)\b", raw_text, re.IGNORECASE)
                if ocr_sec_match:
                    clean_sec_name = re.sub(r"\s+", " ", ocr_sec_match.group(2)).strip()[:60]
                    heading = f"1.{ocr_sec_match.group(1)} {clean_sec_name}"
                elif lines:
                    if lines[0].startswith("#"):
                        heading = lines[0].lstrip("#").strip()[:70]
                    else:
                        # Check for prominent section headers in the first 5 lines
                        detected_h = None
                        for line in lines[:5]:
                            if line.isupper() and 4 <= len(line) <= 65 and not re.match(r"^PAGE\s*\d+$", line) and not line.startswith("ANNUAL REPORT"):
                                detected_h = line[:70]
                                break
                        
                        # If first line is a continuation fragment from previous page, link to previous section
                        first_line = lines[0]
                        is_frag = (
                            first_line[0].islower()
                            or first_line.startswith(("-", "•", "–", "—", "&", "and "))
                            or bool(re.match(r"^[a-zA-Z\s]+-\s*\d{4}$", first_line))
                        )
                        if is_frag and prev_page_raw:
                            prev_lines = [l.strip() for l in prev_page_raw.split("\n") if l.strip()]
                            for pl in reversed(prev_lines):
                                if pl.isupper() and 4 <= len(pl) <= 65 and not re.match(r"^PAGE\s*\d+$", pl):
                                    subheads = [l for l in lines if l.isupper() and 4 <= len(l) <= 50 and not re.match(r"^PAGE\s*\d+$", l)]
                                    if subheads:
                                        detected_h = f"{pl} & {subheads[0]}"[:70]
                                    else:
                                        detected_h = f"{pl} (Contd.)"[:70]
                                    break

                        if not detected_h:
                            for line in lines:
                                if line.isupper() and 4 <= len(line) <= 50 and not re.match(r"^PAGE\s*\d+$", line) and not line.startswith("ANNUAL REPORT"):
                                    detected_h = line[:70]
                                    break

                        # Ignore running document header "Annual Report..." as a section title
                        if not detected_h and first_line and not first_line.lower().startswith("annual report") and len(first_line) > 5:
                            detected_h = first_line[:70]

                        heading = detected_h if detected_h else f"Section (Page {pno+1})"

            prev_page_raw = raw_text

            # If page text is dense (e.g. > 350 words), split into coherent sub-page chunks
            word_list = raw_text.split()
            if len(word_list) > 350:
                para_blocks = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
                coalesced_paras = self.coalesce_markdown_sections(para_blocks, target_words=350, min_words=80, max_words=600)
                if len(coalesced_paras) > 1:
                    for s_i, p_chunk in enumerate(coalesced_paras):
                        sub_h = f"{heading} (Part {s_i+1})"
                        pages_data.append({
                            "page_number": pno + 1,
                            "doc_page_number": doc_page_number,
                            "heading": sub_h,
                            "text": p_chunk,
                            "engine": "PyMuPDF High-Speed Parser",
                            "tables_count": table_count if s_i == 0 else 0,
                            "has_table": has_table if s_i == 0 else False
                        })
                    continue

            pages_data.append({
                "page_number": pno + 1,
                "doc_page_number": doc_page_number,
                "heading": heading,
                "text": raw_text,
                "engine": "PyMuPDF High-Speed Parser",
                "tables_count": table_count,
                "has_table": has_table
            })

        # Final Page-Continuity Validator for PyMuPDF (ensures 100% of pages are present)
        existing_pages = {p["page_number"] for p in pages_data}
        for p_idx in range(pages_to_process):
            p_num = p_idx + 1
            if p_num not in existing_pages:
                fb_page = doc[p_idx]
                fb_txt = self.normalize_text(fb_page.get_text("text").strip())
                pages_data.append({
                    "page_number": p_num,
                    "heading": f"Section (Page {p_num})",
                    "text": fb_txt if fb_txt else f"[Page {p_num} Graphic / Blank]",
                    "engine": "PyMuPDF Continuity Fallback",
                    "tables_count": 0,
                    "has_table": False
                })
        pages_data.sort(key=lambda p: p["page_number"])

        doc.close()
        duration = round(time.time() - t_parse_start, 2)
        tables_total = sum(p.get("tables_count", 0) for p in pages_data)
        print(f" [SmartParser] Completed '{pdf_path.name}' via PyMuPDF: {len(pages_data)} pages in {duration}s ({len(pages_data)/max(duration, 0.01):.1f} p/s, {tables_total} tables)")
        return pages_data

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes OCR and PDF extraction artifacts:
        - Coalesces tracked/spaced uppercase & lowercase letters: "S N A P S H O T" -> "SNAPSHOT", "e c o n o m i c" -> "economic"
        - Reconnects hyphenated word breaks: "de-\nvelopment" -> "development"
        - Strips zero-width & non-standard spacing characters
        - Strips degenerate table placeholder strings
        - Cleans up excessive horizontal/vertical whitespace
        """
        if not text:
            return ""
        # 1. Strip zero-width spaces and control glyphs
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        text = text.replace('\xa0', ' ')

        # 2. Reconnect hyphenated word line-breaks: "inno-\nvation" -> "innovation"
        text = re.sub(r'(\b[a-zA-Z]+)-\s*\n\s*([a-zA-Z]+\b)', r'\1\2', text)

        # 3. Coalesce spaced uppercase letters (e.g. "S N A P S H O T" -> "SNAPSHOT", "A B O U T" -> "ABOUT")
        text = re.sub(r'\b([A-Z]\s){2,}[A-Z]\b', lambda m: m.group(0).replace(' ', ''), text)

        # 4. Coalesce spaced lowercase letters (e.g. "e c o n o m i c" -> "economic", "d e v e l o p m e n t" -> "development")
        text = re.sub(r'\b([a-z]\s){2,}[a-z]\b', lambda m: m.group(0).replace(' ', ''), text)

        # 5. Strip empty table placeholder artifacts
        text = re.sub(r'\[Table placeholder:\s*0\s*rows?,\s*0\s*cols?\]', '', text, flags=re.IGNORECASE)

        # 6. Clean up excessive horizontal and vertical whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


    @staticmethod
    def coalesce_markdown_sections(
        sections: List[str],
        target_words: int = 450,
        min_words: int = 120,
        max_words: int = 700,
    ) -> List[str]:
        """
        Coalesces micro-sections produced by Docling TableFormer / LayoutFormer
        into coherent, high-information semantic chunks.
        Ensures tables remain intact with their introducing context.
        """
        coalesced: List[str] = []
        current_chunk: List[str] = []
        current_word_count = 0

        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean or len(sec_clean) < 15:
                continue
            sec_words = len(sec_clean.split())

            if sec_words >= max_words:
                if current_chunk:
                    coalesced.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_word_count = 0
                coalesced.append(sec_clean)
                continue

            if current_word_count + sec_words > target_words and current_word_count >= min_words:
                coalesced.append("\n\n".join(current_chunk))
                current_chunk = [sec_clean]
                current_word_count = sec_words
            else:
                current_chunk.append(sec_clean)
                current_word_count += sec_words

        if current_chunk:
            coalesced.append("\n\n".join(current_chunk))

        return coalesced


class TextQualityGate:
    """
    Industrial Quality Gate evaluating parsed PDF text prior to embedding and indexing:
      - garbled_token_ratio: ratio of non-printable or corrupted character tokens
      - avg_word_length: detects single-letter fragmentation (< 1.8) or run-together text (> 24.0)
      - repetition_ratio: flags OCR hallucination loops (e.g. repeated words)
    """

    @staticmethod
    def assess(text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "is_acceptable": False,
                "reason": "empty_text",
                "word_count": 0,
                "avg_word_len": 0.0,
                "garbled_ratio": 1.0,
                "repetition_ratio": 0.0,
            }

        words = text.strip().split()
        total_words = len(words)
        if total_words == 0:
            return {
                "is_acceptable": False,
                "reason": "no_words",
                "word_count": 0,
                "avg_word_len": 0.0,
                "garbled_ratio": 1.0,
                "repetition_ratio": 0.0,
            }

        avg_len = sum(len(w) for w in words) / total_words

        # Check for garbled tokens
        garbled_count = 0
        for w in words:
            if len(w) > 35:
                garbled_count += 1
            elif re.search(r"([a-zA-Z0-9])\1{4,}", w):
                garbled_count += 1
            elif re.search(r"[^\x20-\x7E\u00A0-\u024F\u0900-\u097F\u20B9\n\r\t]", w):
                garbled_count += 1

        garbled_ratio = garbled_count / total_words

        # Check token repetition
        rep_count = sum(1 for i in range(1, total_words) if words[i].lower() == words[i-1].lower())
        repetition_ratio = rep_count / total_words

        is_acceptable = (
            garbled_ratio < 0.25
            and repetition_ratio < 0.35
            and 1.8 <= avg_len <= 24.0
        )

        reason = "pass"
        if not is_acceptable:
            reasons = []
            if garbled_ratio >= 0.25:
                reasons.append(f"garbled_ratio_{garbled_ratio:.2f}>=0.25")
            if repetition_ratio >= 0.35:
                reasons.append(f"repetition_ratio_{repetition_ratio:.2f}>=0.35")
            if avg_len < 1.8 or avg_len > 24.0:
                reasons.append(f"abnormal_avg_len_{avg_len:.1f}")
            reason = "; ".join(reasons)

        return {
            "is_acceptable": is_acceptable,
            "reason": reason,
            "word_count": total_words,
            "avg_word_len": round(avg_len, 2),
            "garbled_ratio": round(garbled_ratio, 4),
            "repetition_ratio": round(repetition_ratio, 4),
        }


# Backward-compatible alias conforming to RAISE Canonical Implementation Map
DoclingLayoutParser = SmartDocumentParser

__all__ = ["SmartDocumentParser", "DoclingLayoutParser"]


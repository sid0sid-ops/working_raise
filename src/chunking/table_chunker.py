"""
RAISE Table-Aware Semantic Chunking Engine (Docling AST & Markdown Normalization)
================================================================================
Guarantees schema header persistence, row-window pagination, and rich tabular metadata
across large demographic, financial, and institutional tables.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import pandas as pd

try:
    from docling_core.types.doc import DoclingDocument, TableItem
    HAS_DOCLING_CORE = True
except ImportError:
    HAS_DOCLING_CORE = False
    DoclingDocument = Any  # type: ignore
    TableItem = Any  # type: ignore


class DoclingTablePreservingChunker:
    """
    Splits large Docling TableItem structures into searchable chunks
    while preserving header schema and table captions in every window.
    """

    def __init__(self, max_rows_per_chunk: int = 15):
        self.max_rows_per_chunk = max_rows_per_chunk

    def chunk_table_item(
        self,
        table_item: TableItem,
        doc: Optional[DoclingDocument] = None,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        base_meta = dict(base_metadata or {})
        try:
            df: pd.DataFrame = table_item.export_to_dataframe()
        except Exception:
            return []

        if df is None or df.empty:
            return []

        # Extract caption / title from Docling hierarchy references
        caption = ""
        if hasattr(table_item, "caption") and table_item.caption:
            try:
                caption = table_item.caption.text(doc=doc) if doc else str(table_item.caption)
            except Exception:
                caption = str(table_item.caption)

        header_cols = [str(c) for c in df.columns]
        total_rows = len(df)
        table_chunks: List[Dict[str, Any]] = []

        def _extract_df_cells(df_slice: pd.DataFrame, offset: int) -> List[Dict[str, Any]]:
            cells = []
            for r_idx, (_, r) in enumerate(df_slice.iterrows()):
                for c_idx, col in enumerate(df_slice.columns):
                    v_str = str(r[col])
                    cells.append({
                        "table_caption": caption,
                        "row_idx": offset + r_idx,
                        "col_idx": c_idx,
                        "header": str(col),
                        "value": v_str,
                        "normalized_value": v_str.strip().lower(),
                    })
            return cells

        # If table fits comfortably within a single chunk, preserve entirely
        if total_rows <= self.max_rows_per_chunk:
            md_content = df.to_markdown(index=False)
            content = f"### Table: {caption}\n{md_content}" if caption else md_content
            cell_manifest = _extract_df_cells(df, 0)
            table_chunks.append({
                "plain_text": content,
                "text": content,
                "content": content,
                "is_table": True,
                "table_caption": caption,
                "metadata": {
                    **base_meta,
                    "is_table": True,
                    "has_data": total_rows > 0,
                    "rows_count": total_rows,
                    "header_row": " | ".join(header_cols),
                    "table_caption": caption,
                    "column_names": header_cols,
                    "row_range": [0, total_rows - 1],
                    "total_rows": total_rows,
                    "is_table_split": False,
                    "cell_manifest": cell_manifest,
                },
            })
            return table_chunks

        # Split long tables across rows, re-injecting schema headers into every chunk
        for start_idx in range(0, total_rows, self.max_rows_per_chunk):
            end_idx = min(start_idx + self.max_rows_per_chunk, total_rows)
            sub_df = df.iloc[start_idx:end_idx]

            md_content = sub_df.to_markdown(index=False)
            table_header_prefix = (
                f"### Table: {caption} (Rows {start_idx + 1}-{end_idx} of {total_rows})\n"
                if caption
                else f"### Table Rows {start_idx + 1}-{end_idx} of {total_rows}\n"
            )
            full_chunk_text = table_header_prefix + md_content
            cell_manifest = _extract_df_cells(sub_df, start_idx)

            table_chunks.append({
                "plain_text": full_chunk_text,
                "text": full_chunk_text,
                "content": full_chunk_text,
                "is_table": True,
                "table_caption": caption,
                "metadata": {
                    **base_meta,
                    "is_table": True,
                    "has_data": (end_idx - start_idx) > 0,
                    "rows_count": end_idx - start_idx,
                    "header_row": " | ".join(header_cols),
                    "table_caption": caption,
                    "column_names": header_cols,
                    "row_range": [start_idx, end_idx - 1],
                    "total_rows": total_rows,
                    "is_table_split": True,
                    "cell_manifest": cell_manifest,
                },
            })

        return table_chunks


class MarkdownTablePreservingChunker:
    """
    Universal fallback parser that processes raw pipe-delimited Markdown tables,
    preserving the header and delimiter row across arbitrary split boundaries.
    """

    def __init__(self, max_rows_per_chunk: int = 15):
        self.max_rows_per_chunk = max_rows_per_chunk

    def chunk_markdown_table(
        self,
        table_markdown: str,
        caption: str = "",
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        base_meta = dict(base_metadata or {})
        lines = [l.strip() for l in table_markdown.strip().split("\n") if l.strip()]
        if len(lines) < 2:
            return []

        # Header row & separator
        header_line = lines[0]
        separator_line = lines[1] if re.match(r"^\|[\s\-:\|]+\|$", lines[1]) else ""
        
        data_rows = lines[2:] if separator_line else lines[1:]
        if not data_rows:
            return []

        total_rows = len(data_rows)
        header_cols = [c.strip() for c in header_line.split("|") if c.strip()]

        def _extract_md_cells(rows: List[str], headers: List[str], offset: int) -> List[Dict[str, Any]]:
            cells = []
            for r_idx, r_line in enumerate(rows):
                tokens = [c.strip() for c in r_line.split("|") if c.strip()]
                for c_idx, col_name in enumerate(headers):
                    val = tokens[c_idx] if c_idx < len(tokens) else ""
                    cells.append({
                        "table_caption": caption,
                        "row_idx": offset + r_idx,
                        "col_idx": c_idx,
                        "header": col_name,
                        "value": val,
                        "normalized_value": val.strip().lower(),
                    })
            return cells

        if total_rows <= self.max_rows_per_chunk:
            content = f"### Table: {caption}\n{table_markdown}" if caption else table_markdown
            cell_manifest = _extract_md_cells(data_rows, header_cols, 0)
            return [{
                "plain_text": content,
                "text": content,
                "content": content,
                "is_table": True,
                "table_caption": caption,
                "metadata": {
                    **base_meta,
                    "is_table": True,
                    "has_data": total_rows > 0,
                    "rows_count": total_rows,
                    "header_row": header_line,
                    "table_caption": caption,
                    "column_names": header_cols,
                    "row_range": [0, total_rows - 1],
                    "total_rows": total_rows,
                    "is_table_split": False,
                    "cell_manifest": cell_manifest,
                },
            }]

        chunks: List[Dict[str, Any]] = []
        for start_idx in range(0, total_rows, self.max_rows_per_chunk):
            end_idx = min(start_idx + self.max_rows_per_chunk, total_rows)
            sub_rows = data_rows[start_idx:end_idx]

            table_prefix = (
                f"### Table: {caption} (Rows {start_idx + 1}-{end_idx} of {total_rows})\n"
                if caption
                else f"### Table Rows {start_idx + 1}-{end_idx} of {total_rows}\n"
            )
            table_body = [header_line]
            if separator_line:
                table_body.append(separator_line)
            table_body.extend(sub_rows)

            full_chunk_text = table_prefix + "\n".join(table_body)
            cell_manifest = _extract_md_cells(sub_rows, header_cols, start_idx)

            chunks.append({
                "plain_text": full_chunk_text,
                "text": full_chunk_text,
                "content": full_chunk_text,
                "is_table": True,
                "table_caption": caption,
                "metadata": {
                    **base_meta,
                    "is_table": True,
                    "has_data": (end_idx - start_idx) > 0,
                    "rows_count": end_idx - start_idx,
                    "header_row": header_line,
                    "table_caption": caption,
                    "column_names": header_cols,
                    "row_range": [start_idx, end_idx - 1],
                    "total_rows": total_rows,
                    "is_table_split": True,
                    "cell_manifest": cell_manifest,
                },
            })

        return chunks


class TablePreservingChunker:
    """
    Unified dispatch chunker for tabular data in RAISE.
    Automatically handles Docling TableItems, pandas DataFrames, or raw Markdown.
    """

    def __init__(self, max_rows_per_chunk: int = 15):
        self.docling_chunker = DoclingTablePreservingChunker(max_rows_per_chunk=max_rows_per_chunk)
        self.markdown_chunker = MarkdownTablePreservingChunker(max_rows_per_chunk=max_rows_per_chunk)

    def chunk(
        self,
        table_source: Any,
        doc: Optional[Any] = None,
        caption: str = "",
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        # 1. Docling TableItem dispatch
        if HAS_DOCLING_CORE and isinstance(table_source, TableItem):
            return self.docling_chunker.chunk_table_item(table_source, doc=doc, base_metadata=base_metadata)

        # 2. Pandas DataFrame dispatch
        if isinstance(table_source, pd.DataFrame):
            md = table_source.to_markdown(index=False)
            return self.markdown_chunker.chunk_markdown_table(md, caption=caption, base_metadata=base_metadata)

        # 3. String Markdown table dispatch
        if isinstance(table_source, str):
            return self.markdown_chunker.chunk_markdown_table(table_source, caption=caption, base_metadata=base_metadata)

        return []

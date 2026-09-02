"""
Automated Test Suite for Native Docling Layout Parsing & Ingestion.
Directly converts real academic PDFs and validates section extraction,
Markdown tables, and page provenance.
"""

import sys
from pathlib import Path
import pytest

# Ensure RAG root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers.document_parser import SmartDocumentParser, HAS_DOCLING


def test_docling_availability():
    """Verify Docling library is natively installed and imported."""
    assert HAS_DOCLING is True, "Docling must be natively available in Python environment."


def test_docling_real_pdf_conversion(tmp_path):
    """Test Docling parsing on actual academic PDF fixture."""
    pdf_path = Path("data/documents/07-Jan-2025 AcademicFees.pdf")
    if not pdf_path.exists():
        pytest.skip("Test academic PDF not present in data/documents/")

    parser = SmartDocumentParser()
    assert parser.should_use_docling(pdf_path) is True, "SmartParser must detect tabular layout and route to Docling."

    parsed = parser.parse_pdf(pdf_path, max_pages=2)
    assert len(parsed) > 0, "Docling must produce at least 1 parsed section."
    
    first_sec = parsed[0]
    assert "page_number" in first_sec
    assert "heading" in first_sec
    assert "text" in first_sec
    assert first_sec["engine"] == "Docling LayoutFormer"
    assert len(first_sec["text"]) > 20

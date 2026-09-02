# 🔬 RAISE Provenance & Data Contract Specification

## 1. Provenance Requirements
Every extracted chunk, entity, fact, and relationship in the RAISE system maintains complete provenance tracking:

```json
{
  "document_id": "Annual_Report_2024_25_final_upload",
  "source_filename": "Annual Report 2024-25 final upload.pdf",
  "primary_page": 22,
  "chunk_id": "Annual_Report_2024_25_final_upload_p022",
  "heading": "Sponsored Research & Consultancy",
  "parser": "Docling LayoutFormer / PyMuPDF",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "extraction_model": "AcademicDomainExtractor / Qwen2.5",
  "created_at": "2026-09-02T01:56:00Z"
}
```

---

## 2. Citation Deep-Linking Contract
- Grounded answers must reference citations strictly via brackets: `[1]`, `[2]`.
- Every citation maps to an exact PDF filename, page number, section heading, and chunk ID.
- In the frontend / Web Studio, clicking a citation opens the PDF viewer directly at `#page=N`.

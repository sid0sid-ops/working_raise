"""
Documents & Ingestion Router
Endpoints for uploading PDFs, IBM Docling / PyMuPDF parsing, batch ingestion,
real-time SSE pipeline status tracking, serving raw PDF binaries, and document lifecycle deletion.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from src.api.context import (
    DOCUMENTS_DIR,
    DOWNLOAD_DIR,
    get_library_documents,
    get_ready_documents_list,
    record_ready_document,
    remove_ready_document,
)
from src.api.dependencies import get_postgres_manager, get_rag_engine, get_document_service
from src.features.ingestion.pipeline import AcademicPipelineIngestor

logger = logging.getLogger("raise.router.documents")
router = APIRouter(tags=["Documents & Ingestion"])

BASE_DIR = Path(__file__).resolve().parents[3]


@router.post("/api/upload")
@router.post("/api/documents/upload")
async def upload_document_spec(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    library: Optional[str] = Form(None),
    parser: Optional[str] = Form(None),
    engine: Optional[str] = Form(None),
    parse_mode: Optional[str] = Form(None),
    extract_tables: Optional[str] = Form(None),
    full_potential: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    document_service: Any = Depends(get_document_service),
):
    """
    Document Upload endpoint matching shared frontend specification.
    Supports both single 'file' and multi-file 'files' multipart form fields.
    Honors query and form parameters:
      parser='docling', engine='docling', mode='expert', full_potential='true', extract_tables='true'
    Maintains real-time ingestion phase progression:
      uploading (15%) -> parsing (40%) -> chunking (65%) -> embedding (85%) -> ready (100%)
    """
    q_params = request.query_params
    effective_parser = parser or q_params.get("parser") or engine or q_params.get("engine") or "docling"
    effective_mode = mode or q_params.get("mode") or parse_mode or q_params.get("parse_mode") or "fast"
    effective_library = library or q_params.get("library") or "default"
    effective_full_potential = str(full_potential or q_params.get("full_potential") or "false").lower() in ("true", "1", "yes")
    effective_extract_tables = str(extract_tables or q_params.get("extract_tables") or "true").lower() in ("true", "1", "yes")

    use_engine = "docling" if (effective_parser.lower() in ("docling", "deep") or effective_mode.lower() == "expert" or effective_full_potential) else "auto"

    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=400, detail="No file selected for upload")

    reports = []
    for up_file in upload_list:
        if not up_file.filename:
            continue
        rep = await document_service.ingest_uploaded_file_async(
            file=up_file,
            session_id=session_id,
            library=effective_library,
            engine=use_engine,
            full_potential=effective_full_potential,
            extract_tables=effective_extract_tables,
        )
        reports.append(rep)

    total_nodes, total_edges = document_service.sync_rag_and_graph()
    first_rep = reports[0] if reports else {}

    return {
        "status": "success",
        "message": "Document(s) uploaded and processed successfully",
        "uploaded_count": len(reports),
        "document_id": first_rep.get("doc_id"),
        "doc_id": first_rep.get("doc_id"),
        "filename": first_rep.get("filename"),
        "chunks": first_rep.get("chunks_extracted", 0),
        "library": effective_library,
        "reports": reports,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
    }



@router.post("/api/upload-academic-pdfs")
async def upload_academic_pdfs(
    request: Request,
    files: List[UploadFile] = File(...),
    parser: Optional[str] = Form(None),
    engine: Optional[str] = Form(None),
    parse_mode: Optional[str] = Form(None),
    extract_tables: Optional[str] = Form(None),
    full_potential: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    rag_engine: Any = Depends(get_rag_engine),
):
    """
    Multi-PDF Ingestion Pipeline:
    1. Upload and save PDFs to Download/
    2. Extract structure-aware text spans & clean OCR with Docling / PyMuPDF
    3. Extract Academic Entities & Relations
    4. Index into ChromaDB & sync into Neo4j
    5. Register in verified ready manifest
    """
    if not files:
        raise HTTPException(status_code=400, detail="No PDF files uploaded.")

    q_params = request.query_params
    effective_parser = parser or q_params.get("parser") or engine or q_params.get("engine") or "docling"
    effective_mode = mode or q_params.get("mode") or parse_mode or q_params.get("parse_mode") or "fast"
    effective_full_potential = str(full_potential or q_params.get("full_potential") or "false").lower() in ("true", "1", "yes")
    effective_extract_tables = str(extract_tables or q_params.get("extract_tables") or "true").lower() in ("true", "1", "yes")

    use_engine = "docling" if (effective_parser.lower() in ("docling", "deep") or effective_mode.lower() == "expert" or effective_full_potential) else "auto"

    ingested_reports = []
    academic_pipeline = AcademicPipelineIngestor(download_dir=DOWNLOAD_DIR)

    for upload_file in files:
        if not upload_file.filename.lower().endswith(".pdf"):
            continue

        dest_path = DOWNLOAD_DIR / upload_file.filename
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        # Process the newly uploaded PDF
        res = academic_pipeline.process_pdf(
            dest_path,
            max_pages=30,
            engine=use_engine,
            full_potential=effective_full_potential,
            extract_tables=effective_extract_tables,
        )
        ingested_reports.append(res)

        # Record into ready documents manifest
        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)
        record_ready_document(
            filename=dest_path.name,
            pages=res.get("pages_processed", 1),
            size_mb=size_mb,
            chunks_count=res.get("chunks_extracted", 0)
        )

    # Reload graph data
    if rag_engine:
        rag_engine._load_processed_data()

    total_nodes = rag_engine.graph_engine.graph.number_of_nodes() if (rag_engine and hasattr(rag_engine, "graph_engine")) else 0
    total_edges = rag_engine.graph_engine.graph.number_of_edges() if (rag_engine and hasattr(rag_engine, "graph_engine")) else 0

    return {
        "status": "success",
        "uploaded_count": len(ingested_reports),
        "reports": ingested_reports,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
    }


@router.post("/api/vault/load-defaults")
async def load_vault_defaults(rag_engine: Any = Depends(get_rag_engine)):
    """
    Ingests or loads all available academic reports from DOCUMENTS_DIR directory.
    """
    try:
        # If DOCUMENTS_DIR has no PDFs, auto-seed from tests/Test pdf
        pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))
        if not pdf_files:
            test_fixtures_dir = BASE_DIR / "tests" / "Test pdf"
            if test_fixtures_dir.exists():
                for fixture_pdf in sorted(test_fixtures_dir.glob("*.pdf"))[:2]:
                    target = DOCUMENTS_DIR / fixture_pdf.name
                    if not target.exists():
                        shutil.copy2(fixture_pdf, target)
            pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))

        # Fast sync: check if all documents are already manifested and ingested
        manifest_docs = get_ready_documents_list()
        already_registered = {d.get("filename") for d in manifest_docs if d.get("filename")}
        unprocessed_pdfs = [p for p in pdf_files if p.name not in already_registered]

        if not unprocessed_pdfs and manifest_docs:
            if rag_engine:
                rag_engine._load_processed_data()
            return {
                "status": "success",
                "summary": {
                    "status": "success",
                    "total_documents": len(manifest_docs),
                    "documents": manifest_docs,
                    "message": "Documents already synchronized",
                },
                "documents": manifest_docs,
            }

        with AcademicPipelineIngestor(download_dir=DOCUMENTS_DIR) as academic_pipeline:
            summary = academic_pipeline.process_all_downloads(max_pages_per_doc=25)
            for doc in summary.get("documents", []):
                fname = doc.get("document") or doc.get("pdf_filename") or doc.get("filename")
                if fname:
                    dest_path = DOCUMENTS_DIR / fname
                    size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2) if dest_path.exists() else 0.5
                    record_ready_document(
                        filename=fname,
                        pages=doc.get("pages_processed", 25),
                        size_mb=size_mb,
                        chunks_count=doc.get("chunks_count", 20)
                    )
        if rag_engine:
            rag_engine._load_processed_data()

        # Get updated document list
        manifest_docs = get_ready_documents_list()
        return {
            "status": "success",
            "summary": summary,
            "documents": manifest_docs
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/api/pdf/{filename}")
async def get_pdf_file(filename: str):
    """
    Serves physical PDF for deep-linked in-browser viewing with #page=N.
    Enforces HTTP 206 Partial Content byte ranges, inline display, and long-term caching.
    """
    import os
    import urllib.parse

    clean_name = urllib.parse.unquote(filename).strip()

    # Search candidates: DOWNLOAD_DIR, DOCUMENTS_DIR, user Downloads
    candidates = [
        DOWNLOAD_DIR / clean_name,
        DOCUMENTS_DIR / clean_name,
        Path(os.path.expanduser(f"~/Downloads/{clean_name}")),
    ]

    target_path = None
    for cand in candidates:
        if cand.exists() and cand.is_file():
            target_path = cand
            break

    if not target_path:
        for parent_dir in (DOWNLOAD_DIR, DOCUMENTS_DIR):
            if parent_dir.exists():
                for f in parent_dir.glob("*.pdf"):
                    if f.name.lower() == clean_name.lower():
                        target_path = f
                        break
            if target_path:
                break

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")

    return FileResponse(
        path=str(target_path),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{target_path.name}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        }
    )


@router.get("/api/documents/{document_id}/status")
async def get_document_ingestion_status(
    document_id: str,
    document_service: Any = Depends(get_document_service),
):
    """
    Tier 1 Critical: Real-time Document Ingestion Pipeline Status Endpoint.
    Pollable every 2-3s by frontend during document upload and indexing.
    Returns current pipeline phase, percent (0-100), and stage message.
    """
    status_info = document_service.get_document_status(document_id)
    if status_info:
        return status_info
    raise HTTPException(status_code=404, detail=f"Document status for '{document_id}' not found")


@router.get("/api/documents/{document_id}/events")
async def get_document_ingestion_events(
    document_id: str,
    document_service: Any = Depends(get_document_service),
):
    """
    Server-Sent Events (SSE) Stream for real-time document upload/ingestion progress.
    Stream terminates automatically when phase=='ready' or status=='failed'.
    """
    async def event_generator():
        last_percent = -1
        while True:
            st = document_service.get_document_status(document_id)
            if st:
                curr_pct = st.get("percent", 0)
                if curr_pct != last_percent:
                    last_percent = curr_pct
                    yield f"data: {json.dumps(st)}\n\n"
                if st.get("phase") == "ready" or st.get("status") in ("ready", "failed"):
                    yield "data: [DONE]\n\n"
                    break
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.get("/api/documents")
@router.get("/api/documents/manifest")
async def get_documents(document_service: Any = Depends(get_document_service)):
    """List only documents whose chunking and embedding are confirmed and ready for Q&A."""
    return document_service.list_library_documents()


@router.delete("/api/documents/{document_id}")
async def delete_document_by_id(
    document_id: str,
    document_service: Any = Depends(get_document_service),
):
    """Delete a document by document_id or filename matching shared specification."""
    success, msg_or_fn, err_code = document_service.delete_document(document_id)
    if not success:
        if err_code == "PROTECTED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg_or_fn)
        raise HTTPException(status_code=500, detail=msg_or_fn)

    updated_docs = document_service.list_library_documents().get("documents", [])
    logger.info(f"[DELETE] Successfully purged user document '{msg_or_fn}' from Library")
    return {
        "status": "success",
        "filename": msg_or_fn,
        "documents": updated_docs,
        "total_count": len(updated_docs)
    }


@router.post("/api/documents/delete")
async def delete_document(
    request: Request,
    document_service: Any = Depends(get_document_service),
):
    """Completely purge a document, its chunks, vectors, Neo4j nodes, and manifest."""
    try:
        body = await request.json()
        filename = body.get("filename", "").strip() or body.get("document_id", "").strip()
        if not filename:
            return JSONResponse(status_code=400, content={"status": "error", "error": "Filename is required"})

        success, msg_or_fn, err_code = document_service.delete_document(filename)
        if not success:
            if err_code == "PROTECTED":
                return JSONResponse(status_code=403, content={"status": "error", "error": msg_or_fn})
            return JSONResponse(status_code=500, content={"status": "error", "error": msg_or_fn})

        updated_docs = document_service.list_library_documents().get("documents", [])
        logger.info(f"[DELETE] Successfully purged user document '{msg_or_fn}' from Library")
        return {
            "status": "success",
            "filename": msg_or_fn,
            "documents": updated_docs,
            "total_count": len(updated_docs)
        }
    except Exception as e:
        logger.error(f"[DELETE] Failed to delete document: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": "Document could not be deleted. Please try again."})



@router.post("/api/documents/delete_all")
@router.post("/api/vault/reset")
async def delete_all_documents(rag_engine: Any = Depends(get_rag_engine)):
    """Completely purge all documents, vectors, graph nodes, chunks, and reset vault."""
    try:
        purge_res = rag_engine.purge_all_documents() if rag_engine else {}
        return {
            "status": "success",
            "details": purge_res,
            "documents": [],
            "total_count": 0
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/api/ingest-download-folder")
async def ingest_download_folder(
    postgres_manager: Any = Depends(get_postgres_manager),
    rag_engine: Any = Depends(get_rag_engine),
):
    """Batch-ingest all PDF reports from Download/ directory and record ready manifest and PostgreSQL metadata."""
    try:
        academic_pipeline = AcademicPipelineIngestor(download_dir=DOWNLOAD_DIR)
        res = academic_pipeline.process_all_downloads(max_pages_per_doc=25)
        doc_list = res.get("documents", res.get("reports", []))
        for report in doc_list:
            fname = report.get("filename") or report.get("document")
            if fname:
                pdf_path = DOWNLOAD_DIR / fname
                size_mb = round(pdf_path.stat().st_size / (1024 * 1024), 2) if pdf_path.exists() else 0.0
                pages = report.get("pages_processed", 1)
                chunks = report.get("chunks_count", report.get("chunks_extracted", 0))
                clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(fname).stem)[:40]
                doc_id = f"doc_{clean_stem}"

                record_ready_document(
                    filename=fname,
                    pages=pages,
                    size_mb=size_mb,
                    chunks_count=chunks
                )
                if postgres_manager:
                    postgres_manager.save_document_metadata(
                        doc_id=doc_id,
                        filename=fname,
                        chunks_count=chunks,
                        library="default"
                    )
                    postgres_manager.upsert_document_status(
                        doc_id=doc_id,
                        filename=fname,
                        phase="completed",
                        percent=100,
                        status="ready",
                        detail="Batch ingested and synchronized",
                        pages_processed=pages,
                        chunks_extracted=chunks,
                        file_size_bytes=pdf_path.stat().st_size if pdf_path.exists() else 0,
                        library="default"
                    )
        if rag_engine:
            rag_engine._load_processed_data()
        return res
    except Exception as e:
        return {"status": "error", "error": str(e)}

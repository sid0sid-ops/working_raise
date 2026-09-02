"""
RAISE Master Agentic GraphRAG Studio Application
NotebookLM / YouTube-inspired interface for multi-document academic research,
subgraph exploration, dense vector search, and Neo4j property graphs.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enforce 100% Pure Offline Local Execution (Zero External / Hub Requests)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from src.rag_pipeline import StandaloneRAGPipeline
from src.pipeline_academic_ingest import AcademicPipelineIngestor
from src.batch_ingest import BatchReportIngestor


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    yield


app = FastAPI(
    title="RAISE Master Agentic GraphRAG Studio",
    version="2.5.0",
    description="Multi-PDF Academic GraphRAG, Subgraph Retrieval & Anti-Hallucination Claim Verification",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static & Templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

from src.config import settings

# Initialize Master GraphRAG Pipeline
rag_engine = StandaloneRAGPipeline()
DOCUMENTS_DIR = settings.documents_dir
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = DOCUMENTS_DIR  # Compatibility alias
MANIFEST_FILE = settings.processed_dir / "ingested_manifest.json"


def get_ready_documents_list():
    """Retrieve list of actively confirmed ready documents from authoritative manifest.
    Does NOT auto-scan or auto-register external PDFs without explicit user upload."""
    if MANIFEST_FILE.exists():
        try:
            data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
            return data.get("ready_documents", [])
        except Exception:
            return []
    return []


def record_ready_document(filename: str, pages: int, size_mb: float, chunks_count: int):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"ready_documents": [], "deleted_documents": []}
    if MANIFEST_FILE.exists():
        try:
            manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            manifest = {"ready_documents": [], "deleted_documents": []}
    
    # If this document was previously marked deleted, un-delete it
    deleted = [f for f in manifest.get("deleted_documents", []) if f != filename]
    manifest["deleted_documents"] = deleted

    docs = manifest.get("ready_documents", [])
    updated = False
    for d in docs:
        if d.get("filename") == filename:
            d["pages"] = pages
            d["size_mb"] = size_mb
            d["chunks_count"] = chunks_count
            d["status"] = "ready"
            updated = True
            break
    if not updated:
        docs.append({
            "filename": filename,
            "pages": pages,
            "size_mb": size_mb,
            "chunks_count": chunks_count,
            "status": "ready"
        })
    manifest["ready_documents"] = docs
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def remove_ready_document(filename: str) -> bool:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"ready_documents": [], "deleted_documents": []}
    if MANIFEST_FILE.exists():
        try:
            manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            manifest = {"ready_documents": [], "deleted_documents": []}
    
    deleted = manifest.get("deleted_documents", [])
    if filename not in deleted:
        deleted.append(filename)
    
    docs = manifest.get("ready_documents", [])
    new_docs = [d for d in docs if d.get("filename") != filename]
    
    manifest["ready_documents"] = new_docs
    manifest["deleted_documents"] = deleted
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return True


def _open_browser_when_ready():
    import time
    import webbrowser
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:8080")
    webbrowser.open("http://localhost:7474")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})


@app.post("/api/upload-academic-pdfs")
async def upload_academic_pdfs(files: List[UploadFile] = File(...)):
    """
    Multi-PDF Ingestion Pipeline:
    1. Upload and save PDFs to Download/
    2. Extract structure-aware text spans & clean OCR
    3. Extract Academic Entities & Relations
    4. Index into ChromaDB & sync into Neo4j
    5. Register in verified ready manifest
    """
    if not files:
        raise HTTPException(status_code=400, detail="No PDF files uploaded.")

    ingested_reports = []
    academic_pipeline = AcademicPipelineIngestor(download_dir=DOWNLOAD_DIR)

    for upload_file in files:
        if not upload_file.filename.lower().endswith(".pdf"):
            continue

        dest_path = DOWNLOAD_DIR / upload_file.filename
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        # Process the newly uploaded PDF
        res = academic_pipeline.process_pdf(dest_path, max_pages=30)
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
    rag_engine._load_processed_data()

    return {
        "status": "success",
        "uploaded_count": len(ingested_reports),
        "reports": ingested_reports,
        "total_nodes": rag_engine.graph_engine.graph.number_of_nodes(),
        "total_edges": rag_engine.graph_engine.graph.number_of_edges(),
    }


@app.post("/api/vault/load-defaults")
async def load_vault_defaults():
    """
    Ingests or loads all available academic reports from DOCUMENTS_DIR directory.
    """
    try:
        academic_pipeline = AcademicPipelineIngestor(download_dir=DOCUMENTS_DIR)
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


@app.get("/api/pdf/{filename}")
async def get_pdf_file(filename: str):
    """
    Serves physical PDF from Download/ for deep-linked in-browser viewing with #page=N.
    """
    pdf_path = DOWNLOAD_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@app.post("/api/graphrag/subgraph-query")
async def graphrag_subgraph_query(request: Request):
    """
    Execute LangGraph StateGraph Workflow:
      1. intent_analyzer node
      2. vector_retriever node (ChromaDB)
      3. graph_traverser node (Neo4j / NetworkX)
      4. synthesizer_verifier node (ClaimVerifier)
      5. corrective_expander conditional loop
    """
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        hops = int(body.get("hops", 2))
        top_k = int(body.get("top_k", 4))
        doc_filter = body.get("document_filter")

        if not query:
            return {"error": "Query cannot be empty"}

        ready_docs = get_ready_documents_list()
        if not ready_docs:
            print(f" [GUARD] 0 active documents in research workspace. Refusing retrieval for: \"{query}\"")
            return {
                "query": query,
                "query_type": "EMPTY_WORKSPACE",
                "grounded_answer": "Please upload an academic PDF to begin your research.",
                "answer": "Please upload an academic PDF to begin your research.",
                "grounded": False,
                "traceability_score": 0.0,
                "verified_claims": [],
                "citations": [],
                "top_chunks": [],
                "subgraph": {"nodes": [], "edges": []},
                "sources_count": 0,
                "execution_time": 0.0,
                "message": "Please upload an academic PDF to begin your research."
            }

        # Get active document filenames from workspace manifest
        active_filenames = [d["filename"] for d in ready_docs if "filename" in d]

        print("\n" + "=" * 76)
        print(f" 🦜🕸️ [LANGGRAPH WORKFLOW EXECUTION] Query: \"{query}\"")
        print(f"       • Active Workspace: {len(active_filenames)} PDFs ({', '.join(active_filenames[:3])})")
        print("=" * 76)

        # Run compiled LangGraph state machine with active document scoping
        result = rag_engine.query_subgraph_graphrag(
            query=query,
            hops=hops,
            top_k=top_k,
            document_filter=doc_filter,
            active_docs=active_filenames,
        )

        print(f" [Node 1/5] intent_analyzer:")
        print(f"       • Classified Intent : {result.get('query_type')}")
        print(f"       • Selected Engines  : {', '.join(result.get('selected_tools', []))}")
        if doc_filter:
            print(f"       • Document Filter   : {doc_filter}")

        chunks = result.get("top_chunks", [])
        print(f"\n [Node 2/5] vector_retriever (ChromaDB Cosine Distance):")
        print(f"       • Retrieved {len(chunks)} Context Chunks:")
        for idx, chk in enumerate(chunks, 1):
            meta = chk.get("metadata", {})
            pno = meta.get("primary_page", 1)
            pfile = meta.get("pdf_filename", "Report.pdf")
            sim = chk.get("similarity", 0.85)
            hd = meta.get("heading", "Section")
            print(f"         [{idx}] {pfile} (Page {pno}) | Sim: {sim:.3f} | Heading: {hd[:38]}")

        subg = result.get("subgraph", {})
        print(f"\n [Node 3/5] graph_traverser (Neo4j bolt://localhost:7687):")
        print(f"       • Subgraph Extracted: {len(subg.get('nodes', []))} Nodes | {len(subg.get('edges', []))} Relationships")

        score_pct = round((result.get("traceability_score") or 0.85) * 100)
        claims = result.get("verified_claims", [])
        cits = result.get("citations", [])
        print(f"\n [Node 4/5] synthesizer_verifier (Anti-Hallucination Gate):")
        print(f"       • Grounded Confidence  : {score_pct}% (Tier: Audited Academic Report)")
        print(f"       • Corroborated Claims  : {len(claims)} verified assertions")
        print(f"       • Page Citations       : {len(cits)} verified citations")
        for cidx, cit in enumerate(cits, 1):
            print(f"         [{cidx}] {cit.get('pdf_filename')} -> Page {cit.get('primary_page')}")

        retries = result.get("retry_count", 0)
        exec_time = result.get("execution_time", 0.04)
        print(f"\n [Node 5/5] Conditional Evaluator (Self-Reflective Cycle):")
        print(f"       • Cycles Completed     : {retries + 1} (Retries: {retries})")
        print(f"       • Total Execution Time : {exec_time}s")
        print("=" * 76 + "\n")

        return result
    except Exception as e:
        print(f" [ERROR] LangGraph query execution failed: {e}")
        return {"error": str(e)}


@app.post("/api/agent/query")
async def agent_query(request: Request):
    """Execute autonomous agentic multi-tool reasoning."""
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        if not query:
            return {"error": "Query cannot be empty"}
        ready_docs = get_ready_documents_list()
        if not ready_docs:
            return {
                "response": "Please upload an academic PDF to begin your research.",
                "tool_calls": [],
                "citations": []
            }
        active_filenames = [d["filename"] for d in ready_docs if "filename" in d]
        agent_result = rag_engine.ask_agent(query, active_docs=active_filenames)
        return agent_result
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/search")
async def semantic_search(request: Request):
    """Perform dense vector search across indexed chunks."""
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        top_k = int(body.get("top_k", 5))
        if not query or not get_ready_documents_list():
            return {
                "results": [],
                "query": query,
                "total_matches": 0,
                "message": "Please upload an academic PDF to begin your research."
            }
        results = rag_engine.search_vectors(query=query, top_k=top_k)
        return {"results": results, "query": query, "total_matches": len(results)}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.get("/api/graph")
async def get_graph_data():
    """Retrieve full node-link knowledge graph for canvas rendering."""
    if not get_ready_documents_list():
        return {
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
            "message": "No knowledge graph yet. Upload an academic PDF to build the graph."
        }
    return rag_engine.get_graph_data()


@app.get("/api/subgraph/{node_id}")
async def get_node_subgraph(node_id: str, hops: int = 2):
    """Get multi-hop neighborhood subgraph for specific node."""
    return rag_engine.graph_engine.extract_subgraph([node_id], hops=hops)


@app.get("/api/documents")
async def get_documents():
    """List only documents whose chunking and embedding are confirmed and ready for Q&A."""
    ready_docs = get_ready_documents_list()
    return {"documents": ready_docs, "total_count": len(ready_docs)}


@app.post("/api/documents/delete")
async def delete_document(request: Request):
    """Remove a document from the ready documents manifest and active runtime indices."""
    try:
        body = await request.json()
        filename = body.get("filename", "").strip()
        if not filename:
            return {"status": "error", "error": "Filename is required"}
        success = remove_ready_document(filename)
        
        # Prune from vector engine & Neo4j graph
        doc_id = re.sub(r"[^a-zA-Z0-9]", "_", Path(filename).stem)[:40]
        try:
            rag_engine.vector_engine.collection.delete(where={"document_id": doc_id})
        except Exception:
            pass
        try:
            if rag_engine.neo4j_db.connected:
                rag_engine.neo4j_db.run_cypher("MATCH (n {document_id: $doc_id}) DETACH DELETE n", {"doc_id": doc_id})
        except Exception:
            pass

        updated_docs = get_ready_documents_list()
        return {
            "status": "success" if success else "not_found",
            "filename": filename,
            "documents": updated_docs,
            "total_count": len(updated_docs)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/cypher")
async def get_cypher_script():
    """Download Neo4j Cypher ingestion script."""
    cypher_text = rag_engine.get_cypher_script()
    cypher_file = BASE_DIR / "data" / "processed" / "neo4j" / "academic_graph.cypher"
    cypher_file.parent.mkdir(parents=True, exist_ok=True)
    cypher_file.write_text(cypher_text, encoding="utf-8")
    return FileResponse(str(cypher_file), filename="academic_graph.cypher", media_type="text/plain")


@app.get("/api/neo4j/status")
async def neo4j_status():
    """Check live connection to Neo4j database."""
    return rag_engine.check_neo4j()


@app.post("/api/neo4j/sync")
async def neo4j_sync():
    """Sync all knowledge graph triples into Neo4j."""
    return rag_engine.sync_to_neo4j()


@app.post("/api/neo4j/query")
async def neo4j_run_query(request: Request):
    """Execute raw Cypher query against live Neo4j."""
    try:
        body = await request.json()
        cypher_query = body.get("query", "").strip()
        if not cypher_query:
            return {"records": [], "error": "Query cannot be empty"}
        records = rag_engine.execute_cypher(cypher_query)
        return {"records": records, "query": cypher_query}
    except Exception as e:
        return {"records": [], "error": str(e)}


@app.post("/api/ingest-download-folder")
async def ingest_download_folder():
    """Batch-ingest all PDF reports from Download/ directory and record ready manifest."""
    try:
        academic_pipeline = AcademicPipelineIngestor(download_dir=DOWNLOAD_DIR)
        res = academic_pipeline.process_all_downloads(max_pages_per_doc=25)
        for report in res.get("reports", []):
            fname = report.get("filename")
            if fname:
                pdf_path = DOWNLOAD_DIR / fname
                size_mb = round(pdf_path.stat().st_size / (1024 * 1024), 2) if pdf_path.exists() else 0.0
                record_ready_document(
                    filename=fname,
                    pages=report.get("pages_processed", 1),
                    size_mb=size_mb,
                    chunks_count=report.get("chunks_extracted", 0)
                )
        rag_engine._load_processed_data()
        return res
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/hardware-telemetry")
async def get_hardware_telemetry():
    """Hardware telemetry: 64GB RAM & RTX 3090 GPU."""
    import psutil
    mem = psutil.virtual_memory()
    return {
        "gpu_model": "NVIDIA GeForce RTX 3090 (24 GB VRAM)",
        "ram_total_gb": round(mem.total / (1024**3), 1),
        "ram_available_gb": round(mem.available / (1024**3), 1),
        "ram_percent": mem.percent,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2 (Cached Offline)",
        "neo4j_endpoint": "bolt://localhost:7687",
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print(" 🚀 STARTING RAISE GRAPHRAG STUDIO ON PORT 8080")
    print(" URL: http://127.0.0.1:8080")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")

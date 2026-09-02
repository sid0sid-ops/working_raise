"""
RAISE Academic GraphRAG — Master Terminal & VS Code Interactive Studio
Provides direct, UI-free execution for:
1. Visualizing LangGraph StateGraph (Mermaid Diagram / PNG export / IPython.display)
2. Verifying Neo4j Knowledge Graph & ChromaDB Vector Index connectivity
3. Interactive multi-turn academic research Q&A with real-time reasoning memory recall
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Enforce UTF-8 console output for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure RAG project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import logging
from logging.handlers import RotatingFileHandler

# Configure logs directory and rotating log handler
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "pipeline.log"

logger = logging.getLogger("RAISE_Pipeline")
log_level_str = os.getenv("RAISE_LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level_str, logging.INFO))

if not logger.handlers:
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

from src.rag_pipeline import StandaloneRAGPipeline
from src.reasoning_memory import ReasoningMemory


def render_langgraph_mermaid(workflow_app):
    """
    Renders the LangGraph StateGraph topology as Mermaid syntax,
    exports a local PNG/MMD file, and calls IPython.display if inside a notebook.
    """
    print("\n" + "=" * 70)
    print(" 📊 LANGGRAPH STATEGRAPH WORKFLOW TOPOLOGY")
    print("=" * 70)
    
    try:
        graph = workflow_app.get_graph()
        mermaid_syntax = graph.draw_mermaid()
        print(mermaid_syntax)
        
        # Save mermaid diagram to file for markdown viewers
        mmd_file = BASE_DIR / "graph_workflow.mmd"
        mmd_file.write_text(mermaid_syntax, encoding="utf-8")
        print(f"\n[OK] Mermaid diagram file saved to: {mmd_file}")
    except Exception as e:
        print(f"[Notice] Mermaid text extraction: {e}")

    # Render via IPython.display if running in interactive notebook / IPython shell
    try:
        from IPython.display import Image, display
        png_bytes = workflow_app.get_graph().draw_mermaid_png()
        display(Image(png_bytes))
        print("[OK] Rendered visual Graph via IPython.display")
    except Exception:
        # Save PNG to local directory for direct viewing in VS Code
        try:
            png_bytes = workflow_app.get_graph().draw_mermaid_png()
            png_file = BASE_DIR / "graph_workflow.png"
            png_file.write_bytes(png_bytes)
            print(f"[OK] Visual graph diagram exported to: {png_file}")
        except Exception:
            pass


import subprocess


def auto_start_neo4j_docker():
    """Automatically launches Neo4j container via docker compose if Docker is available."""
    try:
        # Check if Neo4j is already responding
        from src.neo4j_engine import Neo4jDatabase
        db = Neo4jDatabase()
        if db.connected:
            return
        
        print("[Auto-Starter] Attempting to auto-start Neo4j container via Docker Compose...")
        res = subprocess.run(
            ["docker", "compose", "up", "neo4j", "-d"],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        if res.returncode == 0:
            print("[Auto-Starter] Neo4j container started successfully. Waiting for port 7687...")
            time.sleep(3)
    except Exception:
        # Docker not installed or daemon not running; will use in-memory NetworkX fallback
        pass


def main():
    print("=" * 70)
    print(" 🚀 RAISE ACADEMIC GRAPHRAG STUDIO — TERMINAL / VS CODE RUNNER")
    print("=" * 70)
    
    # 0. Auto-Start Neo4j Docker if available
    auto_start_neo4j_docker()
    
    # 1. Initialize Pipeline & Memory Engine
    print("\n[1/3] Initializing Multi-Substrate Pipeline (Vector + Neo4j + LangGraph)...")
    pipeline = StandaloneRAGPipeline()
    memory = ReasoningMemory()
    
    # 2. Check Database Connectivity & Ensure Optimized Schema
    if pipeline.neo4j_db.connected:
        try:
            from src.neo4j_schema import ensure_basic_indexes
            ensure_basic_indexes(pipeline.neo4j_db)
            neo4j_status = "CONNECTED & INDEXED (bolt://localhost:7687)"
        except Exception as e:
            neo4j_status = f"CONNECTED (bolt://localhost:7687) [Index note: {e}]"
    else:
        neo4j_status = "OFFLINE (Using in-memory graph fallback)"
    chroma_count = pipeline.vector_engine.collection.count() if pipeline.vector_engine.collection else 0
    active_docs = pipeline.vector_engine.get_active_workspace_documents()
    
    print(f"  • Neo4j Status:       {neo4j_status}")
    print(f"  • ChromaDB Status:    ACTIVE ({chroma_count} indexed chunks)")
    print(f"  • Embeddings Model:   {pipeline.vector_engine.model_key}")
    print(f"  • Active Manifest:    {len(active_docs)} document(s) loaded")

    
    # 3. Visualize LangGraph StateGraph
    print("\n[2/3] Visualizing Agentic LangGraph StateGraph...")
    render_langgraph_mermaid(pipeline.langgraph_workflow.app)
    
    # 4. Interactive Q&A Loop
    print("\n" + "=" * 70)
    print(" 💬 INTERACTIVE RESEARCH Q&A (Type 'exit' or 'q' to quit)")
    print("=" * 70)
    
    if len(active_docs) == 0:
        print("\n⚠️  [NO DOCUMENTS LOADED]")
        print("  Your database is currently empty (0 documents in manifest).")
        print("  Place your PDF annual reports in: 'data/documents/'")
        print("  Then run document ingestion or upload them via the web studio.")
        print("")
    else:
        from src.question_generator import DynamicQuestionGenerator
        q_gen = DynamicQuestionGenerator()
        dynamic_queries = q_gen.generate_smart_questions(max_questions=4)
        
        print("\n💡 Suggested High-Groundedness Questions (Generated from your uploaded PDFs):")
        for i, sq in enumerate(dynamic_queries, 1):
            print(f"  {i}. {sq}")
        print("")
    
    while True:
        try:
            query = input("\n🔍 Enter Research Question: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("\nExiting RAISE Studio CLI. Goodbye!")
                break
                
            t0 = time.time()
            print("\n[LangGraph Executing Multi-Hop Subgraph Traversal...]")
            
            # Check reasoning memory first
            prior_strat = memory.find_similar_strategy(query)
            if prior_strat:
                print(f"  🧠 Recalled Prior Trajectory ({prior_strat.trajectory_id}) with confidence {prior_strat.confidence_score}")
            
            # Execute GraphRAG query
            res = pipeline.query_subgraph_graphrag(query=query, hops=2, top_k=4)
            elapsed = round(time.time() - t0, 2)
            
            print("\n" + "-" * 70)
            print(f"📋 GROUNDED RESEARCH ANSWER ({elapsed}s | Traceability: {res.get('traceability_score', 0.85)})")
            print("-" * 70)
            print(res.get("grounded_answer", "No response generated."))
            
            # Display Citations
            citations = res.get("citations", [])
            if citations:
                print("\n📚 Verified Source Citations:")
                for c in citations:
                    print(f"  • [{c.get('citation_index')}] {c.get('pdf_filename')} (Page {c.get('primary_page')}) — {c.get('heading')}")
            
            # Display Connected Subgraph
            subgraph = res.get("subgraph", {})
            nodes = subgraph.get("nodes", [])
            if nodes:
                print(f"\n🕸️ Connected Neo4j Subgraph Entities ({len(nodes)} nodes):")
                for n in nodes[:6]:
                    print(f"  • ({n.get('label', 'Entity')}): {n.get('name', n.get('id', ''))}")
            
            # Store Trajectory in Reasoning Memory
            memory.record_trajectory(
                query=query,
                tools_used=res.get("selected_tools", ["tool_vector_search", "tool_cypher_subgraph"]),
                resolved_entities={},
                metrics=[],
                confidence=res.get("traceability_score", 0.85),
                passed=res.get("grounded", True)
            )
            print("-" * 70)
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting RAISE Studio CLI. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error executing query]: {e}")


if __name__ == "__main__":
    main()

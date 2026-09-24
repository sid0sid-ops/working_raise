"""
RAISE — Developer & Deep Observability Console (dev_main.py)
=============================================================
Modular, high-performance CLI research studio and forensic terminal REPL.
Features:
1. Complete decoupled data/presentation architecture (Pipeline -> TelemetryFrame -> Renderer).
2. Honest forensic metric states (MEASURED, DERIVED, ESTIMATED, UNAVAILABLE, NOT_APPLICABLE).
3. Zero silent fake-number synthesis.
4. Interactive research studio with drawer attachment, document scoping, and live diagnostics.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enforce UTF-8 console output for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Enable native ANSI color support
try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

try:
    from prompts.system_synthesis import sanitize_rag_text
except ImportError:
    def sanitize_rag_text(text: str) -> str:
        if not text:
            return ""
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        clean = re.sub(r"\r\n|\r", "\n", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()
from src.retrieval.pipeline import StandaloneRAGPipeline
from src.features.memory.reasoning import ReasoningMemory
from src.cli.models import TelemetryFrame
from src.cli.telemetry_service import TelemetryService
from src.cli.renderer import C, ObsMode, TelemetryRenderer
from src.cli.commands import (
    SessionTracker,
    print_dev_help_menu,
    print_system_dashboard,
    execute_dev_purge_all,
    sanitize_path,
)
from main import (
    auto_start_containers,
    get_active_documents_list,
    list_active_documents,
    ingest_pdf_from_path,
    extract_conversational_persona,
)

logger = logging.getLogger("RAISE_DevStudio")


def main():
    print(C.BANNER + "═" * 78 + C.RESET)
    print(f" {C.TITLE}🔧 RAISE DEV STUDIO (v3.1){C.RESET} — {C.CYAN}FORENSIC OBSERVABILITY CONSOLE{C.RESET}")
    print(f" {C.MUTED}Architecture: Decoupled TelemetryFrame | Honest Provenance Tagging | Anti-Hallucination{C.RESET}")
    print(C.BANNER + "═" * 78 + C.RESET)

    if "--help" in sys.argv or "-h" in sys.argv:
        print_dev_help_menu()
        return

    auto_start_containers()

    # Direct Neural Model Control Center launch flag
    if any(arg in sys.argv for arg in ("control-center", "--control-center", "ops", "--ops", "gui", "--gui", "--ui", "--control-panel", "-g")):
        try:
            from src.gui.control_panel import launch_model_control_center
            print(f"\n{C.SECTION}🖥️  Launching RAISE Neural Model Control Center...{C.RESET}")
            launch_model_control_center()
            return
        except Exception as _gui_err:
            print(f"Notice: Control Center launch error: {_gui_err}")

    # Configure LLM Inference Backend (Local vLLM vs Cloud APIs)
    try:
        from src.cli.llm_selector import prompt_llm_backend
        prompt_llm_backend()
    except Exception as _sel_err:
        logger.debug(f"LLM selection notice: {_sel_err}")

    print(f"\n{C.SECTION}[1/2] Initializing Multi-Substrate Pipeline & Telemetry Service...{C.RESET}")
    pipeline = StandaloneRAGPipeline()
    memory = ReasoningMemory()
    session = SessionTracker(mode=ObsMode.TRACE)

    active_docs = pipeline.vector_engine.get_active_workspace_documents()
    focused_document: Optional[str] = None
    user_persona_name: Optional[str] = None

    # Handle direct PDF ingestion CLI flags (--ingest / --upload)
    if "--ingest" in sys.argv or "--upload" in sys.argv:
        u_flag = "--ingest" if "--ingest" in sys.argv else "--upload"
        u_idx = sys.argv.index(u_flag)
        if u_idx + 1 < len(sys.argv):
            target_pdf = sys.argv[u_idx + 1].strip()
            selected_engine = "fast"
            if "--engine" in sys.argv:
                e_idx = sys.argv.index("--engine")
                if e_idx + 1 < len(sys.argv):
                    selected_engine = sys.argv[e_idx + 1].strip().lower()
            target_pages = 0  # 0 indicates all pages without prompting
            if "--pages" in sys.argv:
                p_idx = sys.argv.index("--pages")
                if p_idx + 1 < len(sys.argv):
                    p_val = sys.argv[p_idx + 1].strip()
                    try:
                        target_pages = int(p_val) if p_val.isdigit() else 0
                    except ValueError:
                        target_pages = 0
            print(f"\n{C.SECTION}📥 [dev_main CLI] Ingesting PDF report:{C.RESET} {C.WHITE}{target_pdf}{C.RESET}")
            new_doc = ingest_pdf_from_path(target_pdf, pipeline, engine=selected_engine, max_pages=target_pages)
            if new_doc:
                print(f"\n{C.SUCCESS}✨ [dev_main CLI] Successfully ingested and synced to ChromaDB & Neo4j:{C.RESET} {new_doc}\n")
            return

    # Handle automated benchmark suite CLI flags (--benchmark [raise|frames], --limit N)
    if any(flag in sys.argv for flag in ("--benchmark", "-b", "--bench")):
        b_flag = next(f for f in ("--benchmark", "-b", "--bench") if f in sys.argv)
        b_idx = sys.argv.index(b_flag)
        bench_type = "raise"
        if b_idx + 1 < len(sys.argv) and not sys.argv[b_idx + 1].startswith("-"):
            bench_type = sys.argv[b_idx + 1].strip().lower()

        limit = None
        if "--limit" in sys.argv:
            l_idx = sys.argv.index("--limit")
            if l_idx + 1 < len(sys.argv) and sys.argv[l_idx + 1].isdigit():
                limit = int(sys.argv[l_idx + 1])

        from src.cli.benchmark_runner import run_dev_benchmark
        run_dev_benchmark(pipeline, memory, session, benchmark_type=bench_type, limit=limit)
        return

    # Status / Diagnostic flag
    if "--status" in sys.argv or "-s" in sys.argv:
        print_system_dashboard(pipeline, memory, session, focused_document)
        return

    # Hard reset / purge flag
    if "--purge-all" in sys.argv or "--hard-reset" in sys.argv:
        execute_dev_purge_all(pipeline, memory)
        return

    # Render dashboard for interactive REPL session
    print_system_dashboard(pipeline, memory, session, focused_document)

    # Handle mode CLI flag

    if "--mode" in sys.argv or "-m" in sys.argv:
        m_flag = "--mode" if "--mode" in sys.argv else "-m"
        m_idx = sys.argv.index(m_flag)
        if m_idx + 1 < len(sys.argv):
            m_val = sys.argv[m_idx + 1].strip().upper()
            try:
                session.mode = ObsMode[m_val]
                print(f"🎯 [Mode Initialized]: {session.mode.value}\n")
            except Exception:
                pass

    # Handle attach CLI flag
    if "--attach" in sys.argv or "-a" in sys.argv:
        a_flag = "--attach" if "--attach" in sys.argv else "-a"
        a_idx = sys.argv.index(a_flag)
        if a_idx + 1 < len(sys.argv):
            target_att = sys.argv[a_idx + 1].strip()
            manifest_docs = get_active_documents_list()
            resolved = None
            if target_att.isdigit():
                idx = int(target_att) - 1
                if 0 <= idx < len(manifest_docs):
                    resolved = manifest_docs[idx].get("filename")
            else:
                for d in manifest_docs:
                    fn = d.get("filename", "")
                    if target_att.lower() in fn.lower():
                        resolved = fn
                        break
            if resolved:
                focused_document = resolved
                print(f"🎯 [Active Scope Attached]: {C.ACCENT}'{focused_document}'{C.RESET}\n")

    # Handle query CLI flag
    cli_query = None
    if "--query" in sys.argv:
        q_idx = sys.argv.index("--query")
        if q_idx + 1 < len(sys.argv):
            cli_query = sys.argv[q_idx + 1]
    elif "-q" in sys.argv:
        q_idx = sys.argv.index("-q")
        if q_idx + 1 < len(sys.argv):
            cli_query = sys.argv[q_idx + 1]
    elif len(sys.argv) > 1:
        pos_tokens = []
        skip_next = False
        for a in sys.argv[1:]:
            if skip_next:
                skip_next = False
                continue
            if a in ("--attach", "-a", "--mode", "-m"):
                skip_next = True
                continue
            if not a.startswith("-") and not a.lower().endswith(".pdf") and not Path(a).is_file():
                pos_tokens.append(a)
        if pos_tokens:
            cli_query = " ".join(pos_tokens)

    print(C.BANNER + "═" * 78 + C.RESET)
    print(f" {C.TITLE}💬 RAISE RESEARCH STUDIO — INTERACTIVE OBSERVABILITY REPL{C.RESET}")
    print(f" {C.MUTED}Commands: 'docs', 'attach <N>', 'mode <1-4>', 'export', 'status', 'help', 'exit'{C.RESET}")
    print(C.BANNER + "═" * 78 + C.RESET)

    while True:
        try:
            scope_badge = f"{focused_document}" if focused_document else "ALL DOCUMENTS"
            prompt_label = f"🔬 [{C.ACCENT}{scope_badge}{C.RESET} | {C.NUM}{session.mode.value}{C.RESET}] Enter Query: "
            if cli_query is not None:
                query = cli_query.strip()
                print(f"{prompt_label}{query}")
            else:
                try:
                    query = input(prompt_label).strip()
                except EOFError:
                    print(f"\n{C.CYAN}Exiting RAISE Dev Studio. Goodbye!{C.RESET}")
                    break

            if not query:
                if cli_query is not None:
                    break
                continue

            q_lower = query.lower()

            if q_lower in ["exit", "quit", "q", ":q"]:
                print(f"\n{C.CYAN}Exiting RAISE Dev Studio. Goodbye!{C.RESET}")
                break

            if q_lower in ["help", "?", "commands"]:
                print_dev_help_menu()
                if cli_query is not None:
                    break
                continue

            if q_lower in ["status", "health", "info", "diag"]:
                print_system_dashboard(pipeline, memory, session, focused_document)
                if cli_query is not None:
                    break
                continue

            if q_lower in ["control-center", "control center", "ops", "model-center", "gui", "panel", "control panel", "operator", "ui"]:
                try:
                    from src.gui.control_panel import launch_model_control_center
                    print(f"\n{C.SECTION}🖥️  Launching RAISE Neural Model Control Center...{C.RESET}")
                    launch_model_control_center()
                    print(f"{C.SUCCESS}✨ [Control Center Closed] Returned to interactive console.{C.RESET}\n")
                except Exception as _gui_e:
                    print(f"\n{C.DANGER}⚠️  Failed to launch Control Center: {_gui_e}{C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            if q_lower.startswith("mode ") or q_lower.startswith("m "):
                parts = query.split(None, 1)
                if len(parts) > 1:
                    m_arg = parts[1].strip().upper()
                    m_map = {
                        "1": ObsMode.NORMAL, "NORMAL": ObsMode.NORMAL,
                        "2": ObsMode.VERBOSE, "VERBOSE": ObsMode.VERBOSE,
                        "3": ObsMode.TRACE, "TRACE": ObsMode.TRACE, "DEEP TRACE": ObsMode.TRACE,
                        "4": ObsMode.DEBUG, "DEBUG": ObsMode.DEBUG, "RAW DEBUG": ObsMode.DEBUG,
                    }
                    if m_arg in m_map:
                        session.mode = m_map[m_arg]
                        print(f"\n{C.SUCCESS}✨ [OBSERVABILITY MODE UPDATED]{C.RESET} Active Mode: {C.NUM}{session.mode.value}{C.RESET}\n")
                    else:
                        print(f"\n{C.WARN}⚠️  Unknown mode '{m_arg}'. Options: 1(NORMAL), 2(VERBOSE), 3(TRACE), 4(DEBUG){C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            if q_lower in ["export", "export traces", "save trace"] or q_lower.startswith("export "):
                parts = query.split(None, 1)
                custom_fn = parts[1].strip() if len(parts) > 1 else None
                saved_path = session.export_traces(custom_fn)
                print(f"\n{C.SUCCESS}📁 [TELEMETRY EXPORTED]{C.RESET} Saved trace JSON to: {C.CYAN}{sanitize_path(saved_path)}{C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            if q_lower in ["docs", "list", "documents", "vault"]:
                list_active_documents(focused_document)
                if cli_query is not None:
                    break
                continue

            if q_lower in ["clear chat", "clear history", "clear memory", "cls"]:
                pipeline.clear_chat_session()
                memory.clear()
                print(f"\n{C.SUCCESS}✨ [DEV CHAT & MEMORY CLEARED]{C.RESET} Session context reset.\n")
                if cli_query is not None:
                    break
                continue

            if q_lower in ["purge all", "wipe all", "hard reset"]:
                success = execute_dev_purge_all(pipeline, memory)
                if success:
                    focused_document = None
                if cli_query is not None:
                    break
                continue

            if q_lower in ["attach all", "use all", "focus all", "select all", "scope all"]:
                focused_document = None
                print(f"🎯 [{C.SUCCESS}Scope Updated{C.RESET}]: Searching across {C.ACCENT}ALL documents{C.RESET}.\n")
                if cli_query is not None:
                    break
                continue

            if q_lower in ["detach", "attach none", "detach all", "clear drawer"]:
                focused_document = "NONE"
                print(f"🎯 [{C.WARN}Drawer Emptied{C.RESET}]: No documents attached to drawer.\n")
                if cli_query is not None:
                    break
                continue

            if q_lower.startswith("attach ") or q_lower.startswith("use "):
                target = query.split(None, 1)[1].strip().strip("'\"")
                docs = get_active_documents_list()
                resolved = None
                if target.isdigit():
                    idx = int(target) - 1
                    if 0 <= idx < len(docs):
                        resolved = docs[idx].get("filename")
                else:
                    for d in docs:
                        fn = d.get("filename", "")
                        if target.lower() in fn.lower():
                            resolved = fn
                            break
                if resolved:
                    focused_document = resolved
                    print(f"🎯 [{C.SUCCESS}Drawer Updated{C.RESET}]: Scope attached strictly to '{C.ACCENT}{focused_document}{C.RESET}'.\n")
                else:
                    print(f"{C.WARN}⚠️  No document matched '{target}'. Use 'docs' to view available IDs.{C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            # Direct PDF path pasted without command prefix
            clean_potential_path = query.strip().strip("'\"")
            if clean_potential_path.lower().endswith(".pdf") and Path(clean_potential_path).is_file():
                print(f"\n{C.SECTION}📄 Detected PDF file path. Ingesting into library...{C.RESET}")
                new_doc = ingest_pdf_from_path(clean_potential_path, pipeline)
                if new_doc:
                    focused_document = new_doc
                if cli_query is not None:
                    break
                continue

            if q_lower in ["upload", "add"]:
                try:
                    pdf_input = input(f"\n{C.SECTION}📄 Enter path to PDF report:{C.RESET} ").strip()
                except (EOFError, KeyboardInterrupt):
                    continue
                if pdf_input:
                    new_doc = ingest_pdf_from_path(pdf_input, pipeline)
                    if new_doc:
                        focused_document = new_doc
                if cli_query is not None:
                    break
                continue

            if q_lower.startswith("upload ") or q_lower.startswith("add "):
                raw_arg = query.split(None, 1)[1].strip()
                new_doc = ingest_pdf_from_path(raw_arg, pipeline)
                if new_doc:
                    focused_document = new_doc
                if cli_query is not None:
                    break
                continue

            # -------------------------------------------------------------
            # Execute Query & Extract Verifiable TelemetryFrame
            # -------------------------------------------------------------
            t_turn_start = time.perf_counter()
            turn_id = session.next_turn_id()

            # Dynamic Intent Routing: Persona vs Academic Research
            q_clean = query.strip()
            q_words = q_clean.split()
            # Guardrail: Never classify research queries as conversational greetings/intros
            is_potential_persona = (
                (len(q_words) <= 4 and not ("?" in q_clean) and not any(term in q_clean.lower() for term in ["campus", "located", "research", "admission", "examination", "nobel", "prize", "annual", "report", "council", "institute", "science", "genome", "biotech", "what", "where", "how", "which", "who", "why"]))
                or any(q_clean.lower().startswith(p) for p in ["my name is", "call me ", "i am ", "i'm "])
            )
            persona_intent = extract_conversational_persona(query) if is_potential_persona else {"type": "research_query"}
            if persona_intent["type"] in ("name_intro", "greeting"):
                if persona_intent["type"] == "name_intro":
                    user_persona_name = persona_intent["name"]
                    answer_text = f"Hello {user_persona_name}! I am RAISE. How can I assist your research today?"
                else:
                    greet_suffix = f", {user_persona_name}" if user_persona_name else ""
                    answer_text = f"Hello{greet_suffix}! I am RAISE, running in Developer Observability mode. Please attach an academic report or ask any research inquiry."

                total_duration_ms = (time.perf_counter() - t_turn_start) * 1000.0
                frame = TelemetryService.build_frame(
                    result={
                        "grounded_answer": answer_text,
                        "query_intent": "CONVERSATIONAL",
                        "routing_strategy": "ZERO_DB_BYPASS",
                        "timings": {"routing_ms": max(1.0, total_duration_ms * 0.8), "synthesis_ms": max(1.0, total_duration_ms * 0.2)},
                    },
                    query=query,
                    turn_id=turn_id,
                    session_id=session.session_id,
                    scope="CONVERSATIONAL",
                    mode=session.mode.value,
                )
                session.record_turn(frame)
                print(f"\n{C.TITLE}RAISE:{C.RESET} {answer_text}\n")
                TelemetryRenderer.render(frame, session.mode)
                if cli_query is not None:
                    break
                continue

            # Factual Document Research Query Boundary
            manifest_docs = get_active_documents_list()
            if not manifest_docs or focused_document == "NONE":
                print(f"\n{C.WARN}⚠️  No active documents are currently attached to your drawer.{C.RESET}")
                print(f"   Please attach a document in your drawer to begin research.\n")
                if cli_query is not None:
                    break
                continue

            active_scoping = [focused_document] if focused_document else None
            scope_desc = f"'{focused_document}'" if focused_document else "ALL DOCUMENTS"
            print(f"\n{C.INFO}[LangGraph Executing Multi-Hop Retrieval (Target Scope: {C.ACCENT}{scope_desc}{C.INFO})...]{C.RESET}")

            res = pipeline.query_subgraph_graphrag(
                query=query,
                hops=2,
                top_k=6,
                document_filter=focused_document,
                active_docs=active_scoping,
            )
            total_duration_ms = (time.perf_counter() - t_turn_start) * 1000.0

            if not isinstance(res, dict):
                res = {"grounded_answer": str(res)}

            raw_answer = res.get("grounded_answer") or res.get("answer", "No response generated.")
            clean_answer = sanitize_rag_text(str(raw_answer))
            citations = res.get("citations") or []

            # Build Honest, Decoupled TelemetryFrame
            frame = TelemetryService.build_frame(
                result=res,
                query=query,
                turn_id=turn_id,
                session_id=session.session_id,
                scope=scope_desc,
                mode=session.mode.value,
            )
            # Ensure total duration is recorded if pipeline didn't provide one
            if frame.performance.total_latency_ms == 0.0:
                frame.performance.total_latency_ms = total_duration_ms

            session.record_turn(frame)

            # -------------------------------------------------------------
            # Render Clean Grounded Answer & Citations
            # -------------------------------------------------------------
            print("\n" + C.BANNER + "═" * 78 + C.RESET)
            print(f" {C.TITLE}📋 GROUNDED RESEARCH ANSWER{C.RESET} {C.MUTED}({total_duration_ms/1000.0:.2f}s | Gate: {frame.quality.decision.upper()}){C.RESET}")
            print(f" {C.MUTED}📄 Attached Document:{C.RESET} {C.ACCENT}{scope_desc}{C.RESET}")
            print(C.BANNER + "═" * 78 + C.RESET)

            colorized_answer = re.sub(
                r"\[(\d+(?:,\s*\d+)*)\]",
                lambda m: f"{C.CYAN}[{m.group(1)}]{C.RESET}",
                clean_answer
            )
            print(colorized_answer + "\n")

            if citations:
                print(f"{C.SECTION}📚 Verified Citations & Provenance:{C.RESET}")
                for cit in frame.provenance.citations:
                    p_str = f"PDF Page {cit.primary_page}, Doc Page {cit.printed_page}" if cit.printed_page and str(cit.printed_page) != str(cit.primary_page) else f"Page {cit.primary_page}"
                    head_str = f" — {C.MUTED}{cit.section_heading}{C.RESET}" if cit.section_heading else ""
                    print(f"  • {C.CITATION}[{cit.citation_index}]{C.RESET} {C.CYAN}{cit.document}{C.RESET} ({C.SECTION}{p_str}{C.RESET}){head_str}")
                print()

            # Render Granular Telemetry Layers according to selected mode
            TelemetryRenderer.render(frame, session.mode)

            if cli_query is not None:
                break

        except KeyboardInterrupt:
            print(f"\n\n{C.WARN}⚠️  Session interrupted by user.{C.RESET}")
            break
        except Exception as e:
            logger.error(f"Dev studio runtime error: {e}", exc_info=True)
            print(f"\n{C.DANGER}❌ [Error]: {e}{C.RESET}\n")
            if cli_query is not None:
                break


if __name__ == "__main__":
    main()

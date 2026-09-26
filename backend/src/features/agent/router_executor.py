"""
Agent Plan Executor & Grounded Answer Synthesizer Mixin
=======================================================
Executes multi-tool retrieval plans, enforces Lost-in-the-Middle attention mitigation,
manages LLM inference provider dispatch, and builds anti-hallucination answer contracts.

Architectural Role & Pipeline Flow:
-----------------------------------
1. Workspace Safety Boundary:
   - Immediately returns clean notice if `active_docs` is empty (`[]`), making 0 external calls.

2. Candidate Collection & Reciprocal Rank Fusion:
   - Merges dense vector hits with sparse lexical BM25 candidates using RRF.
   - Ensures title/contact page (`p001`) is preserved when a specific document is targeted.

3. Context Optimization:
   - Reranks fused candidates with Cross-Encoder.
   - Hydrates macro-chunk parent sections to give the LLM full contextual paragraphs.
   - Applies Lost-in-the-Middle sandwich reordering: [c1, c3, c5, c6, c4, c2] placing top evidence
     at the primacy (head) and recency (tail) positions where attention is strongest.

4. LLM Synthesis & Provider Fallback:
   - Dispatches prompt to the active inference provider (Local vLLM, Groq, or OpenAI fallback).
   - If LLM is unreachable, falls back to deterministic structured excerpt assembly.

5. Verification & Citations:
   - Verifies claims via `ClaimVerifier` and generates an `AnswerContract`.
   - Renumbers in-text citation brackets to strictly consecutive `[1..N]` order, eliminating gaps.
   - Generates 3 relevant contextual follow-up inquiries.

How to Update or Tune:
----------------------
- To change evidence block formatting, see `evidence_blocks` loop in `execute_plan()`.
- To modify max synthesis tokens, adjust `safe_max_tokens` calculation.
- To adjust follow-up question generation prompt, edit `fu_prompt` in `execute_plan()`.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .router_models import AgentExecutionPlan
from .follow_ups import generate_follow_up_inquiries
from src.retrieval.fusion import document_to_chunk, reciprocal_rank_fusion, hydrate_macro_chunks
from src.features.verification.math_engine import DeterministicMathEngine
from src.features.verification.fact_engine import NumericFact


class PlanExecutorMixin:
    """Provides candidate retrieval, context sandwiching, and grounded response synthesis."""

    @staticmethod
    def _reorder_context_sandwich(items: List[Any]) -> List[Any]:
        """
        Applies Lost-in-the-Middle mitigation by reordering ranked evidence chunks.
        Places highest-priority items at the start (primacy) and end (recency),
        pushing lower-priority items to the middle where transformer attention is lowest.
        Input : [c1, c2, c3, c4, c5, c6]
        Output: [c1, c3, c5, c6, c4, c2]
        """
        if len(items) <= 2:
            return list(items)
        head = []
        tail = []
        for idx, item in enumerate(items):
            if idx % 2 == 0:
                head.append(item)
            else:
                tail.insert(0, item)
        return head + tail

    def execute_plan(
        self,
        plan: AgentExecutionPlan,
        active_docs: Optional[List[str]] = None,
    ) -> AgentExecutionPlan:
        """Execute dynamic retrieval and synthesize clean, 100% grounded response from uploaded PDF content."""
        if active_docs is not None and len(active_docs) == 0:
            plan.grounded_answer = "No active documents are currently attached to your drawer. Please attach a document in the drawer to begin research."
            plan.traceability_score = 1.0
            plan.citations = []
            plan.verified_claims = []
            return plan

        q_lower = plan.query.lower()
        facts: List[NumericFact] = []
        chunks: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        active_doc_list = active_docs if active_docs is not None else self._get_active_documents()
        target_doc = plan.retrieved_evidence.get("target_doc_filter")

        # 1. Gather Candidates: Use pre-retrieved fused chunks if provided, else run hybrid Dense + BM25
        pre_chunks = plan.retrieved_evidence.get("chunks")
        if pre_chunks and len(pre_chunks) > 0:
            raw_chunks = [document_to_chunk(c) for c in pre_chunks]
        else:
            raw_chunks = self.vector_engine.search(
                query=plan.query,
                top_k=12,
                doc_filter=target_doc,
                active_docs=active_doc_list,
            )
            bm25_hits = self._get_bm25_search(
                query=plan.query,
                top_k=12,
                doc_filter=target_doc,
                active_docs=active_doc_list,
            )
            if bm25_hits:
                raw_chunks = reciprocal_rank_fusion(
                    [raw_chunks, bm25_hits],
                    k=60,
                    table_boost=True,
                )

        # If a single document is targeted and has small chunk count, ensure chunk 1 (header/contacts) is included
        if target_doc and raw_chunks:
            chunk_ids = [c.get("chunk_id", "") for c in raw_chunks]
            doc_stem = Path(target_doc).stem
            p001_id = f"{doc_stem}_p001"
            if not any(p001_id in cid for cid in chunk_ids):
                try:
                    c1 = self.vector_engine.collection.get(ids=[p001_id], include=["documents", "metadatas"])
                    if c1 and c1.get("ids") and len(c1["ids"]) > 0:
                        c1_chunk = {
                            "id": c1["ids"][0],
                            "chunk_id": c1["ids"][0],
                            "text": c1["documents"][0],
                            "similarity": 0.90,
                            "metadata": c1["metadatas"][0],
                        }
                        raw_chunks.append(c1_chunk)
                except Exception:
                    pass

        # 2. Contextual Cross-Encoder Reranking
        chunks = self.reranker.rerank(
            query=plan.query,
            candidates=raw_chunks,
            text_key="text",
            top_n=8,
        )

        # GraphRAG Macro-Chunk Hydration: expand child snippets into rich parent sections
        chunks = hydrate_macro_chunks(chunks)

        # For contact/author queries, ensure chunk 1 is prioritized at top if present
        if any(w in q_lower for w in ["phone", "mobile", "contact", "email", "name", "who", "author", "candidate"]):
            c1_idx = next((i for i, c in enumerate(chunks) if "p001" in (c.get("chunk_id") or c.get("id") or "")), None)
            if c1_idx is not None and c1_idx > 0:
                c1_val = chunks.pop(c1_idx)
                chunks.insert(0, c1_val)

        # Apply Lost-in-the-Middle sandwich reordering to top chunks so prompt evidence and citations align 1-to-1
        ordered_chunks = self._reorder_context_sandwich(chunks[:6]) + chunks[6:]
        plan.retrieved_evidence["chunks"] = ordered_chunks

        seen_cids = set()
        for idx, c in enumerate(ordered_chunks):
            meta = c.get("metadata", {})
            cid = str(meta.get("chunk_id") or c.get("id") or f"chk_{idx+1}")
            if cid not in seen_cids:
                seen_cids.add(cid)
                raw_t = c.get("text", "")
                cleaned_excerpt = re.sub(r"\[Section Context:[^\]]*\]", "", raw_t, flags=re.IGNORECASE)
                cleaned_excerpt = re.sub(r"Institution:.*?\n|Document:.*?\n|Period:.*?\n|Page:.*?\n|Heading:.*?\n|Content:\s*", "", cleaned_excerpt).strip()
                cleaned_excerpt = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned_excerpt)
                cleaned_excerpt = re.sub(r'\s+', ' ', cleaned_excerpt).strip()

                # Resolve physical page
                p_page = meta.get("primary_page") or meta.get("physical_page") or meta.get("page")
                if not p_page or int(p_page) < 1:
                    match = re.search(r"_p0*(\d+)", cid)
                    p_page = int(match.group(1)) if match else 1
                p_page = int(p_page)

                # Resolve PDF filename
                pdf_name = meta.get("pdf_filename") or meta.get("filename") or (active_doc_list[0] if active_doc_list else "Annual Report.pdf")
                d_page = meta.get("printed_page")

                citations.append({
                    "citation_index": idx + 1,
                    "chunk_id": cid,
                    "document_id": meta.get("doc_id") or meta.get("document_id") or Path(pdf_name).stem,
                    "pdf_filename": pdf_name,
                    "primary_page": p_page,
                    "printed_page": d_page if (d_page and str(d_page).strip() != "") else None,
                    "heading": meta.get("heading") or f"Section (Page {p_page})",
                    "plain_text": cleaned_excerpt[:500],
                    "university": meta.get("university", "Academic Institution"),
                    "similarity": round(float(c.get("similarity", 0.88)), 3),
                })

        # 2. Extract Structured Facts if available
        if "structured_fact_search" in plan.selected_tools:
            uni = plan.extracted_universities[0] if plan.extracted_universities else None
            facts = self.fact_engine.query_facts(university=uni)
            if active_doc_list:
                active_stems = [Path(f).stem for f in active_doc_list]
                facts = [f for f in facts if f.document_id in active_stems or f.document_id in active_doc_list]
            plan.retrieved_evidence["facts"] = [f.to_dict() for f in facts]

        # 3. Dynamic Grounded Answer Synthesis
        claims: List[str] = []
        answer_parts: List[str] = []

        if ordered_chunks:
            doc_groups: Dict[str, List[Dict[str, Any]]] = {}
            for c in ordered_chunks:
                meta = c.get("metadata", {})
                pdf_name = meta.get("pdf_filename") or "Uploaded Report"
                doc_groups.setdefault(pdf_name, []).append(c)

            cit_lookup = {c["chunk_id"]: c["citation_index"] for c in citations}

            # Attempt LLM Grounded Generation via Unified Provider Router
            llm_response = None
            math_result = None
            try:
                # Deterministic math pre-computation check
                math_intent = DeterministicMathEngine.detect_math_intent(plan.query)
                if math_intent:
                    operands, m_unit = self._extract_math_operands(plan.query, ordered_chunks, math_intent)
                    if len(operands) >= 2:
                        math_result = DeterministicMathEngine.compute(math_intent, operands, units=m_unit)
            except Exception:
                pass

            try:
                from src.infrastructure.providers.router import get_provider_router, InferenceTask
                router = get_provider_router()
                evidence_blocks = []
                for idx, c in enumerate(ordered_chunks[:6]):
                    meta = c.get("metadata", {})
                    p_page = meta.get("primary_page", 1)
                    d_page = meta.get("printed_page")
                    doc_p_str = f", Doc Page {d_page}" if (d_page and str(d_page).strip() != "" and str(d_page) != str(p_page)) else ""
                    evidence_blocks.append(
                        f"[{idx+1}] [Doc: {meta.get('pdf_filename')}, PDF Page {p_page}{doc_p_str}, Heading: {meta.get('heading')}]:\n{self._extract_relevant_chunk_text(c.get('text') or '', plan.query, max_chars=4000)}"
                    )
                subgraph = plan.retrieved_evidence.get("subgraph")
                if subgraph and (subgraph.get("edges") or subgraph.get("nodes")):
                    graph_facts = []
                    for edge in subgraph.get("edges", []):
                        graph_facts.append(f"• Verified Knowledge Graph Fact: {edge.get('source')} --[{edge.get('type')}]--> {edge.get('target')}")
                    if graph_facts:
                        evidence_blocks.append("Verified Institutional Knowledge Graph Facts:\n" + "\n".join(graph_facts[:8]))

                if active_doc_list:
                    evidence_blocks.insert(0, f"[STRICT DRAWER BOUNDARY: The user is querying ONLY the active documents attached to their drawer: {', '.join(active_doc_list)}. Answer strictly and exclusively using excerpts from these attached documents. Disregard any unattached documents in the library.]")

                if math_result and math_result.is_verified:
                    math_block = (
                        f"[DETERMINISTIC VERIFIED CALCULATION]:\n"
                        f"Operation: {math_result.operation}\n"
                        f"Formula: {math_result.formula_expression}\n"
                        f"Result: {math_result.formatted_result}\n"
                        f"INSTRUCTION: You MUST use this verified calculation in your answer. Do NOT re-calculate or approximate."
                    )
                    evidence_blocks.append(math_block)

                prompt_evidence = "\n\n".join(evidence_blocks)
                try:
                    from prompts.system_synthesis import get_synthesis_system_prompt
                    base_sys_prompt = get_synthesis_system_prompt()
                except Exception:
                    sys_prompt_path = Path(__file__).resolve().parent.parent.parent.parent / "prompts" / "system_synthesis.md"
                    base_sys_prompt = sys_prompt_path.read_text(encoding="utf-8").strip() if sys_prompt_path.exists() else "You are an audited institutional intelligence system. Answer strictly using only provided document excerpts with [1], [2] citations."
                user_prompt = f"User Query: {plan.query}\n\nDocument Evidence:\n{prompt_evidence}\n\nGrounded Answer:"

                est_prompt_tokens = (len(base_sys_prompt.split()) + len(user_prompt.split())) * 4 // 3
                safe_max_tokens = min(1024, max(256, 7900 - est_prompt_tokens))

                prov = router.get_provider_for_task(InferenceTask.RAG_GENERATION)
                llm_response = router.complete(
                    prompt=user_prompt,
                    task=InferenceTask.RAG_GENERATION,
                    system_prompt=base_sys_prompt,
                    max_tokens=safe_max_tokens,
                    temperature=0.1,
                )

                if llm_response and not any(llm_response.startswith(pfx) for pfx in ("Inference execution error", "Error executing inference", "Cloud LLM error", "Ollama error")):
                    compl_info = getattr(router, "get_last_completion_info", lambda: {})()
                    actual_provider = compl_info.get("provider") or prov.name
                    actual_model = compl_info.get("model") or getattr(prov, "model_name", "default")
                    plan.synthesis_metadata = {
                        "provider": actual_provider,
                        "model": actual_model,
                        "prompt_tokens": est_prompt_tokens,
                        "completion_tokens": len(llm_response.split()) * 4 // 3,
                        "total_tokens": est_prompt_tokens + len(llm_response.split()) * 4 // 3,
                    }
                else:
                    llm_response = None
            except Exception as e:
                print(f"[Router Synthesis Notice]: {e}")
                llm_response = None

            if llm_response:
                prov_name = plan.synthesis_metadata.get("provider", "LLM").upper() if plan.synthesis_metadata else "LLM"
                model_lbl = plan.synthesis_metadata.get("model", "") if plan.synthesis_metadata else ""
                print(f"[{prov_name} Synthesis Success]: Generated {len(llm_response)} chars from {model_lbl}")
                raw_answer = llm_response
                if math_result:
                    claims.append(f"Mathematically Verified ({math_result.operation}): {math_result.formula_expression} = {math_result.formatted_result}")
                for c in ordered_chunks:
                    meta = c.get("metadata", {})
                    pno = meta.get("primary_page", 1)
                    doc_p = meta.get("printed_page")
                    page_str = f"PDF Page {pno}, Doc Page {doc_p}" if (doc_p and str(doc_p).strip() != "" and str(doc_p) != str(pno)) else f"Page {pno}"
                    pdf_name = meta.get("pdf_filename", "Document.pdf")
                    claims.append(f"{pdf_name} ({page_str}): Verified via LLM Grounding.")
            else:
                answer_parts.append(f"Based on the verified excerpts from your uploaded institutional reports:\n")
                findings = []
                if math_result:
                    findings.append(f"• **Deterministic Mathematical Pre-computation** ({math_result.operation}):\n  {math_result.formula_expression} → **Result: {math_result.formatted_result} {math_result.units or ''}**")
                    claims.append(f"Mathematically Verified ({math_result.operation}): {math_result.formula_expression} = {math_result.formatted_result}")
                for idx, c in enumerate(ordered_chunks):
                    meta = c.get("metadata", {})
                    cid = str(meta.get("chunk_id") or c.get("id") or "")
                    cit_num = cit_lookup.get(cid, idx + 1)
                    pno = meta.get("primary_page", 1)
                    doc_p = meta.get("printed_page")
                    page_str = f"PDF Page {pno}, Doc Page {doc_p}" if (doc_p and str(doc_p).strip() != "" and str(doc_p) != str(pno)) else f"Page {pno}"
                    pdf_name = meta.get("pdf_filename") or "Report.pdf"
                    heading = meta.get("heading") or f"Section ({page_str})"
                    raw_text = c.get("text", "")
                    cleaned_body = re.sub(
                        r"Institution:.*?\n|Document:.*?\n|Period:.*?\n|Page:.*?\n|Heading:.*?\n|Content:\s*",
                        "",
                        raw_text,
                    ).strip()

                    q_words = set(w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", plan.query) if w.lower() not in {"what", "the", "and", "for", "with", "show", "tell", "total", "who", "user", "name", "your"})
                    body_lines = [l.strip() for l in cleaned_body.splitlines() if l.strip()]
                    
                    best_match_idx = -1
                    best_overlap = 0
                    for line_i, line in enumerate(body_lines):
                        line_lower = line.lower()
                        overlap = sum(1 for qw in q_words if qw in line_lower)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_match_idx = line_i

                    selected_content = ""
                    if best_match_idx != -1 and best_overlap > 0:
                        extracted_lines = [body_lines[best_match_idx]]
                        for f_idx in range(best_match_idx + 1, min(best_match_idx + 4, len(body_lines))):
                            nxt = body_lines[f_idx]
                            if any(nxt.startswith(pfx) for pfx in ["-", "•", "*", "–"]) or re.match(r"^\d+[\.\)]", nxt) or (len(nxt) < 120 and not nxt.startswith("Chapter") and not re.search(r"\b(year|fy|q1|q2|table|total)\b", nxt.lower())) or any(qw in nxt.lower() for qw in q_words):
                                extracted_lines.append(nxt)
                            else:
                                break
                        selected_content = "\n  ".join(extracted_lines)
                    else:
                        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_body) if len(s.strip()) > 15]
                        matched_sentences = [
                            s for s in sentences 
                            if any(qw in s.lower() for qw in q_words) or re.search(r"(\bRs\.?|INR|\d+(?:\.\d+)?\s*(?:crore|lakh|%)|\b20\d\d\b)", s, re.IGNORECASE)
                        ]
                        if matched_sentences:
                            selected_content = matched_sentences[0]
                        elif sentences and idx == 0:
                            selected_content = sentences[0]
                        elif idx == 0:
                            selected_content = cleaned_body[:200]

                    if selected_content:
                        findings.append(f"• **{heading}** [[{cit_num}]]:\n  {selected_content}")
                        claims.append(f"{pdf_name} ({page_str}): {selected_content.replace(chr(10), ' ')[:140]}")

                if findings:
                    answer_parts.append("\n\n".join(findings))
                    raw_answer = "\n".join(answer_parts)
                else:
                    raw_answer = f"The uploaded institutional documents do not contain information related to '{plan.query}'. They cover institutional governance, sponsored research grants, academic degrees, and startup incubation."
        else:
            raw_answer = "INSUFFICIENT_EVIDENCE: No matching verified statements or passages were found in the uploaded document(s) for your query."
            claims.append("INSUFFICIENT_EVIDENCE: No matching statements found in uploaded document(s).")

        # 4. Anti-Hallucination Claim Verification
        contract = self.verifier.create_answer_contract(
            answer_text=raw_answer,
            claims=claims,
            query=plan.query,
            retrieved_facts=facts,
            retrieved_chunks=chunks,
            comparability="COMPARABLE",
        )

        plan.answer_contract = contract.to_dict()
        plan.verified_claims = [c.to_dict() for c in contract.claims]
        plan.traceability_score = contract.grounding_score

        # Strip negative meta-commentary explaining omitted/irrelevant passages
        raw_answer = re.sub(
            r'(?:(?:Excerpts?|Passages?|Sources?|References?)\s*(?:\[\d+\][,\s&and–-]*)+[^.\n]*(?:omitted|excluded|not\s+(?:used|relevant)|do\s+not\s+pertain|pertain\s+to|refer\s+to|irrelevant)[^.\n]*[.\n]?)',
            '',
            raw_answer,
            flags=re.IGNORECASE,
        ).strip()

        plan.grounded_answer = raw_answer
        
        found_indices = []
        for m in re.finditer(r"\[\[?([0-9\s,\-–]+)\]?\]", raw_answer):
            for part in re.findall(r"\d+", m.group(1)):
                try:
                    p_int = int(part)
                    if p_int not in found_indices:
                        found_indices.append(p_int)
                except ValueError:
                    pass

        if found_indices:
            # Map original citation indices to strictly consecutive 1..N order
            index_mapping = {old_idx: new_idx for new_idx, old_idx in enumerate(found_indices, 1)}

            def _replace_cit(match):
                sub_parts = re.findall(r"\d+", match.group(1))
                new_parts = [str(index_mapping.get(int(sp), sp)) for sp in sub_parts if sp.isdigit()]
                return f"[{', '.join(new_parts)}]"

            raw_answer = re.sub(r"\[\[?([0-9\s,\-–]+)\]?\]", _replace_cit, raw_answer)
            plan.grounded_answer = raw_answer

            filtered_cits = []
            for old_idx in found_indices:
                matching = [c for c in citations if c.get("citation_index") == old_idx]
                if matching:
                    cit_copy = dict(matching[0])
                    cit_copy["citation_index"] = index_mapping[old_idx]
                    filtered_cits.append(cit_copy)
            plan.citations = filtered_cits if filtered_cits else citations
        else:
            plan.grounded_answer = raw_answer
            plan.citations = citations

        if plan.grounded_answer:
            try:
                from prompts.system_synthesis import sanitize_rag_text
            except ImportError:
                from RAG.prompts.system_synthesis import sanitize_rag_text
            plan.grounded_answer = sanitize_rag_text(plan.grounded_answer)

        # 4. Generate 3 contextual follow-up inquiries
        plan.follow_up_inquiries = generate_follow_up_inquiries(
            query=plan.query,
            grounded_answer=plan.grounded_answer or "",
            citations=plan.citations or citations,
        )

        return plan

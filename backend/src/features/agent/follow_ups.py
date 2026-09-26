"""
Contextual Follow-up Inquiries Generator
========================================
Generates high-probability follow-up inquiries based on the synthesized answer
and cited document headings using LLM completion with deterministic fallback.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_follow_up_inquiries(
    query: str,
    grounded_answer: str,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """
    Generates up to 3 high-probability contextual follow-up inquiries.
    Uses LLM generation when available, falling back to citation heading heuristics.
    """
    follow_ups: List[str] = []
    if grounded_answer and "INSUFFICIENT_EVIDENCE" not in grounded_answer:
        try:
            from src.infrastructure.providers.router import get_provider_router, InferenceTask
            llm_router = get_provider_router()
            fu_prompt = (
                f"User Query: {query}\n"
                f"Synthesized Answer: {grounded_answer[:600]}\n\n"
                f"Generate exactly 3 high-probability contextual follow-up inquiries that an analyst or researcher would naturally ask next.\n"
                f"Rules:\n"
                f"- Each question must be under 80 characters.\n"
                f"- Must be directly grounded in the topics covered in the answer.\n"
                f"- Return JSON list of strings only: [\"...\", \"...\", \"...\"]"
            )
            fu_resp = llm_router.complete(
                prompt=fu_prompt,
                task=InferenceTask.QUERY_DECOMPOSITION,
                max_tokens=200,
                temperature=0.2,
            )
            if fu_resp and "[" in fu_resp and "]" in fu_resp:
                clean_fu = fu_resp[fu_resp.find("["):fu_resp.rfind("]")+1]
                parsed_fu = json.loads(clean_fu)
                if isinstance(parsed_fu, list):
                    follow_ups = [str(q).strip() for q in parsed_fu if str(q).strip()][:3]
        except Exception:
            pass

    # Heuristic fallback if LLM returned fewer than 3 inquiries
    if len(follow_ups) < 3 and citations:
        cand_headings = [c.get("heading") for c in citations if c.get("heading") and not str(c.get("heading", "")).startswith("Section")]
        cand_docs = list(dict.fromkeys([c.get("pdf_filename") for c in citations if c.get("pdf_filename")]))
        
        if cand_headings:
            for h in cand_headings:
                clean_h = re.sub(r"^\d+\s*\|\s*|\s*\|\s*\d+$", "", str(h)).strip()
                if clean_h:
                    follow_ups.append(f"What key metrics and targets are established under {clean_h}?")
                    if len(follow_ups) >= 3:
                        break
        if len(follow_ups) < 3 and cand_docs:
            for d in cand_docs:
                d_title = Path(d).stem.replace("_", " ").title()
                follow_ups.append(f"What additional institutional initiatives are documented in {d_title}?")
                if len(follow_ups) >= 3:
                    break
        if len(follow_ups) < 3:
            follow_ups.append("Can you provide a detailed breakdown of the related financial figures?")
            follow_ups.append("What are the key policy recommendations mentioned for this area?")

    return follow_ups[:3]

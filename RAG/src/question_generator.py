"""
RAISE Dynamic Question Generator
Generates high-groundedness, high-traceability research questions directly
from the entities, metrics, sections, and facts extracted from uploaded PDFs.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class DynamicQuestionGenerator:
    """
    Analyzes active ChromaDB chunks and Neo4j entities to synthesize
    custom research questions tailored to the specific uploaded documents.
    """

    def __init__(self, processed_dir: Optional[Path | str] = None):
        self.processed_dir = Path(processed_dir or Path(__file__).parent.parent / "data" / "processed").resolve()

    def generate_smart_questions(self, max_questions: int = 4) -> List[str]:
        """
        Inspects extracted chunks and triples to generate tailored, grounded research questions.
        """
        chunks_dir = self.processed_dir / "chunks"
        triples_dir = self.processed_dir / "graph_triples"

        if not chunks_dir.exists():
            return []

        chunk_files = list(chunks_dir.glob("*_chunks.json"))
        if not chunk_files:
            return []

        questions: List[str] = []
        universities: List[str] = []
        headings: List[str] = []
        financial_metrics: List[str] = []
        patents_innovations: List[str] = []

        # 1. Parse chunks from active documents
        for cf in chunk_files:
            try:
                data = json.loads(cf.read_text(encoding="utf-8"))
                for c in data[:15]:
                    u = c.get("university")
                    if u and u not in universities:
                        universities.append(u)
                    
                    h = c.get("heading")
                    if h and len(h) > 5 and not h.startswith("Section (Page") and h not in headings:
                        headings.append(h)

                    txt = c.get("plain_text", "")
                    # Detect financial figures
                    fin_match = re.findall(r"(?:Rs\.?|INR|\bLakh\b|\bCrore\b|\bGrant\b|\bEndowment\b)\s*[\d,.]+", txt, re.IGNORECASE)
                    if fin_match:
                        financial_metrics.extend(fin_match[:2])

                    # Detect patents / technologies
                    if re.search(r"\b(patent|startup|incubated|variety|technology|mou)\b", txt, re.IGNORECASE):
                        patents_innovations.append(c.get("heading", "technology initiatives"))
            except Exception:
                continue

        # 2. Generate questions dynamically based on discovered facts
        primary_uni = universities[0] if universities else "the reported institution"

        if financial_metrics:
            questions.append(f"What are the major sponsored research grants and financial expenditures reported by {primary_uni}?")
        
        if len(headings) >= 2:
            questions.append(f"What key developments are detailed under '{headings[0]}' and '{headings[1]}'?")
        elif headings:
            questions.append(f"Summarize the key institutional milestones reported in '{headings[0]}'.")

        if patents_innovations:
            questions.append(f"Which patents, deep-tech incubations, or research initiatives were developed by {primary_uni}?")

        if len(universities) > 1:
            questions.append(f"Compare the strategic focus and academic metrics between {universities[0]} and {universities[1]}.")
        else:
            questions.append(f"What are the academic programs, governance policies, and faculty accomplishments reported for {primary_uni}?")

        return questions[:max_questions]

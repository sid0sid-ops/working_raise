"""
2WikiMultihopQA Dataset Loader
Reads official 2WikiMultihopQA dev format with explicit relational paths and entity linking annotations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .schema import EvalQuestion

logger = logging.getLogger("raise.eval.loader.2wiki")

EVAL_DATASETS_ROOT = Path(__file__).resolve().parents[1] / "datasets" / "2wikimultihopqa"


class TwoWikiMultihopLoader:
    """
    Loads 2WikiMultihopQA relational multi-hop reasoning questions.
    Data is stored in RAG/evaluation/datasets/2wikimultihopqa/ and kept strictly isolated.
    """

    def __init__(self, data_dir: Optional[Path | str] = None):
        self.data_dir = Path(data_dir or EVAL_DATASETS_ROOT).resolve()

    def load_dev_questions(self, limit: Optional[int] = None) -> List[EvalQuestion]:
        target_file = self.data_dir / "dev.json"
        
        questions: List[EvalQuestion] = []
        if target_file.exists():
            logger.info(f"Loading 2WikiMultihopQA from {target_file}")
            raw_data = json.loads(target_file.read_text(encoding="utf-8"))
            for idx, item in enumerate(raw_data):
                if limit and idx >= limit:
                    break
                
                sp_facts = [f"{sp[0]} (Sentence {sp[1]})" for sp in item.get("supporting_facts", [])]
                
                questions.append(EvalQuestion(
                    q_id=f"2WIKI_{item.get('_id', idx)}",
                    benchmark="2WikiMultihopQA",
                    dataset="2wikimultihopqa-dev",
                    tier="Relational Multi-Hop",
                    question=item.get("question", "").strip(),
                    ground_truth_answer=item.get("answer", "").strip(),
                    page_citations=[],
                    required_keywords=[item.get("answer", "").strip()],
                    supporting_facts=sp_facts,
                    hop_count=2,
                    is_unanswerable=False,
                    metadata={
                        "type": item.get("type"),
                        "evidences": item.get("evidences", []),
                        "supporting_facts_raw": item.get("supporting_facts", [])
                    }
                ))
        else:
            logger.warning(f"No dev.json found in {self.data_dir}. Generating representative diagnostic relational questions.")
            sample_data = [
                {
                    "_id": "2wiki_001",
                    "question": "Which film has the director who was born earlier, The Great Gatsby or Citizen Kane?",
                    "answer": "Citizen Kane",
                    "type": "comparison",
                    "supporting_facts": [["The Great Gatsby (2013 film)", 0], ["Baz Luhrmann", 0], ["Citizen Kane", 0], ["Orson Welles", 0]]
                },
                {
                    "_id": "2wiki_002",
                    "question": "What is the place of birth of the director of film Inception?",
                    "answer": "London",
                    "type": "bridge",
                    "supporting_facts": [["Inception", 0], ["Christopher Nolan", 0]]
                },
                {
                    "_id": "2wiki_003",
                    "question": "Are the directors of Jurassic Park and Schindler's List the same person?",
                    "answer": "yes",
                    "type": "comparison",
                    "supporting_facts": [["Jurassic Park (film)", 0], ["Schindler's List", 0], ["Steven Spielberg", 0]]
                }
            ]
            for item in sample_data:
                sp_facts = [f"{sp[0]} (Sentence {sp[1]})" for sp in item["supporting_facts"]]
                questions.append(EvalQuestion(
                    q_id=f"2WIKI_{item['_id']}",
                    benchmark="2WikiMultihopQA",
                    dataset="2wikimultihopqa-dev",
                    tier="Relational Multi-Hop",
                    question=item["question"],
                    ground_truth_answer=item["answer"],
                    page_citations=[],
                    required_keywords=[item["answer"]],
                    supporting_facts=sp_facts,
                    hop_count=2,
                    is_unanswerable=False,
                    metadata={"type": item["type"]}
                ))

        logger.info(f"Loaded {len(questions)} questions from 2WikiMultihopQA loader.")
        return questions

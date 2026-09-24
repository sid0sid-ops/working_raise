"""
MuSiQue Dataset Loader
Reads official MuSiQue dev format (2-hop, 3-hop, 4-hop and unanswerable contrast questions).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .schema import EvalQuestion

logger = logging.getLogger("raise.eval.loader.musique")

EVAL_DATASETS_ROOT = Path(__file__).resolve().parents[1] / "datasets" / "musique"


class MuSiQueLoader:
    """
    Loads MuSiQue questions with disconnected reasoning chains and contrast unanswerable flags.
    Data is stored in RAG/evaluation/datasets/musique/ and kept strictly isolated.
    """

    def __init__(self, data_dir: Optional[Path | str] = None):
        self.data_dir = Path(data_dir or EVAL_DATASETS_ROOT).resolve()

    def load_dev_questions(self, limit: Optional[int] = None) -> List[EvalQuestion]:
        candidates = list(self.data_dir.glob("*.jsonl"))
        
        questions: List[EvalQuestion] = []
        if candidates:
            target_file = candidates[0]
            logger.info(f"Loading MuSiQue from {target_file}")
            with open(target_file, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    if limit and idx >= limit:
                        break
                    item = json.loads(line)
                    decomp = item.get("question_decomposition", [])
                    hop_count = len(decomp) if decomp else 2
                    is_ans = item.get("answerable", True)
                    ans = item.get("answer", "")

                    questions.append(EvalQuestion(
                        q_id=f"MUSIQUE_{item.get('id', idx)}",
                        benchmark="MuSiQue",
                        dataset="musique-dev",
                        tier=f"{hop_count}-Hop Reasoning",
                        question=item.get("question", "").strip(),
                        ground_truth_answer=ans,
                        page_citations=[],
                        required_keywords=[ans] if ans else [],
                        supporting_facts=[d.get("question", "") for d in decomp],
                        hop_count=hop_count,
                        is_unanswerable=not is_ans,
                        metadata={
                            "answerable": is_ans,
                            "question_decomposition": decomp,
                            "paragraphs_count": len(item.get("paragraphs", []))
                        }
                    ))
        else:
            logger.warning(f"No jsonl files found in {self.data_dir}. Generating representative diagnostic MuSiQue questions.")
            sample_data = [
                {
                    "id": "musique_2hop_001",
                    "question": "What country is the birthplace of the spouse of Barack Obama located in?",
                    "answer": "United States",
                    "answerable": True,
                    "hop_count": 2,
                    "decomposition": [
                        {"id": 1, "question": "Who is the spouse of Barack Obama?", "answer": "Michelle Obama"},
                        {"id": 2, "question": "What country is the birthplace of Michelle Obama located in?", "answer": "United States"}
                    ]
                },
                {
                    "id": "musique_3hop_002",
                    "question": "What is the headquarter city of the airline whose subsidiary operates flights to the birthplace of Marie Curie?",
                    "answer": "Warsaw",
                    "answerable": True,
                    "hop_count": 3,
                    "decomposition": [
                        {"id": 1, "question": "What is the birthplace of Marie Curie?", "answer": "Warsaw"},
                        {"id": 2, "question": "Which airline operates flights to Warsaw?", "answer": "LOT Polish Airlines"},
                        {"id": 3, "question": "What is the headquarter city of LOT Polish Airlines?", "answer": "Warsaw"}
                    ]
                },
                {
                    "id": "musique_unans_003",
                    "question": "What was the doctoral dissertation topic of the mother of the founder of Neuralink?",
                    "answer": "",
                    "answerable": False,
                    "hop_count": 3,
                    "decomposition": [
                        {"id": 1, "question": "Who is the founder of Neuralink?", "answer": "Elon Musk"},
                        {"id": 2, "question": "Who is the mother of Elon Musk?", "answer": "Maye Musk"},
                        {"id": 3, "question": "What was the doctoral dissertation topic of Maye Musk?", "answer": "INSUFFICIENT_EVIDENCE"}
                    ]
                }
            ]
            for item in sample_data:
                questions.append(EvalQuestion(
                    q_id=f"MUSIQUE_{item['id']}",
                    benchmark="MuSiQue",
                    dataset="musique-dev",
                    tier=f"{item['hop_count']}-Hop Reasoning",
                    question=item["question"],
                    ground_truth_answer=item["answer"],
                    page_citations=[],
                    required_keywords=[item["answer"]] if item["answer"] else [],
                    supporting_facts=[d["question"] for d in item["decomposition"]],
                    hop_count=item["hop_count"],
                    is_unanswerable=not item["answerable"],
                    metadata={"answerable": item["answerable"], "question_decomposition": item["decomposition"]}
                ))

        logger.info(f"Loaded {len(questions)} questions from MuSiQue loader.")
        return questions

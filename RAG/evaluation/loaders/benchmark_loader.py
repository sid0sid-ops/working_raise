"""
Benchmark Dataset Loader supporting Tier 1 (RAISE Domain & FRAMES 824) and General Multi-Hop Suites
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .schema import EvalQuestion

logger = logging.getLogger("raise.eval.loader")

EVAL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = EVAL_ROOT.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"


class BenchmarkLoader:
    """
    Loads benchmark datasets with strict schema validation and provenance tracking.
    """

    @staticmethod
    def load_raise_domain_benchmark(filepath: Optional[Path | str] = None) -> List[EvalQuestion]:
        """
        Loads the locked 16-question RAISE Domain Benchmark (Exact tables, multi-hop, trends, unanswerable).
        """
        path = Path(filepath or BACKEND_ROOT / "evaluation" / "benchmark_qa.json")
        if not path.exists():
            raise FileNotFoundError(f"RAISE Domain Benchmark file not found at {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        raw_questions = data.get("questions", [])
        
        parsed = []
        for q in raw_questions:
            tier_num = q.get("tier", 1)
            tier_name = f"Tier {tier_num}"
            is_unans = tier_num == 4 or "INSUFFICIENT_EVIDENCE" in str(q.get("ground_truth_answer", ""))
            
            hop_count = 1
            if tier_num == 2 or tier_num == 3:
                hop_count = 2

            parsed.append(EvalQuestion(
                q_id=str(q.get("q_id")),
                benchmark="RAISE-Domain",
                dataset="RAISE-Bench-V1",
                tier=tier_name,
                question=q.get("question", "").strip(),
                ground_truth_answer=q.get("ground_truth_answer", "").strip(),
                target_document=q.get("target_document"),
                page_citations=q.get("page_citations", []),
                required_keywords=q.get("required_keywords", []),
                supporting_facts=q.get("page_citations", []),
                hop_count=hop_count,
                is_unanswerable=is_unans,
                metadata={"raw_tier": tier_num}
            ))

        logger.info(f"Loaded {len(parsed)} questions from RAISE Domain Benchmark.")
        return parsed

    @staticmethod
    def load_frames_benchmark(limit: Optional[int] = None, tsv_path: Optional[Path | str] = None) -> List[EvalQuestion]:
        """
        Loads the official Google Research FRAMES multi-hop evaluation set (824 examples).
        """
        path = Path(tsv_path or BACKEND_ROOT / "evaluation" / "benchmarks" / "frames" / "data" / "frames_test.tsv")
        if not path.exists():
            # Check loader data dir
            alt_path = BACKEND_ROOT / "evaluation" / "benchmarks" / "frames" / "data" / "frames_test.tsv"
            if alt_path.exists():
                path = alt_path
            else:
                raise FileNotFoundError(f"FRAMES test.tsv not found at {path}")

        questions: List[EvalQuestion] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for idx, row in enumerate(reader):
                if limit and idx >= limit:
                    break

                q_id = f"FRAMES_{idx+1:04d}"
                raw_q = row.get("Prompt", row.get("question", "")).strip()
                ans = row.get("Answer", row.get("answer", "")).strip()
                
                # Check reasoning types
                reasoning_types = row.get("reasoning_types", "")
                is_unans = "unanswerable" in reasoning_types.lower() or "insufficient" in ans.lower()
                
                questions.append(EvalQuestion(
                    q_id=q_id,
                    benchmark="FRAMES",
                    dataset="google/frames-benchmark",
                    tier="Multi-Hop Reasoning",
                    question=raw_q,
                    ground_truth_answer=ans,
                    target_document=None,
                    page_citations=[],
                    required_keywords=[],
                    supporting_facts=[],
                    hop_count=2,
                    is_unanswerable=is_unans,
                    metadata={"reasoning_types": reasoning_types}
                ))

        logger.info(f"Loaded {len(questions)} questions from FRAMES benchmark.")
        return questions

    @classmethod
    def load(cls, benchmark_name: str, limit: Optional[int] = None) -> List[EvalQuestion]:
        """Unified benchmark dispatcher."""
        b_clean = benchmark_name.lower().strip()
        if b_clean in ("raise", "raise-domain", "raise_domain", "tier1"):
            return cls.load_raise_domain_benchmark()
        elif b_clean in ("frames", "google_frames", "824"):
            return cls.load_frames_benchmark(limit=limit)
        else:
            raise ValueError(f"Unknown benchmark: '{benchmark_name}'. Supported: 'raise-domain', 'frames'.")

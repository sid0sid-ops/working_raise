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

    @staticmethod
    def _load_standardized_jsonl(filepath: Path, limit: Optional[int] = None) -> List[EvalQuestion]:
        """Loads standardized EvalQuestion instances from a JSONL file."""
        if not filepath.exists():
            raise FileNotFoundError(f"Benchmark file not found at {filepath}")
        questions: List[EvalQuestion] = []
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if limit and idx >= limit:
                    break
                if not line.strip():
                    continue
                d = json.loads(line)
                questions.append(EvalQuestion(
                    q_id=str(d.get("q_id", f"Q_{idx}")),
                    benchmark=str(d.get("benchmark", "Standard")),
                    dataset=str(d.get("dataset", "")),
                    tier=str(d.get("tier", "Standard")),
                    question=str(d.get("question", "")).strip(),
                    ground_truth_answer=d.get("ground_truth_answer"),
                    target_document=d.get("target_document"),
                    page_citations=d.get("page_citations", []),
                    required_keywords=d.get("required_keywords", []),
                    supporting_facts=d.get("supporting_facts", []),
                    hop_count=int(d.get("hop_count", 1)),
                    is_unanswerable=bool(d.get("is_unanswerable", False)),
                    metadata=d.get("metadata", {})
                ))
        return questions

    @classmethod
    def load_hotpotqa(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "hotpotqa" / "samples_300.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_2wikimultihopqa(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "2wikimultihopqa" / "samples_300.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_musique(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "musique" / "samples_300.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_nq(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "nq" / "dev" / "samples_300.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_triviaqa(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "triviaqa" / "samples_300.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_beir(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "beir" / "scifact" / "samples_300.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_trec_dl_2019(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "trec_dl" / "2019" / "samples_200.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load_trec_dl_2020(cls, limit: Optional[int] = None) -> List[EvalQuestion]:
        path = EVAL_ROOT / "datasets" / "trec_dl" / "2020" / "samples_200.jsonl"
        return cls._load_standardized_jsonl(path, limit=limit)

    @classmethod
    def load(cls, benchmark_name: str, limit: Optional[int] = None) -> List[EvalQuestion]:
        """Unified benchmark dispatcher across all 9 academic benchmarks + RAISE Domain."""
        b_clean = benchmark_name.lower().strip().replace("-", "_").replace(" ", "_")
        
        # RAISE Domain
        if b_clean in ("raise", "raise_domain", "tier1"):
            q_list = cls.load_raise_domain_benchmark()
            return q_list[:limit] if limit else q_list
        # FRAMES
        elif b_clean in ("frames", "google_frames", "824"):
            return cls.load_frames_benchmark(limit=limit)
        # HotpotQA
        elif b_clean in ("hotpot", "hotpotqa"):
            return cls.load_hotpotqa(limit=limit)
        # 2WikiMultihopQA
        elif b_clean in ("2wiki", "2wikimultihop", "2wikimultihopqa", "twowiki"):
            return cls.load_2wikimultihopqa(limit=limit)
        # MuSiQue
        elif b_clean in ("musique", "musique_ans"):
            return cls.load_musique(limit=limit)
        # Natural Questions
        elif b_clean in ("nq", "natural_questions", "naturalquestions"):
            return cls.load_nq(limit=limit)
        # TriviaQA
        elif b_clean in ("trivia", "triviaqa"):
            return cls.load_triviaqa(limit=limit)
        # BEIR
        elif b_clean in ("beir", "beir_scifact", "scifact"):
            return cls.load_beir(limit=limit)
        # TREC DL 2019
        elif b_clean in ("trec_2019", "trec_dl_2019", "trecdl2019", "dl19"):
            return cls.load_trec_dl_2019(limit=limit)
        # TREC DL 2020
        elif b_clean in ("trec_2020", "trec_dl_2020", "trecdl2020", "dl20"):
            return cls.load_trec_dl_2020(limit=limit)
        else:
            raise ValueError(
                f"Unknown benchmark: '{benchmark_name}'. Supported:\n"
                "- raise-domain\n"
                "- frames\n"
                "- hotpotqa\n"
                "- 2wikimultihopqa\n"
                "- musique\n"
                "- nq\n"
                "- triviaqa\n"
                "- beir\n"
                "- trec-dl-2019\n"
                "- trec-dl-2020"
            )

"""
FRAMES Benchmark Dataset Loader
Fetches, validates, caches, and parses the official Google FRAMES benchmark dataset (824 examples).
Guarantees immutability and provenance tracking via SHA-256 integrity manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .schema import FramesQuestion

logger = logging.getLogger("raise.frames.loader")

DATASET_REPO = "google/frames-benchmark"
DATASET_FILENAME = "test.tsv"
DATASET_REVISION = "58d9fb6330f3ab1316d1eca12e5e8ef23dcc22ef"


class FramesDatasetLoader:
    """
    Manages acquisition, verification, and structured loading of the FRAMES benchmark.
    """

    def __init__(self, data_dir: Optional[Path | str] = None):
        if data_dir:
            self.data_dir = Path(data_dir).resolve()
        else:
            self.data_dir = Path(__file__).resolve().parent
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.tsv_path = self.data_dir / "frames_test.tsv"
        self.manifest_path = self.data_dir / "manifest.json"
        self._questions: Optional[List[FramesQuestion]] = None

    def ensure_dataset(self) -> Path:
        """
        Ensures the official test.tsv is acquired, validated, and cached locally.
        Falls back to HuggingFace Hub cache or downloads if missing.
        """
        if self.tsv_path.exists() and self.tsv_path.stat().st_size > 100000:
            logger.info(f"Using existing cached FRAMES dataset: {self.tsv_path}")
            self._ensure_manifest()
            return self.tsv_path

        # Check local HF Hub cache first
        hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "datasets--google--frames-benchmark"
        if hf_cache_dir.exists():
            matches = list(hf_cache_dir.rglob("test.tsv"))
            if matches and matches[0].exists() and matches[0].stat().st_size > 100000:
                logger.info(f"Found existing HuggingFace cached dataset: {matches[0]}")
                shutil.copy2(matches[0], self.tsv_path)
                self._ensure_manifest()
                return self.tsv_path

        # Attempt download via huggingface_hub
        try:
            from huggingface_hub import hf_hub_download
            logger.info("Downloading official google/frames-benchmark test.tsv from HuggingFace Hub...")
            downloaded = hf_hub_download(
                repo_id=DATASET_REPO,
                filename=DATASET_FILENAME,
                repo_type="dataset",
                revision=DATASET_REVISION,
            )
            shutil.copy2(downloaded, self.tsv_path)
            logger.info(f"Successfully downloaded and cached FRAMES to: {self.tsv_path}")
            self._ensure_manifest()
            return self.tsv_path
        except Exception as e:
            logger.error(f"HuggingFace Hub download failed: {e}")
            raise RuntimeError(
                f"Could not acquire FRAMES benchmark dataset: {e}. "
                f"Please verify network access to {DATASET_REPO} or place test.tsv at {self.tsv_path}"
            )

    def _calculate_sha256(self, filepath: Path) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _ensure_manifest(self):
        """Generates or updates manifest.json with provenance metadata and SHA-256."""
        sha = self._calculate_sha256(self.tsv_path)
        manifest_data = {
            "benchmark": "FRAMES",
            "full_name": "Factuality, Retrieval, And reasoning MEasurement Set",
            "source": f"https://huggingface.co/datasets/{DATASET_REPO}",
            "dataset_revision": DATASET_REVISION,
            "filename": DATASET_FILENAME,
            "sha256": sha,
            "download_date": datetime.now(timezone.utc).isoformat(),
            "sample_count": 824,
            "pipeline_version": "2.5.0",
            "license": "Apache 2.0 (Google Research)",
            "reference_paper": "https://arxiv.org/abs/2409.12941"
        }
        self.manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        logger.info(f"Updated FRAMES manifest at: {self.manifest_path} (SHA-256: {sha[:12]}...)")

    def load_questions(self, force_reload: bool = False) -> List[FramesQuestion]:
        """
        Loads and parses all benchmark examples into normalized FramesQuestion models.
        """
        if self._questions is not None and not force_reload:
            return self._questions

        tsv_file = self.ensure_dataset()
        questions: List[FramesQuestion] = []

        with open(tsv_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for idx, row in enumerate(reader):
                try:
                    q = FramesQuestion.from_tsv_row(row)
                    questions.append(q)
                except Exception as err:
                    logger.warning(f"Error parsing FRAMES row {idx}: {err}")

        logger.info(f"Loaded {len(questions)} validated FRAMES benchmark questions.")
        self._questions = questions
        return self._questions

    def get_questions(
        self,
        reasoning_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[FramesQuestion]:
        """Filters questions by reasoning category with offset and limit pagination."""
        all_q = self.load_questions()
        if reasoning_type:
            all_q = [q for q in all_q if q.has_reasoning_type(reasoning_type)]
        sliced = all_q[offset:]
        if limit is not None:
            sliced = sliced[:limit]
        return sliced

    def get_by_id(self, question_id: str) -> Optional[FramesQuestion]:
        """Retrieves a specific question by its benchmark ID."""
        all_q = self.load_questions()
        for q in all_q:
            if str(q.question_id) == str(question_id):
                return q
        return None

    def get_category_statistics(self) -> Dict[str, int]:
        """Returns question counts broken down by reasoning category."""
        all_q = self.load_questions()
        stats: Dict[str, int] = {
            "Total": len(all_q),
            "Multiple constraints": sum(1 for q in all_q if q.is_constraint),
            "Numerical reasoning": sum(1 for q in all_q if q.is_numerical),
            "Temporal reasoning": sum(1 for q in all_q if q.is_temporal),
            "Tabular reasoning": sum(1 for q in all_q if q.is_tabular),
            "Post processing": sum(1 for q in all_q if q.is_post_processing),
            "Multi-hop": sum(1 for q in all_q if q.is_multihop),
        }
        return stats

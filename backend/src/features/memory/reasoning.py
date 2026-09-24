"""
RAISE Reasoning Memory Store (Inspired by Google ReasoningBank 2026)
Records verified retrieval trajectories, entity alias resolutions, and verification failure patterns.
Guides future query planning without overriding ground-truth source evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ReasoningTrajectory:
    trajectory_id: str
    query_pattern: str
    successful_tools: List[str]
    resolved_entities: Dict[str, str]
    key_metrics: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    verification_passed: bool = True
    notes: str = ""

    @property
    def metrics(self) -> List[str]:
        """Backward-compatible alias for key_metrics."""
        return self.key_metrics

    @metrics.setter
    def metrics(self, value: List[str]):
        self.key_metrics = value

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["metrics"] = self.key_metrics
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReasoningTrajectory":
        metrics = data.get("metrics") or data.get("key_metrics") or []
        return cls(
            trajectory_id=data.get("trajectory_id", "traj_0001"),
            query_pattern=data.get("query_pattern", data.get("query", "")),
            successful_tools=data.get("successful_tools", data.get("tools_used", [])),
            resolved_entities=data.get("resolved_entities", {}),
            key_metrics=metrics,
            confidence_score=data.get("confidence_score", data.get("confidence", 0.0)),
            verification_passed=data.get("verification_passed", data.get("passed", True)),
            notes=data.get("notes", ""),
        )


class ReasoningMemory:
    """
    In-memory and file-persisted store for agent reasoning patterns.
    """

    def __init__(self, storage_path: Optional[Path | str] = None):
        if storage_path:
            self.storage_path = Path(storage_path).resolve()
        else:
            self.storage_path = (Path(__file__).resolve().parent.parent / ".runtime" / "reasoning_memory.json").resolve()
        self.trajectories: List[ReasoningTrajectory] = []
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.trajectories = [ReasoningTrajectory.from_dict(t) if isinstance(t, dict) else t for t in data]
            except Exception:
                self.trajectories = []


    def record_trajectory(
        self,
        query: str,
        tools_used: List[str],
        resolved_entities: Dict[str, str],
        metrics: List[str],
        confidence: float,
        passed: bool,
        notes: str = "",
    ) -> ReasoningTrajectory:
        """
        Save a completed reasoning trajectory to memory.
        """
        traj_id = f"traj_{len(self.trajectories)+1:04d}"
        traj = ReasoningTrajectory(
            trajectory_id=traj_id,
            query_pattern=query,
            successful_tools=tools_used,
            resolved_entities=resolved_entities,
            key_metrics=metrics,
            confidence_score=confidence,
            verification_passed=passed,
            notes=notes,
        )
        self.trajectories.append(traj)
        self._save()
        return traj

    def find_similar_strategy(self, query: str) -> Optional[ReasoningTrajectory]:
        """
        Lookup past verified trajectory with meaningful semantic overlap,
        excluding conversational stop words and trivial pronouns.
        """
        stop_words = {"what", "is", "my", "the", "a", "an", "and", "or", "tell", "me", "who", "am", "i", "are", "you", "user", "using", "now", "to", "for", "in", "of", "on", "about"}
        q_words = set(w.lower() for w in re.findall(r"\b[a-zA-Z0-9_]{3,}\b", query) if w.lower() not in stop_words)
        
        if not q_words:
            return None

        best_match = None
        best_score = 0

        for t in reversed(self.trajectories):
            # Only recall trajectories that passed verification and have positive confidence
            if not t.verification_passed or t.confidence_score <= 0.0:
                continue
            # Never recall trajectories that recorded out-of-scope refusals
            if "outside this scope" in t.notes.lower() or "refusal" in t.notes.lower():
                continue

            t_words = set(w.lower() for w in re.findall(r"\b[a-zA-Z0-9_]{3,}\b", t.query_pattern) if w.lower() not in stop_words)
            if not t_words:
                continue
                
            intersection = len(q_words.intersection(t_words))
            if intersection >= 2 and intersection > best_score:
                best_score = intersection
                best_match = t

        return best_match

    def clear(self):
        """Clears all stored trajectories in memory and on disk."""
        self.trajectories = []
        if self.storage_path.exists():
            try:
                self.storage_path.unlink()
            except Exception:
                try:
                    self.storage_path.write_text("[]", encoding="utf-8")
                except Exception:
                    pass

    def remove_document_trajectories(self, doc_id_or_name: str) -> int:
        """Removes trajectories that referenced a specific document or filename."""
        clean_target = doc_id_or_name.lower()
        initial_len = len(self.trajectories)
        self.trajectories = [
            t for t in self.trajectories
            if clean_target not in t.query_pattern.lower() and clean_target not in t.notes.lower()
        ]
        self._save()
        return initial_len - len(self.trajectories)

    def _save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(
                json.dumps([t.to_dict() for t in self.trajectories], indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

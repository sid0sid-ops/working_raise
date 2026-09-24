"""
RAISE Memory Architecture: Stateful Sessions (Short-Term Memory)
and Graph-Backed Knowledge Base Evolution (Long-Term Memory).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConversationTurn:
    turn_id: int
    user_query: str
    resolved_query: str
    active_entities: List[str]
    citations: List[Dict[str, Any]]
    assistant_answer: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SessionMemoryManager:
    """
    Short-Term Memory: Manages thread-scoped state checkpoints and resolves
    pronouns (e.g., 'they', 'their', 'its', 'that project') using conversational context.
    """

    PRONOUN_PATTERNS = [
        r"\btheir\b", r"\bthey\b", r"\bits\b", r"\bit\b",
        r"\bthat institution\b", r"\bthis university\b", r"\bthat person\b",
        r"\bthat grant\b", r"\bthat department\b", r"\bthat lab\b"
    ]

    def __init__(self):
        self._threads: Dict[str, List[ConversationTurn]] = {}
        self._user_personas: Dict[str, Dict[str, str]] = {}

    def extract_user_name(self, text: str) -> Optional[str]:
        """
        Extract user's name from introductory phrases like 'my name is Rohan', 'call me Rohan', 'I am Rohan'.
        """
        m1 = re.search(r"(?i)\b(?:my\s+name\s+is|call\s+me)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text)
        if m1:
            cand = m1.group(1).strip()
            words = cand.split()
            filtered = []
            for w in words:
                if w.lower() in ("what", "whats", "what's", "and", "how", "who", "please", "yours", "tell"):
                    break
                filtered.append(w)
            if filtered:
                res = " ".join(filtered)
                if res.lower() not in ("a", "an", "the", "someone", "nobody"):
                    return res.title()

        m2 = re.search(r"(?i)\b(?:i\s+am|i'm)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text)
        if m2:
            cand = m2.group(1).strip()
            words = cand.split()
            filtered = []
            for w in words:
                if w.lower() in ("what", "whats", "what's", "and", "how", "who", "please", "yours", "tell", "a", "an", "the", "student", "researcher", "engineer", "scientist", "professor", "doctor", "busy", "working", "looking", "trying"):
                    break
                filtered.append(w)
            if filtered:
                res = " ".join(filtered)
                if res.lower() not in ("a", "an", "the", "someone", "nobody", "here", "ready", "new"):
                    return res.title()
        return None

    def extract_and_set_user_persona(self, thread_id: str, message: str) -> Optional[str]:
        name = self.extract_user_name(message)
        if name:
            self._user_personas.setdefault(thread_id, {})["user_name"] = name
        return name

    def get_user_persona(self, thread_id: str) -> Dict[str, str]:
        return self._user_personas.get(thread_id, {})

    def clear_thread(self, thread_id: str):
        self._threads.pop(thread_id, None)
        self._user_personas.pop(thread_id, None)

    def get_thread_history(self, thread_id: str) -> List[ConversationTurn]:
        return self._threads.get(thread_id, [])

    def record_turn(
        self,
        thread_id: str,
        user_query: str,
        resolved_query: str,
        active_entities: List[str],
        citations: List[Dict[str, Any]],
        assistant_answer: str,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            turn_id=len(self._threads.get(thread_id, [])) + 1,
            user_query=user_query,
            resolved_query=resolved_query,
            active_entities=active_entities,
            citations=citations,
            assistant_answer=assistant_answer,
        )
        self._threads.setdefault(thread_id, []).append(turn)
        return turn

    def resolve_coreference(self, query: str, thread_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Inspects checkpointed state to resolve pronoun references to earlier entities.
        Returns: (resolved_query, resolved_entity_name)
        """
        if not thread_id or thread_id not in self._threads or not self._threads[thread_id]:
            return query, None

        history = self._threads[thread_id]
        last_turn = history[-1]
        dominant_entity = last_turn.active_entities[0] if last_turn.active_entities else None

        if not dominant_entity:
            return query, None

        has_pronoun = any(re.search(pat, query, re.IGNORECASE) for pat in self.PRONOUN_PATTERNS)
        if not has_pronoun:
            return query, None

        # Disambiguate pronouns
        resolved = query
        resolved = re.sub(r"\btheir\b", f"{dominant_entity}'s", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\bthey\b", dominant_entity, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\bits\b", f"{dominant_entity}'s", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\bit\b", dominant_entity, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\bthat institution\b", dominant_entity, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\bthis university\b", dominant_entity, resolved, flags=re.IGNORECASE)

        return resolved, dominant_entity


@dataclass
class StagedTriple:
    stage_id: str
    source_entity: str
    source_type: str
    relationship: str
    target_entity: str
    target_type: str
    properties: Dict[str, Any]
    provenance: Dict[str, Any]
    verified: bool = False
    confidence: float = 0.0


class LongTermGraphEvolutionManager:
    """
    Long-Term Memory: Executes the 3-step Graph-Backed Knowledge Base Evolution:
      1. Information Extraction
      2. Verification Staging
      3. Graph Reconciliation (Idempotent parameterized MERGE updates)
    """

    def __init__(self, neo4j_db: Optional[Any] = None):
        self.neo4j_db = neo4j_db
        self.staging_buffer: List[StagedTriple] = []

    def stage_extracted_triples(
        self,
        extracted_data: List[Dict[str, Any]],
        confidence_threshold: float = 0.75,
    ) -> List[StagedTriple]:
        """
        Stage 1 & 2: Information Extraction & Verification Staging.
        Quarantines triples and checks threshold before reconciliation.
        """
        staged = []
        for idx, item in enumerate(extracted_data):
            conf = float(item.get("confidence", 0.85))
            is_valid = conf >= confidence_threshold
            t = StagedTriple(
                stage_id=f"staged_{len(self.staging_buffer) + idx + 1:04d}",
                source_entity=item.get("source", ""),
                source_type=item.get("source_type", "Entity"),
                relationship=item.get("relationship", "RELATED_TO"),
                target_entity=item.get("target", ""),
                target_type=item.get("target_type", "Entity"),
                properties=item.get("properties", {}),
                provenance=item.get("provenance", {}),
                verified=is_valid,
                confidence=conf,
            )
            staged.append(t)
            self.staging_buffer.append(t)
        return staged

    def reconcile_into_graph(self) -> Dict[str, Any]:
        """
        Stage 3: Graph Reconciliation.
        Applies verified staged triples into permanent Knowledge Graph.
        """
        verified_items = [t for t in self.staging_buffer if t.verified]
        if not verified_items:
            return {"reconciled_count": 0, "status": "no_verified_triples"}

        reconciled_nodes = 0
        reconciled_edges = 0

        if self.neo4j_db and getattr(self.neo4j_db, "connected", False):
            # Parameterized Cypher batch update
            node_payload = []
            edge_payload = []
            for item in verified_items:
                node_payload.append({
                    "id": item.source_entity,
                    "name": item.source_entity,
                    "type": item.source_type,
                    "doc_id": item.provenance.get("document_id", "global"),
                })
                node_payload.append({
                    "id": item.target_entity,
                    "name": item.target_entity,
                    "type": item.target_type,
                    "doc_id": item.provenance.get("document_id", "global"),
                })
                edge_payload.append({
                    "source": item.source_entity,
                    "target": item.target_entity,
                    "rel_type": item.relationship,
                    "doc_id": item.provenance.get("document_id", "global"),
                })

            cypher_node = """
            UNWIND $batch AS item
            MERGE (n:Entity {id: item.id})
            ON CREATE SET n.name = item.name, n.type = item.type, n.document_id = item.doc_id, n.created_at = timestamp()
            ON MATCH SET n.name = coalesce(item.name, n.name), n.type = coalesce(item.type, n.type), n.updated_at = timestamp()
            """
            self.neo4j_db.run_cypher(cypher_node, {"batch": node_payload})

            # Execute edge Cypher
            cypher_edge = """
            UNWIND $batch AS edge
            MATCH (src {id: edge.source})
            MATCH (tgt {id: edge.target})
            MERGE (src)-[r:EVOLVED_RELATION {type: edge.rel_type}]->(tgt)
            ON CREATE SET r.document_id = edge.doc_id, r.created_at = timestamp()
            """
            self.neo4j_db.run_cypher(cypher_edge, {"batch": edge_payload})

            reconciled_nodes = len(node_payload)
            reconciled_edges = len(edge_payload)
        else:
            reconciled_nodes = len(verified_items) * 2
            reconciled_edges = len(verified_items)

        # Clear reconciled buffer
        self.staging_buffer = [t for t in self.staging_buffer if not t.verified]

        return {
            "status": "reconciled_successfully",
            "reconciled_nodes": reconciled_nodes,
            "reconciled_edges": reconciled_edges,
            "remaining_unverified_in_staging": len(self.staging_buffer),
        }

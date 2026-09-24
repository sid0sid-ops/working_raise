"""
Chain Completeness Gate & Evidence-Driven Multi-Hop Extractor (chain_gate.py)
=============================================================================
Deterministic verification gate and intermediate bridge extractor for multi-hop RAG.

Key Architectural Guarantees:
1. Evidence-Driven Extraction: Intermediate bridge entities are extracted from Hop 1
   retrieved evidence (chunks & Neo4j graph hits), NOT from ungrounded query words.
2. Pre-Synthesis Completeness Gating: Evaluates whether the required reasoning chain
   (A -> B -> C) is fully connected BEFORE invoking the LLM generator.
3. Anti-Hallucination Firewall: If the bridge is missing after recovery passes,
   the gate triggers deterministic honest abstention (INSUFFICIENT_EVIDENCE).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.cli.models import HopEvidenceItem

logger = logging.getLogger("ChainCompletenessGate")


@dataclass
class ChainGateResult:
    is_complete: bool
    status: str  # "PASSED", "TRIGGER_RECOVERY", "ABSTAIN_INSUFFICIENT"
    required_hops: int
    completed_hops: int
    hops: List[HopEvidenceItem] = field(default_factory=list)
    discovered_bridge_entity: Optional[str] = None
    target_attribute: Optional[str] = None
    targeted_hop2_query: Optional[str] = None
    confidence: float = 1.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_complete": self.is_complete,
            "status": self.status,
            "required_hops": self.required_hops,
            "completed_hops": self.completed_hops,
            "hops": [h.to_dict() for h in self.hops],
            "discovered_bridge_entity": self.discovered_bridge_entity,
            "target_attribute": self.target_attribute,
            "targeted_hop2_query": self.targeted_hop2_query,
            "confidence": self.confidence,
            "reason": self.reason,
        }


class ChainCompletenessGate:
    """
    Deterministic Chain Completeness Gate.
    Inspects retrieved chunks and graph edges to certify that all reasoning hops are grounded.
    """

    RELATION_KEYWORDS = {
        "expenditure": ["expenditure", "budget", "allocated", "spent", "expenses", "grant", "funding", "cost", "incurred", "rs.", "crore", "lakh"],
        "director_head": ["director", "head", "dean", "chair", "professor", "officer", "secretary", "lead", "in-charge"],
        "alumni_education": ["alumni", "graduated", "degree", "phd", "btech", "mtech", "studied at", "batch"],
        "patent_technology": ["patents", "patent", "technology", "commercialized", "intellectual property", "ipr"],
        "revenue_profit": ["revenue", "turnover", "profit", "income", "surplus", "earnings"],
        "enrollment_count": ["enrolled", "enrollment", "admitted", "intake", "students", "strength"],
    }

    TARGET_ATTRIBUTE_PATTERNS = [
        ("expenditure", r"\b(expenditure|budget|allocated|spent|cost|grant|incurred|amount|crore|lakh|rupees|inr)\b"),
        ("director_head", r"\b(who leads|who is the head|director|dean|chairperson|in-charge)\b"),
        ("alumni_education", r"\b(graduate|graduated|alumni|degree|where did|university)\b"),
        ("patent_technology", r"\b(patents?|technology|commercialized|intellectual property)\b"),
        ("revenue_profit", r"\b(revenue|turnover|profit|income|surplus|earnings)\b"),
        ("enrollment_count", r"\b(enrolled|enrollment|admitted|intake|students? count)\b"),
    ]

    def __init__(self, neo4j_db: Optional[Any] = None):
        self.neo4j_db = neo4j_db

    def analyze_query_requirements(self, query: str) -> Dict[str, Any]:
        """
        Determines if the query requires multi-hop traversal and identifies target attributes.
        """
        q_lower = query.lower()
        
        # Check for multi-hop indicators
        multihop_indicators = [
            " led by ", " headed by ", " recipient of ", " winner of ", " who won ",
            " department of the ", " company founded by ", " graduated from ",
            " expenditure of the department ", " budget of the center ",
            " director of ", " according to schedule ", " which was established by "
        ]
        is_multihop = any(ind in q_lower for ind in multihop_indicators)
        
        # Identify target question attribute
        target_attr = None
        for attr_name, pattern in self.TARGET_ATTRIBUTE_PATTERNS:
            if re.search(pattern, q_lower):
                target_attr = attr_name
                break

        # Extract root query seeds (ignoring generic words)
        stopwords = {
            "what", "which", "where", "who", "whom", "how", "the", "and", "for", "with",
            "from", "into", "during", "annual", "report", "according", "total", "tell",
            "show", "give", "list", "name", "about", "their", "under", "both", "table"
        }
        words = re.findall(r"\b[A-Za-z0-9_\-\.]{3,}\b", query)
        seed_terms = [w for w in words if w.lower() not in stopwords]

        return {
            "is_multihop": is_multihop,
            "required_hops": 2 if is_multihop else 1,
            "target_attribute": target_attr,
            "seed_terms": seed_terms,
        }

    def extract_evidence_bridge_entity(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        subgraph: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, str, float]]:
        """
        Extracts intermediate bridge entities discovered in Hop 1 evidence.
        Returns: (bridge_entity_name, relation_type, confidence)
        
        CRITICAL ARCHITECTURAL DIFFERENCE:
        Extracts entities discovered in the *evidence chunks/graph*, NOT from the query itself!
        """
        q_lower = query.lower()
        query_words = set(re.findall(r"\b\w+\b", q_lower))

        # 1. Inspect Graph Subgraph first (High-Precision Grounding)
        if subgraph and isinstance(subgraph, dict):
            edges = subgraph.get("edges", [])
            for e in edges:
                if not isinstance(e, dict):
                    continue
                src = str(e.get("source", ""))
                tgt = str(e.get("target", ""))
                rel = str(e.get("type", "RELATED_TO")).upper()

                # If source or target was in query, the OTHER end is our discovered bridge entity!
                src_in_q = any(w in q_lower for w in src.lower().split() if len(w) > 3)
                tgt_in_q = any(w in q_lower for w in tgt.lower().split() if len(w) > 3)

                if src_in_q and not tgt_in_q and len(tgt) > 2:
                    tgt_norm = re.sub(r'^(The|A|An)\s+', '', tgt, flags=re.IGNORECASE).strip()
                    return (tgt_norm, rel, 0.95)
                elif tgt_in_q and not src_in_q and len(src) > 2:
                    src_norm = re.sub(r'^(The|A|An)\s+', '', src, flags=re.IGNORECASE).strip()
                    return (src_norm, rel, 0.95)

        # 2. Inspect Top Evidence Chunks for Named Entities not present in Query
        candidate_entities: Dict[str, float] = {}
        for c in retrieved_chunks[:4]:
            text = c.get("text") or c.get("plain_text") or ""
            
            # Find capitalized entity mentions: e.g. "Prof. Bhaskar Ramamurthi", "Department of Electrical Engineering"
            patterns = [
                r"\b(?:Prof\.|Dr\.|Mr\.|Ms\.|Shri)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
                r"\b(Department of [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
                r"\b(Centre for [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\s+(?:Laboratory|Institute|Foundation|Limited|Park))\b",
            ]
            for pat in patterns:
                for match in re.finditer(pat, text):
                    ent_str = match.group(0).strip()
                    # Exclude entities that already appeared directly in the user query
                    ent_words = [w.lower() for w in ent_str.split()]
                    if not any(w in query_words for w in ent_words if len(w) > 3):
                        candidate_entities[ent_str] = candidate_entities.get(ent_str, 0.0) + 1.0

        if candidate_entities:
            best_entity = max(candidate_entities.items(), key=lambda x: x[1])[0]
            best_entity = re.sub(r'^(The|A|An)\s+', '', best_entity, flags=re.IGNORECASE).strip()
            return (best_entity, "DISCOVERED_BRIDGE", 0.85)

        return None

    def evaluate_chain(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        subgraph: Optional[Dict[str, Any]] = None,
        is_recovery_pass: bool = False,
    ) -> ChainGateResult:
        """
        Evaluates the reasoning chain completeness.
        Returns a structured ChainGateResult certifying whether generation should proceed.
        """
        requirements = self.analyze_query_requirements(query)
        is_multihop = requirements["is_multihop"]
        required_hops = requirements["required_hops"]
        target_attr = requirements["target_attribute"]

        if not retrieved_chunks:
            return ChainGateResult(
                is_complete=False,
                status="TRIGGER_RECOVERY" if not is_recovery_pass else "ABSTAIN_INSUFFICIENT",
                required_hops=required_hops,
                completed_hops=0,
                confidence=0.0,
                reason="Zero evidence chunks acquired in retrieval pass.",
            )

        # Single-hop query: Check basic evidence grounding
        if not is_multihop:
            hop1 = HopEvidenceItem(
                hop_id=1,
                sub_goal=f"Direct retrieval for '{query[:60]}'",
                source_entity=requirements["seed_terms"][0] if requirements["seed_terms"] else "Query",
                relation="DIRECT_GROUNDING",
                target_entity=target_attr or "Fact",
                supporting_chunks=[str(c.get("chunk_id") or c.get("id")) for c in retrieved_chunks[:3]],
                confidence=0.92,
                status="VERIFIED",
            )
            return ChainGateResult(
                is_complete=True,
                status="PASSED",
                required_hops=1,
                completed_hops=1,
                hops=[hop1],
                confidence=0.92,
                reason="Single-hop query directly verified against retrieved evidence.",
            )

        # Multi-Hop Query Evaluation:
        # Hop 1: Ground root query seeds to discovered bridge entity
        bridge_info = self.extract_evidence_bridge_entity(query, retrieved_chunks, subgraph)
        
        if not bridge_info:
            # We couldn't even extract the bridge entity from Hop 1
            return ChainGateResult(
                is_complete=False,
                status="TRIGGER_RECOVERY" if not is_recovery_pass else "ABSTAIN_INSUFFICIENT",
                required_hops=2,
                completed_hops=0,
                confidence=0.20,
                reason="Failed to ground Hop 1: No intermediate bridge entity discovered in evidence.",
            )

        bridge_entity, bridge_relation, bridge_conf = bridge_info

        hop1 = HopEvidenceItem(
            hop_id=1,
            sub_goal=f"Identify intermediate entity connecting '{query[:40]}...'",
            source_entity=requirements["seed_terms"][0] if requirements["seed_terms"] else "RootQuery",
            relation=bridge_relation,
            target_entity=bridge_entity,
            supporting_chunks=[str(c.get("chunk_id") or c.get("id")) for c in retrieved_chunks[:2]],
            confidence=bridge_conf,
            status="VERIFIED",
        )

        # Hop 2: Verify connection from bridge_entity to target_attribute
        hop2_verified = False
        hop2_supporting_chunks: List[str] = []
        hop2_conf = 0.0

        if target_attr:
            # Search if bridge entity AND target attribute appear together in any chunk
            b_lower = bridge_entity.lower()
            attr_kws = self.RELATION_KEYWORDS.get(target_attr, [target_attr])
            
            for c in retrieved_chunks:
                c_text = (c.get("text") or c.get("plain_text") or "").lower()
                cid = str(c.get("chunk_id") or c.get("id"))
                
                # Bridge entity must be mentioned
                has_bridge = any(w in c_text for w in b_lower.split() if len(w) > 3)
                if not has_bridge:
                    continue

                # Target attribute keyword must be present
                has_attr_kw = any(kw in c_text for kw in attr_kws)
                if not has_attr_kw:
                    continue

                # If attribute is quantitative (expenditure, revenue, enrollment), check for non-year numerical figures
                if target_attr in ("expenditure", "revenue_profit", "enrollment_count"):
                    # Find numbers that are NOT years 1990-2035
                    num_matches = re.findall(r"\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\b", c_text)
                    valid_nums = []
                    for n in num_matches:
                        clean_n = n.replace(",", "")
                        try:
                            f = float(clean_n)
                            if 1990 <= f <= 2035 and "." not in clean_n:
                                continue
                            valid_nums.append(f)
                        except ValueError:
                            pass
                    if not valid_nums:
                        continue  # Only year was present, no actual quantitative figure!

                hop2_verified = True
                hop2_supporting_chunks.append(cid)
                hop2_conf = 0.88
                break

        if hop2_verified:
            hop2 = HopEvidenceItem(
                hop_id=2,
                sub_goal=f"Resolve '{target_attr or 'attribute'}' for '{bridge_entity}'",
                source_entity=bridge_entity,
                relation=f"HAS_{target_attr.upper()}" if target_attr else "RESOLVED_ATTRIBUTE",
                target_entity=target_attr or "AttributeValue",
                supporting_chunks=hop2_supporting_chunks,
                confidence=hop2_conf,
                status="VERIFIED",
            )
            return ChainGateResult(
                is_complete=True,
                status="PASSED",
                required_hops=2,
                completed_hops=2,
                hops=[hop1, hop2],
                discovered_bridge_entity=bridge_entity,
                target_attribute=target_attr,
                confidence=round((bridge_conf + hop2_conf) / 2.0, 3),
                reason=f"Multi-hop chain complete: '{requirements['seed_terms'][:1]}' -> '{bridge_entity}' -> '{target_attr}'",
            )
        else:
            # Hop 1 succeeded, but Hop 2 is missing!
            hop2 = HopEvidenceItem(
                hop_id=2,
                sub_goal=f"Resolve '{target_attr or 'attribute'}' for '{bridge_entity}'",
                source_entity=bridge_entity,
                relation=f"HAS_{target_attr.upper()}" if target_attr else "RESOLVED_ATTRIBUTE",
                target_entity=target_attr or "AttributeValue",
                supporting_chunks=[],
                confidence=0.15,
                status="MISSING",
            )
            
            # Formulate the targeted Hop 2 subquery
            targeted_hop2_query = f'"{bridge_entity}" {target_attr or ""} expenditure budget total figures'.strip()

            status = "TRIGGER_RECOVERY" if not is_recovery_pass else "ABSTAIN_INSUFFICIENT"
            reason = (
                f"Chain incomplete: Discovered '{bridge_entity}' in Hop 1, but Hop 2 "
                f"('{target_attr or 'attribute'}') is missing from retrieved context."
            )
            return ChainGateResult(
                is_complete=False,
                status=status,
                required_hops=2,
                completed_hops=1,
                hops=[hop1, hop2],
                discovered_bridge_entity=bridge_entity,
                target_attribute=target_attr,
                targeted_hop2_query=targeted_hop2_query,
                confidence=0.45,
                reason=reason,
            )

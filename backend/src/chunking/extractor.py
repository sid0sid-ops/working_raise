"""
Entity and Relationship Extractor for Candidate Information Units (Stage 4 & Stage 5 of GGAHC).
Extracts entities (organizations, people, projects, technologies, startups, locations, metrics, dates)
and relationships connecting entities within candidate units to support Graph-Guided boundary optimization.
Reuses and extends the project's AcademicDomainExtractor and FactEngine.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import CandidateUnit


class CandidateKnowledgeExtractor:
    """
    Extracts entities and relational facts from candidate units.
    Populates candidate.entities and candidate.relationships for temporary graph construction.
    """

    def __init__(
        self,
        academic_extractor: Optional[Any] = None,
        fact_engine: Optional[Any] = None,
    ):
        if academic_extractor is None:
            from src.features.ingestion.academic_extractor import AcademicDomainExtractor
            self.academic_extractor = AcademicDomainExtractor()
        else:
            self.academic_extractor = academic_extractor

        if fact_engine is None:
            from src.features.verification.fact_engine import FactEngine
            self.fact_engine = FactEngine()
        else:
            self.fact_engine = fact_engine
        self.extractor = self.academic_extractor

    def extract_candidate_knowledge(
        self,
        candidate: CandidateUnit,
        institution_name: str = "Institution",
    ) -> CandidateUnit:
        """
        Extracts entities and relationships for a single candidate unit.
        Preserves complete provenance to the candidate unit.
        """
        text = candidate.plain_text
        cid = candidate.candidate_id
        doc_id = candidate.document_id
        pno = candidate.page_start
        heading = candidate.heading

        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        # 1. Academic & Enterprise Entities from AcademicDomainExtractor
        ents, rels = self.extractor.extract_academic_knowledge(
            text=text,
            pdf_filename=f"{doc_id}.pdf",
            page_number=pno,
            section_heading=heading,
            chunk_id=cid,
            university_name=institution_name,
        )
        for e in ents:
            entities.append({
                "id": e.entity_id,
                "name": e.name,
                "label": e.label,
                "properties": e.properties,
            })
        for r in rels:
            relationships.append({
                "relation_id": r.relation_id,
                "source_id": r.source_id,
                "relation_type": r.relation_type,
                "target_id": r.target_id,
                "source_label": r.source_label,
                "target_label": r.target_label,
            })

        # 2. Extract numeric facts via FactEngine
        try:
            num_facts = self.fact_engine.extract_facts_from_text(
                text=text,
                document_id=doc_id,
                university=institution_name,
                page_number=pno,
                section_id=candidate.section_id,
            )
            for nf in num_facts:
                fid = nf.fact_id
                fname = f"{nf.metric_name.replace('_', ' ').title()}: {nf.raw_value}"
                entities.append({
                    "id": fid,
                    "name": fname,
                    "label": "MetricFact",
                    "properties": nf.to_dict(),
                })
                relationships.append({
                    "relation_id": f"rel_{cid}_{fid}_fact",
                    "source_id": cid,
                    "relation_type": "HAS_FACT",
                    "target_id": fid,
                    "source_label": "CandidateUnit",
                    "target_label": "MetricFact",
                })
        except Exception:
            pass

        # 3. Dedicated startup / organization mentions heuristic if text describes deep-tech / products
        startup_matches = re.findall(
            r"\b(XYMA Analytics|Mindgrove Technologies|NeoMotion|AgniKul Cosmos|Agnikul|NeoFly|NeoBolt|TMAP)\b",
            text,
            re.IGNORECASE
        )
        for sm in set(startup_matches):
            canon_name = sm.title()
            eid = f"startup_{re.sub(r'[^a-zA-Z0-9]', '_', canon_name.lower())}"
            if not any(e["id"] == eid for e in entities):
                entities.append({
                    "id": eid,
                    "name": canon_name,
                    "label": "Startup",
                    "properties": {"name": canon_name},
                })

        # Deduplicate entities by ID
        unique_ents = {}
        for e in entities:
            unique_ents[e["id"]] = e
        candidate.entities = list(unique_ents.values())

        # Deduplicate relations by ID
        unique_rels = {}
        for r in relationships:
            unique_rels[r["relation_id"]] = r
        candidate.relationships = list(unique_rels.values())

        return candidate

    def extract_batch(
        self,
        candidates: List[CandidateUnit],
        institution_name: str = "Institution",
    ) -> List[CandidateUnit]:
        """Process a list of candidate units sequentially or in batches."""
        return [self.extract_candidate_knowledge(c, institution_name) for c in candidates]

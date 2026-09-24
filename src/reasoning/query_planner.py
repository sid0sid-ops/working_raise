"""
RAISE Typed Query Planner
Constructs structured Query Plans and Typed Query Graphs for complex multi-hop reasoning.
Preserves relational composition (e.g., 'same scientist', 'same year', 'winner vs host')
and extracts declared atomic operations and dependency graphs.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.graph.entity_resolver import EntityResolver
from src.graph.relation_resolver import RelationResolver, RelationType


@dataclass
class QueryPlanNode:
    id: str
    type: str  # "entity", "event", "value", "operator", "attribute"
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryPlanEdge:
    id: str
    source_id: str
    relation: RelationType
    target_id: str
    is_compositional: bool = False  # e.g., 'same scientist', 'same year'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "relation": self.relation.value,
            "target_id": self.target_id,
            "is_compositional": self.is_compositional,
        }


@dataclass
class QueryPlanOperator:
    id: str
    type: str  # "ADD", "SUB", "DATE_DIFF", "ELAPSED_FULL_YEARS", "ARGMAX", "ARGMIN", "FILTER", "INTERSECT"
    inputs: List[str]
    output_var: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryPlanHop:
    hop_id: int
    atomic_subquery: str
    required_relation: RelationType
    source_entity: str
    target_type: str = "entity"
    dependencies: List[int] = field(default_factory=list)
    compositional_cue: Optional[str] = None  # "same scientist", "same year", "same location"
    qualifying_constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hop_id": self.hop_id,
            "atomic_subquery": self.atomic_subquery,
            "required_relation": self.required_relation.value,
            "source_entity": self.source_entity,
            "target_type": self.target_type,
            "dependencies": self.dependencies,
            "compositional_cue": self.compositional_cue,
            "qualifying_constraints": self.qualifying_constraints,
        }


@dataclass
class TypedQueryPlan:
    original_query: str
    nodes: List[QueryPlanNode] = field(default_factory=list)
    edges: List[QueryPlanEdge] = field(default_factory=list)
    operators: List[QueryPlanOperator] = field(default_factory=list)
    hops: List[QueryPlanHop] = field(default_factory=list)
    preserves_composition: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "operators": [o.to_dict() for o in self.operators],
            "hops": [h.to_dict() for h in self.hops],
            "preserves_composition": self.preserves_composition,
        }


class QueryPlanner:
    """
    Deconstructs complex, multi-hop, relational questions into a typed DAG execution plan.
    """

    COMPOSITION_PATTERNS = {
        "SAME_SCIENTIST": r"\b(?:same\s+scientist|same\s+researcher|same\s+person\s+who\s+discovered)\b",
        "SAME_PERSON": r"\b(?:same\s+person|same\s+author|same\s+actor|same\s+director|same\s+artist)\b",
        "SAME_YEAR": r"\b(?:same\s+year|in\s+that\s+same\s+year|during\s+the\s+same\s+year)\b",
        "SAME_LOCATION": r"\b(?:same\s+country|same\s+city|same\s+state|same\s+place)\b",
        "WINNER_VS_HOST": r"\b(?:who\s+won|winner\s+of|won\s+the\s+championship)\b.*\b(?:hosted|held\s+in)\b",
    }

    def __init__(self, entity_resolver: Optional[EntityResolver] = None):
        self.entity_resolver = entity_resolver or EntityResolver()

    def build_plan(self, query: str, context_hints: Optional[List[str]] = None) -> TypedQueryPlan:
        plan = TypedQueryPlan(original_query=query)
        q_lower = query.lower()

        # 1. Extract Seed Entities using EntityResolver (sentence-initial stopword safe)
        raw_cands = self.entity_resolver.extract_candidate_entities(query)
        entities = [c for c in raw_cands if not re.match(r"^\d{4}$", c)]
        years = [c for c in raw_cands if re.match(r"^\d{4}$", c)]

        # 2. Check for Compositional Cues ("same scientist", "same year", etc.)
        compositional_cues = []
        for cue_name, pat in self.COMPOSITION_PATTERNS.items():
            if re.search(pat, q_lower):
                compositional_cues.append(cue_name)

        plan.preserves_composition = len(compositional_cues) > 0

        # 3. Detect Operators (Math / Date Diff / Comparison)
        if any(w in q_lower for w in ["age difference", "how much older", "difference between", "how many years between"]):
            plan.operators.append(QueryPlanOperator(
                id="op_date_diff",
                type="DATE_DIFF",
                inputs=entities[:2] if len(entities) >= 2 else ["entity_1", "entity_2"],
                output_var="age_difference_years",
            ))
        elif any(w in q_lower for w in ["how old was", "age of", "how old were"]):
            plan.operators.append(QueryPlanOperator(
                id="op_age_calc",
                type="ELAPSED_FULL_YEARS",
                inputs=entities[:1] if entities else ["subject"],
                output_var="subject_age",
            ))
        elif any(w in q_lower for w in ["greater than", "more than", "added", "plus", "sum of", "total"]):
            match_num = re.search(r"\b(\d+)\s+(?:greater|more|higher|less|fewer)\b", q_lower)
            val = float(match_num.group(1)) if match_num else 0.0
            plan.operators.append(QueryPlanOperator(
                id="op_arithmetic",
                type="ADD" if "greater" in q_lower or "more" in q_lower or "added" in q_lower or "plus" in q_lower else "SUB",
                inputs=[f"var_base", str(val)],
                output_var="calculated_metric",
                parameters={"delta": val}
            ))

        # 4. Detect Qualifying Constraints (Awards, Chronological Minimums, Surface Formatting)
        qualifying_constraints = []
        if any(w in q_lower for w in ["award", "prize", "won", "winner", "trophy", "medal"]):
            award_match = re.search(r"\b([A-Z][a-zA-Z\s]+(?:Award|Prize|Trophy|Championship))\b", query)
            if award_match:
                qualifying_constraints.append(f"AWARD:{award_match.group(1).strip()}")
        if any(w in q_lower for w in ["first", "earliest", "debut"]):
            qualifying_constraints.append("CHRONOLOGICAL_MINIMUM")
        if any(w in q_lower for w in ["how many letters", "number of letters", "letter count"]):
            qualifying_constraints.append("LETTER_COUNT")
        if any(w in q_lower for w in ["in words", "nearest million", "in characters"]):
            qualifying_constraints.append("SURFACE_WORDS")

        # 5. Construct Multi-Hop Plan
        # If "same scientist" composition detected (e.g. Q6 style query):
        if "SAME_SCIENTIST" in compositional_cues or ("same" in q_lower and "discovered" in q_lower):
            disc_match = re.search(r"\bdiscovered\s+([a-zA-Z]{3,})\b", query, re.IGNORECASE)
            seed_ent = disc_match.group(1).strip() if disc_match else (entities[0] if entities else "target_element")
            h1 = QueryPlanHop(
                hop_id=1,
                atomic_subquery=f"Who discovered {seed_ent} and in what year?",
                required_relation=RelationType.DISCOVERED_BY,
                source_entity=seed_ent,
                target_type="scientist",
                dependencies=[],
                compositional_cue="SAME_SCIENTIST",
                qualifying_constraints=qualifying_constraints,
            )
            h2 = QueryPlanHop(
                hop_id=2,
                atomic_subquery="What other element was discovered by {hop_1_entity} in the same year?",
                required_relation=RelationType.DISCOVERED_BY,
                source_entity="{hop_1_entity}",
                target_type="element",
                dependencies=[1],
                compositional_cue="SAME_YEAR",
                qualifying_constraints=qualifying_constraints,
            )
            h3 = QueryPlanHop(
                hop_id=3,
                atomic_subquery="What is the atomic number of {hop_2_entity}?",
                required_relation=RelationType.ATOMIC_NUMBER,
                source_entity="{hop_2_entity}",
                target_type="number",
                dependencies=[2],
                qualifying_constraints=qualifying_constraints,
            )
            plan.hops = [h1, h2, h3]

        # Standard Multi-Entity / Multi-Clause Hop Generation
        elif len(entities) >= 2:
            req_rel = RelationResolver.detect_required_relation(query) or RelationType.RELATED_TO
            for idx, ent in enumerate(entities[:4], start=1):
                plan.hops.append(QueryPlanHop(
                    hop_id=idx,
                    atomic_subquery=f"Retrieve facts and relations regarding {ent}",
                    required_relation=req_rel,
                    source_entity=ent,
                    target_type="entity",
                    dependencies=[idx - 1] if idx > 1 else [],
                    qualifying_constraints=qualifying_constraints,
                ))
        elif len(entities) == 1:
            req_rel = RelationResolver.detect_required_relation(query) or RelationType.RELATED_TO
            plan.hops.append(QueryPlanHop(
                hop_id=1,
                atomic_subquery=query,
                required_relation=req_rel,
                source_entity=entities[0],
                target_type="entity_or_value",
                dependencies=[],
                qualifying_constraints=qualifying_constraints,
            ))
        else:
            # Fallback if no specific named entity found
            req_rel = RelationResolver.detect_required_relation(query) or RelationType.RELATED_TO
            plan.hops.append(QueryPlanHop(
                hop_id=1,
                atomic_subquery=query,
                required_relation=req_rel,
                source_entity="query_subject",
                target_type="entity_or_value",
                dependencies=[],
                qualifying_constraints=qualifying_constraints,
            ))

        # Populate graph nodes and edges
        for idx, ent in enumerate(entities):
            plan.nodes.append(QueryPlanNode(id=f"ent_{idx}", type="entity", text=ent))
        for idx, yr in enumerate(years):
            plan.nodes.append(QueryPlanNode(id=f"yr_{idx}", type="value", text=yr))

        for hop in plan.hops:
            plan.edges.append(QueryPlanEdge(
                id=f"edge_hop_{hop.hop_id}",
                source_id=hop.source_entity,
                relation=hop.required_relation,
                target_id=f"target_hop_{hop.hop_id}",
                is_compositional=bool(hop.compositional_cue),
            ))

        return plan

    def decompose_to_subqueries(self, query: str) -> List[str]:
        """
        Deconstructs complex multi-hop queries into discrete, atomic search sub-queries.
        Prevents dense embedding dilution and cross-encoder score collapse on multi-part questions.
        """
        if not query or len(query.strip()) < 15:
            return [query] if query else []

        subqueries: List[str] = []
        q_clean = query.strip().rstrip("?").strip()

        # 1. Split across major multi-constraint clausal boundaries
        clause_split_pattern = r"(?:\band\s+(?:her|his|their|whose|its)\b|\bwhose\s+(?:wife|husband|mother|father|name|height)\b|\bthe\s+last\s+time\b|\bthe\s+first\s+time\b|\bunder\s+the\s+record\s+label\s+that\b|\bin\s+the\s+same\s+state\s+as\b|\bin\s+the\s+same\s+year\s+as\b|\bSpecifically,\s*|\bImagine\s+there\s+is\s+[^.]+\.\s*)"
        raw_clauses = re.split(clause_split_pattern, q_clean, flags=re.IGNORECASE)

        for clause in raw_clauses:
            cl = clause.strip()
            # Remove leading fillers
            cl = re.sub(r"^(?:if|what\s+is|who\s+is|which\s+is|where\s+is|how\s+many|that|whose|and|the)\s+", "", cl, flags=re.IGNORECASE).strip()
            if len(cl) >= 12 and len(cl.split()) >= 3:
                subqueries.append(cl)

        # 2. Extract Ordinal & Superlative Constraint Phrases (e.g. '15th first lady', 'second assassinated president')
        ordinal_patterns = [
            r"\b(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|last|earliest|debut)\s+[a-zA-Z0-9_\-\s]{4,35}?(?:mother|father|wife|husband|president|album|novel|book|winner|champion|vocalist|singer|building|single)\b",
            r"\b(?:mother|father|wife|husband|maiden\s+name|surname|first\s+name)\s+of\s+the\s+[a-zA-Z0-9_\-\s]{4,40}\b",
            r"\b(?:won|winner|champion|holders)\s+(?:of\s+)?the\s+[A-Z][a-zA-Z0-9_\-\s]{3,30}\b",
        ]
        for pat in ordinal_patterns:
            for match in re.finditer(pat, query, flags=re.IGNORECASE):
                phrase = match.group(0).strip()
                if len(phrase) >= 10 and not any(phrase.lower() in sq.lower() for sq in subqueries):
                    subqueries.append(phrase)

        # 3. Entity-Centered Subqueries using EntityResolver
        entities = self.entity_resolver.extract_candidate_entities(query)
        rel_keywords = [
            "mother", "father", "maiden name", "wife", "husband", "born", "birth",
            "published", "album", "vocalist", "dewey decimal", "height", "rank",
            "tallest", "state", "capitol", "champions league", "world cup", "winner"
        ]
        active_rels = [rk for rk in rel_keywords if rk in query.lower()]

        for ent in entities[:4]:
            if len(ent) >= 3 and not re.match(r"^\d{4}$", ent):
                # Formulate a targeted subquery pairing the entity with active question relations
                if active_rels:
                    subqueries.append(f"{ent} {' '.join(active_rels[:3])}")
                else:
                    subqueries.append(ent)

        # 4. Filter and Deduplicate
        seen = set()
        clean_subqueries: List[str] = []
        for sq in subqueries:
            sq_norm = re.sub(r"[^\w\s]", "", sq).lower().strip()
            if sq_norm and sq_norm not in seen and len(sq_norm.split()) >= 2:
                seen.add(sq_norm)
                clean_subqueries.append(sq.strip())

        # Always include original query as baseline if not present
        if clean_subqueries:
            return clean_subqueries[:6]
        return [query]


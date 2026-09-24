"""
RAISE Relation Resolver
Enforces strict typed relation vocabulary and semantic compatibility contracts.
Prevents semantic relation collisions (e.g. World Cup HOSTED_BY vs WINNER/CHAMPION).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class RelationType(str, Enum):
    # Tournament / Sports / Event
    HOSTED_BY = "HOSTED_BY"
    HELD_IN = "HELD_IN"
    WINNER = "WINNER"
    CHAMPION = "CHAMPION"
    RUNNER_UP = "RUNNER_UP"
    PLAYED_FOR = "PLAYED_FOR"
    MANAGED_BY = "MANAGED_BY"
    ASSISTS = "ASSISTS"
    RANK = "RANK"

    # Biography / Persons
    BORN_IN = "BORN_IN"
    DIED_IN = "DIED_IN"
    FOUNDED_BY = "FOUNDED_BY"
    NAMED_AFTER = "NAMED_AFTER"
    MEMBER_OF = "MEMBER_OF"
    CHILD_OF = "CHILD_OF"
    SPOUSE_OF = "SPOUSE_OF"

    # Science / Discovery
    DISCOVERED_BY = "DISCOVERED_BY"
    ATOMIC_NUMBER = "ATOMIC_NUMBER"
    INVENTED_BY = "INVENTED_BY"

    # Corporate / Institutions
    PARENT_COMPANY = "PARENT_COMPANY"
    CURRENT_RECORD_LABEL = "CURRENT_RECORD_LABEL"
    LOCATED_IN = "LOCATED_IN"
    CAPITAL_OF = "CAPITAL_OF"

    # Temporal & Relational Composition
    FIRST = "FIRST"
    LAST = "LAST"
    PREVIOUS = "PREVIOUS"
    NEXT = "NEXT"
    DURING = "DURING"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    SAME_YEAR = "SAME_YEAR"
    SAME_PERSON = "SAME_PERSON"
    SAME_LOCATION = "SAME_LOCATION"

    # General fallback (never accepted as semantic multi-hop proof on its own)
    RELATED_TO = "RELATED_TO"
    MENTIONS = "MENTIONS"


# Explicit pairs of incompatible relations that must NEVER satisfy each other
INCOMPATIBLE_RELATION_PAIRS: Set[Tuple[RelationType, RelationType]] = {
    (RelationType.HOSTED_BY, RelationType.WINNER),
    (RelationType.HOSTED_BY, RelationType.CHAMPION),
    (RelationType.HELD_IN, RelationType.WINNER),
    (RelationType.HELD_IN, RelationType.CHAMPION),
    (RelationType.WINNER, RelationType.RUNNER_UP),
    (RelationType.FIRST, RelationType.LAST),
    (RelationType.PREVIOUS, RelationType.NEXT),
    (RelationType.BEFORE, RelationType.AFTER),
    (RelationType.BORN_IN, RelationType.DIED_IN),
}


class RelationResolver:
    """
    Validates, extracts, and checks compatibility of semantic relations.
    """

    RELATION_INDICATOR_PATTERNS = {
        RelationType.HOSTED_BY: [r"\bhosted by\b", r"\bhost country\b", r"\bhost city\b", r"\bhost nation\b", r"\btook place in\b"],
        RelationType.HELD_IN: [r"\bheld in\b", r"\bstaged in\b", r"\blocated in\b"],
        RelationType.WINNER: [r"\bwon\b", r"\bwinner\b", r"\bvictorious\b", r"\bdefeated .* in the final\b", r"\bchampions?\b", r"\btitle\b"],
        RelationType.CHAMPION: [r"\bchampions?\b", r"\bchampion\b", r"\bwon the championship\b"],
        RelationType.RUNNER_UP: [r"\brunner-up\b", r"\blost in the final\b", r"\bsecond place\b"],
        RelationType.BORN_IN: [r"\bborn in\b", r"\bbirthplace\b", r"\bnative of\b"],
        RelationType.DIED_IN: [r"\bdied in\b", r"\bdeathplace\b", r"\bpassed away in\b"],
        RelationType.FOUNDED_BY: [r"\bfounded by\b", r"\bestablished by\b", r"\bcreator\b", r"\boriginated by\b"],
        RelationType.NAMED_AFTER: [r"\bnamed after\b", r"\bnamed in honour of\b", r"\bnamed in honor of\b", r"\beponym\b"],
        RelationType.DISCOVERED_BY: [r"\bdiscovered by\b", r"\bdiscovery by\b", r"\bfirst isolated by\b", r"\bidentified by\b"],
        RelationType.PLAYED_FOR: [r"\bplayed for\b", r"\bjoined\b", r"\bsigned with\b", r"\bmember of the .* team\b"],
        RelationType.PARENT_COMPANY: [r"\bparent company\b", r"\bsubsidiary of\b", r"\bowned by\b", r"\bacquired by\b"],
        RelationType.CURRENT_RECORD_LABEL: [r"\brecord label\b", r"\bsigned to\b", r"\breleased on\b", r"\blabel\b"],
    }

    @classmethod
    def are_compatible(cls, req_rel: RelationType, cand_rel: RelationType) -> bool:
        """
        Returns False if candidate relation is strictly incompatible with required relation.
        """
        if req_rel == cand_rel:
            return True
        if (req_rel, cand_rel) in INCOMPATIBLE_RELATION_PAIRS or (cand_rel, req_rel) in INCOMPATIBLE_RELATION_PAIRS:
            return False
        # Generic MENTIONS or RELATED_TO cannot satisfy specific typed relation
        if cand_rel in (RelationType.MENTIONS, RelationType.RELATED_TO) and req_rel not in (RelationType.MENTIONS, RelationType.RELATED_TO):
            return False
        # WINNER and CHAMPION are mutually compatible
        if req_rel in (RelationType.WINNER, RelationType.CHAMPION) and cand_rel in (RelationType.WINNER, RelationType.CHAMPION):
            return True
        # HOSTED_BY and HELD_IN are compatible
        if req_rel in (RelationType.HOSTED_BY, RelationType.HELD_IN) and cand_rel in (RelationType.HOSTED_BY, RelationType.HELD_IN):
            return True
        return False

    @classmethod
    def detect_relation_from_text(cls, text: str) -> RelationType:
        """
        Infers the dominant relation type asserted in an evidence passage.
        """
        text_lower = text.lower()
        for rel_type, patterns in cls.RELATION_INDICATOR_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text_lower):
                    return rel_type
        return RelationType.RELATED_TO

    @classmethod
    def detect_required_relation(cls, query: str) -> Optional[RelationType]:
        """
        Infers what relation type the query is asking about.
        """
        q_lower = query.lower()

        # Check winner vs host
        if any(w in q_lower for w in ["who won", "which team won", "winner of", "champion"]):
            return RelationType.WINNER
        if any(w in q_lower for w in ["who hosted", "where was", "host country", "host nation", "held in"]):
            return RelationType.HOSTED_BY
        if any(w in q_lower for w in ["who discovered", "discovered by", "scientist who discovered"]):
            return RelationType.DISCOVERED_BY
        if any(w in q_lower for w in ["named after", "named for"]):
            return RelationType.NAMED_AFTER
        if any(w in q_lower for w in ["who founded", "founded by"]):
            return RelationType.FOUNDED_BY
        if any(w in q_lower for w in ["born in", "birthplace", "where was .* born"]):
            return RelationType.BORN_IN
        if any(w in q_lower for w in ["who did .* play for", "played for", "career team"]):
            return RelationType.PLAYED_FOR
        if any(w in q_lower for w in ["parent company", "who owns"]):
            return RelationType.PARENT_COMPANY

        return None

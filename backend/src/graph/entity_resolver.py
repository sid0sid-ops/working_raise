"""
RAISE Entity Resolver
Provides strict entity identity, normalization, and disambiguation rules.
Features:
  - Exact normalized title matching
  - Alias and redirect mapping
  - Parenthetical disambiguation (e.g., 'Target House (London)' vs 'Target House')
  - Unicode NFKD diacritic folding & case-folding
  - Sentence-position awareness (sentence-initial auxiliaries/verbs like 'Did', 'Who', 'What' are never part of entity names)
  - Token-aware stopword-bounded phrase extraction
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple


class EntityResolver:
    """
    Dedicated entity resolution and normalization engine.
    """

    SENTENCE_INITIAL_STOPWORDS = {
        "did", "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
        "is", "are", "was", "were", "do", "does", "have", "has", "had", "can", "could",
        "would", "should", "if", "in", "on", "at", "during", "after", "before", "from",
        "according", "name", "tell", "give", "list", "the", "a", "an",
        "find", "identify", "locate", "determine", "calculate", "compute", "show", "search", "state"
    }

    GENERAL_STOPWORDS = {
        "the", "a", "an", "of", "and", "in", "on", "at", "to", "for", "with",
        "by", "about", "against", "between", "into", "through", "during", "before",
        "after", "above", "below", "from", "up", "down", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why", "how",
        "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
        "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can"
    }

    def __init__(self, aliases: Optional[Dict[str, str]] = None, redirects: Optional[Dict[str, str]] = None):
        self.aliases: Dict[str, str] = {self.normalize_entity(k): v for k, v in (aliases or {}).items()}
        self.redirects: Dict[str, str] = {self.normalize_entity(k): v for k, v in (redirects or {}).items()}

    @staticmethod
    def normalize_entity(text: str) -> str:
        """
        Applies NFKD diacritic folding, lowercase conversion, and punctuation normalization.
        """
        if not text:
            return ""
        # 1. Unicode NFKD diacritic stripping
        nfkd = unicodedata.normalize("NFKD", text)
        no_diacritics = "".join(c for c in nfkd if not unicodedata.combining(c))
        # 2. Clean replacement characters
        cleaned = no_diacritics.replace("\ufffd", "").strip()
        # 3. Strip parenthetical qualifiers for comparison (e.g. "Target House (London)" -> "Target House")
        cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)
        # 4. Remove punctuation and lowercase
        cleaned = re.sub(r"[^\w\s-]", "", cleaned).lower()
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def strip_parenthetical(entity: str) -> Tuple[str, Optional[str]]:
        """
        Splits 'Target House (London)' into ('Target House', 'London').
        """
        m = re.match(r"^(.*?)\s*\((.*?)\)$", entity.strip())
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return entity.strip(), None

    def extract_candidate_entities(self, query: str) -> List[str]:
        """
        Extracts high-confidence entity candidates from a natural language query.
        Guarantees that sentence-initial auxiliary verbs ('Did', 'What', 'Which', 'Who')
        are NOT merged into entity names.
        """
        candidates: List[str] = []
        q_stripped = query.strip()

        # 1. Quoted explicit phrases (highest precision)
        quoted = re.findall(r'"([^"]+)"', q_stripped)
        for qp in quoted:
            if len(qp.strip()) >= 2 and qp.strip() not in candidates:
                candidates.append(qp.strip())

        # 2. Sentence-initial boundary cleaning:
        # If query starts with e.g. "Did Krampus defeat...", do NOT capture "Did Krampus".
        # Remove sentence-initial auxiliary/interrogative token for multi-word entity scanning.
        words = q_stripped.split()
        lead_word_stripped = False
        body_text = q_stripped
        if words:
            first_word = words[0].strip(".,;:\"'!?()[]{}")
            if first_word.lower() in self.SENTENCE_INITIAL_STOPWORDS:
                body_text = " ".join(words[1:])
                lead_word_stripped = True

        # 3. Multi-word capitalized phrases from body text
        multi_entities = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+(?:\s+[A-Z][a-zA-Z0-9_-]+)+\b', body_text)
        for me in multi_entities:
            me_clean = me.strip()
            # Double check: leading token must not be a stopword
            tokens = me_clean.split()
            if tokens and tokens[0].lower() in self.SENTENCE_INITIAL_STOPWORDS:
                me_clean = " ".join(tokens[1:])
            if len(me_clean) >= 3 and me_clean not in candidates:
                candidates.append(me_clean)

        # 4. Single capitalized proper nouns (>= 3 characters, not in general or lead stopwords)
        single_caps = re.findall(r'\b[A-Z][a-zA-Z0-9_-]{2,}\b', body_text)
        for sc in single_caps:
            sc_clean = sc.strip()
            if sc_clean.lower() not in self.SENTENCE_INITIAL_STOPWORDS and sc_clean.lower() not in self.GENERAL_STOPWORDS:
                if sc_clean not in candidates and not any(sc_clean.lower() == c.lower() for c in candidates):
                    candidates.append(sc_clean)

        # 5. Explicit 4-digit years (18xx, 19xx, 20xx)
        years = re.findall(r'\b(?:15|16|17|18|19|20)\d{2}\b', q_stripped)
        for yr in years:
            if yr not in candidates:
                candidates.append(yr)

        return candidates

    def resolve(
        self,
        candidate: str,
        known_entities: Set[str],
        threshold: float = 0.85,
    ) -> Optional[Tuple[str, float]]:
        """
        Resolves a raw candidate entity string against a set of known knowledge graph/corpus entities.
        Returns (resolved_entity, match_confidence) or None.
        """
        if not candidate:
            return None

        cand_norm = self.normalize_entity(candidate)
        if not cand_norm:
            return None

        # 1. Check alias / redirect map
        if cand_norm in self.aliases:
            target = self.aliases[cand_norm]
            if target in known_entities:
                return target, 1.0
        if cand_norm in self.redirects:
            target = self.redirects[cand_norm]
            if target in known_entities:
                return target, 1.0

        # 2. Exact match on normalized text
        norm_map = {self.normalize_entity(k): k for k in known_entities}
        if cand_norm in norm_map:
            return norm_map[cand_norm], 1.0

        # 3. Base name match without parenthetical qualifier
        base_cand, _ = self.strip_parenthetical(candidate)
        base_cand_norm = self.normalize_entity(base_cand)
        if base_cand_norm and base_cand_norm in norm_map:
            return norm_map[base_cand_norm], 0.95

        for norm_k, orig_k in norm_map.items():
            base_k, _ = self.strip_parenthetical(orig_k)
            if self.normalize_entity(base_k) == cand_norm:
                return orig_k, 0.95

        # 4. Token-level Jaccard overlap on substantive tokens
        cand_tokens = set(cand_norm.split()) - self.GENERAL_STOPWORDS
        if not cand_tokens:
            return None

        best_entity = None
        best_score = 0.0

        for norm_k, orig_k in norm_map.items():
            k_tokens = set(norm_k.split()) - self.GENERAL_STOPWORDS
            if not k_tokens:
                continue

            intersection = cand_tokens.intersection(k_tokens)
            union = cand_tokens.union(k_tokens)
            jaccard = len(intersection) / len(union) if union else 0.0

            # Substring exact containment boost
            if cand_norm in norm_k or norm_k in cand_norm:
                containment = min(len(cand_norm), len(norm_k)) / max(len(cand_norm), len(norm_k))
                score = max(jaccard, containment * 0.9)
            else:
                score = jaccard

            if score > best_score and score >= threshold:
                best_score = score
                best_entity = orig_k

        if best_entity:
            return best_entity, round(best_score, 4)

        # 5. Corrupted diacritic / character gap resolution (e.g., 'l huihui' vs 'lu huihui')
        cand_skeleton = re.sub(r"[aeiou\s]", "", cand_norm)
        if len(cand_skeleton) >= 3:
            for norm_k, orig_k in norm_map.items():
                k_skeleton = re.sub(r"[aeiou\s]", "", norm_k)
                if cand_skeleton == k_skeleton:
                    return orig_k, 0.90

        return None

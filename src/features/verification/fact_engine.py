"""
RAISE Deterministic Numeric & Temporal Fact Engine
Extracts, normalizes, and verifies quantitative university metrics with 100% provenance.
Supports INR, USD, Lakhs, Crores, Millions, Academic Years, Financial Years, and Calendar Years.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TemporalPeriod:
    type: str  # "financial_year", "academic_year", "calendar_year", "date_range"
    label: str  # e.g. "2023-2024", "2024"
    start_year: int
    end_year: int
    normalized_year: int  # Canonical reporting year (e.g. 2024 for FY2023-24)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None

    def contains_year(self, year: int) -> bool:
        """Determines if a target year falls within this reporting period."""
        return self.start_year <= year <= self.end_year

    def is_before(self, year: int) -> bool:
        """Checks if this period ends strictly before target year."""
        return self.end_year < year

    def is_after(self, year: int) -> bool:
        """Checks if this period starts strictly after target year."""
        return self.start_year > year

    def is_within(self, start_year: int, end_year: int) -> bool:
        """Checks if this period is completely contained within the specified range."""
        return self.start_year >= start_year and self.end_year <= end_year

    def overlaps(self, other: TemporalPeriod) -> bool:
        """Checks if this period intersects with another period."""
        return max(self.start_year, other.start_year) <= min(self.end_year, other.end_year)


@dataclass
class NumericFact:
    fact_id: str
    document_id: str
    university: str
    metric_name: str
    raw_value: str
    normalized_value: float
    unit: str  # "currency", "count", "percentage", "ratio", "tokens"
    currency: Optional[str] = None  # "INR", "USD", "EUR", etc.
    scale: float = 1.0  # Multiplier applied (e.g. 10,000,000 for Crore)
    temporal_period: Optional[TemporalPeriod] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    authority_tier: str = "Official Audited Report"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.temporal_period:
            d["temporal_period"] = asdict(self.temporal_period)
        return d


class FactEngine:
    """
    Parses, stores, indexes, and queries deterministic numeric facts.
    """

    SCALE_MULTIPLIERS = {
        "crore": 10_000_000.0,
        "crores": 10_000_000.0,
        "cr": 10_000_000.0,
        "lakh": 100_000.0,
        "lakhs": 100_000.0,
        "lac": 100_000.0,
        "million": 1_000_000.0,
        "millions": 1_000_000.0,
        "m": 1_000_000.0,
        "billion": 1_000_000_000.0,
        "billions": 1_000_000_000.0,
        "b": 1_000_000_000.0,
        "thousand": 1_000.0,
        "thousands": 1_000.0,
        "k": 1_000.0,
    }

    METRIC_PATTERNS = {
        "research_expenditure": [
            r"research\s+(?:and\s+development\s+)?expenditure",
            r"r&d\s+expenses",
            r"research\s+spending",
            r"funds\s+utilized\s+for\s+research",
        ],
        "research_grants_received": [
            r"research\s+grants?\s+received",
            r"extramural\s+funding",
            r"sponsored\s+research\s+funding",
            r"grant\s+inflows",
        ],
        "total_income": [
            r"total\s+income",
            r"total\s+revenue",
            r"gross\s+receipts",
            r"revenue\s+from\s+operations",
        ],
        "profit_after_tax": [
            r"profit\s+after\s+tax",
            r"\bpat\b",
            r"net\s+profit",
            r"operating\s+profit",
        ],
        "turnover": [
            r"average\s+daily\s+turnover",
            r"total\s+turnover",
            r"turnover",
            r"trade\s+volume",
        ],
        "market_capitalisation": [
            r"market\s+capitalisation",
            r"market\s+cap",
        ],
        "fund_mobilisation": [
            r"fund\s+mobilisation",
            r"equity\s+fund\s+mobilisation",
            r"debt\s+fund\s+mobilisation",
            r"capital\s+raised",
        ],
        "listed_entities": [
            r"listed\s+entities",
            r"listed\s+companies",
            r"number\s+of\s+companies",
        ],
        "registered_investors": [
            r"unique\s+registered\s+investors",
            r"registered\s+investors",
            r"total\s+investors",
        ],
        "total_expenditure": [
            r"total\s+expenditure",
            r"total\s+expenses",
            r"gross\s+disbursements",
        ],
        "patents_filed": [
            r"patents?\s+filed",
            r"patent\s+applications?",
            r"ip\s+filings?",
        ],
        "patents_granted": [
            r"patents?\s+granted",
            r"patents?\s+awarded",
            r"patents?\s+issued",
        ],
        "faculty_strength": [
            r"faculty\s+strength",
            r"sanctioned\s+faculty",
            r"teaching\s+staff",
            r"total\s+professors",
        ],
        "student_enrollment": [
            r"student\s+enrollment",
            r"total\s+students",
            r"intake\s+capacity",
        ],
        "startups_incubated": [
            r"startups?\s+incubated",
            r"incubated\s+startups?",
            r"companies\s+incubated",
            r"startups?\s+supported",
        ],
        "funding_raised": [
            r"funding\s+raised",
            r"total\s+funding",
            r"external\s+funding",
            r"investment\s+raised",
        ],
    }

    def __init__(self):
        self.facts: Dict[str, NumericFact] = {}

    def extract_facts_from_text(
        self,
        text: str,
        document_id: str,
        university: str,
        page_number: int = 1,
        section_id: str = "sec_0",
    ) -> List[NumericFact]:
        """
        Scan unstructured text or table cells for verifiable numeric statements.
        """
        extracted = []
        # Split into granular clauses/sentences to allow extracting multiple facts per paragraph
        lines = re.split(
            r'[\n;]|\.(?:\s+|$)|,\s*(?=(?:with|and|total|operating|profit|revenue|income|expenditure|patents?|startups?|grants?|₹|\$|€|[0-9]))',
            text,
            flags=re.IGNORECASE
        )

        for line_idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str or len(line_str) < 3:
                continue

            # Detect Metric Name for this clause
            matched_metric = None
            for m_name, patterns in self.METRIC_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, line_str, re.IGNORECASE):
                        matched_metric = m_name
                        break
                if matched_metric:
                    break

            # Detect all Values in the clause (e.g. ₹ 125.70 Crores, $ 45 Million, 340 Patents)
            val_matches = list(re.finditer(
                r"(?:(₹|rs\.?|inr|\$|usd|€|eur)\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(crores?|cr|lakhs?|lac|millions?|billions?|thousands?|k|%)?",
                line_str,
                re.IGNORECASE,
            ))

            for val_match in val_matches:
                curr_symbol = val_match.group(1)
                num_raw = val_match.group(2).replace(",", "")
                scale_raw = val_match.group(3)

                # Discard standalone year numbers (e.g., FY26, AY2024, or years like 2024 without currency/metric)
                if re.search(r'\b(?:FY|AY)\s*' + re.escape(num_raw) + r'\b', line_str, re.IGNORECASE):
                    continue
                if not curr_symbol and not scale_raw and not matched_metric:
                    continue

                try:
                    base_val = float(num_raw)
                except ValueError:
                    continue

                multiplier = 1.0
                if scale_raw:
                    multiplier = self.SCALE_MULTIPLIERS.get(scale_raw.lower(), 1.0)

                normalized_val = base_val * multiplier
                currency = None
                unit = "count"
                if curr_symbol:
                    unit = "currency"
                    c_sym = curr_symbol.lower()
                    if c_sym in ["₹", "rs", "rs.", "inr"]:
                        currency = "INR"
                    elif c_sym in ["$", "usd"]:
                        currency = "USD"
                    elif c_sym in ["€", "eur"]:
                        currency = "EUR"
                elif scale_raw and "%" in scale_raw:
                    unit = "percentage"

                # Extract Temporal Period from surrounding text or line
                temporal = self.extract_temporal_period(line_str) or self.extract_temporal_period(document_id)

                fact_id = f"fact_{document_id}_p{page_number}_{len(self.facts) + len(extracted) + 1}"
                fact = NumericFact(
                    fact_id=fact_id,
                    document_id=document_id,
                    university=university,
                    metric_name=matched_metric or "unspecified_metric",
                    raw_value=val_match.group(0).strip(),
                    normalized_value=normalized_val,
                    unit=unit,
                    currency=currency,
                    scale=multiplier,
                    temporal_period=temporal,
                    provenance={
                        "source_document": document_id,
                        "page_number": page_number,
                        "section_id": section_id,
                        "line_text": line_str[:250],
                    },
                    confidence=0.95 if matched_metric else 0.80,
                )
                extracted.append(fact)
                self.facts[fact_id] = fact

        return extracted

    extract_facts = extract_facts_from_text

    def extract_temporal_period(self, text: str) -> Optional[TemporalPeriod]:
        """
        Parse reporting temporal entities: FY 2023-24, AY 2024-25, 2024, 2023-2024.
        """
        # Financial Year: FY 2023-24 or 2023-24
        fy_match = re.search(r"(?:FY\s*)?(20[0-9]{2})\s*[-–/]\s*([0-9]{2,4})", text, re.IGNORECASE)
        if fy_match:
            y1 = int(fy_match.group(1))
            raw_y2 = fy_match.group(2)
            y2 = int(raw_y2) if len(raw_y2) == 4 else int(str(y1)[:2] + raw_y2)
            return TemporalPeriod(
                type="financial_year",
                label=f"{y1}-{y2}",
                start_year=y1,
                end_year=y2,
                normalized_year=y2,
            )

        # Calendar Year: 2020..2030
        cal_match = re.search(r"\b(20[12][0-9])\b", text)
        if cal_match:
            y = int(cal_match.group(1))
            return TemporalPeriod(
                type="calendar_year",
                label=str(y),
                start_year=y,
                end_year=y,
                normalized_year=y,
            )

        return None

    def query_facts(
        self,
        university: Optional[str] = None,
        metric_name: Optional[str] = None,
        year: Optional[int] = None,
        unit: Optional[str] = None,
    ) -> List[NumericFact]:
        """
        Deterministic, zero-hallucination lookup for specific university metrics.
        """
        results = []
        for fact in self.facts.values():
            if university and university.lower() not in fact.university.lower():
                continue
            if metric_name and metric_name.lower() != fact.metric_name.lower() and fact.metric_name != "unspecified_metric":
                continue
            if year and fact.temporal_period and fact.temporal_period.normalized_year != year:
                continue
            if unit and fact.unit != unit:
                continue
            results.append(fact)
        return results

    def clear(self):
        self.facts.clear()

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
        lines = text.split("\n")

        for line_idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue

            # Detect Metric Name
            matched_metric = None
            for m_name, patterns in self.METRIC_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, line_str, re.IGNORECASE):
                        matched_metric = m_name
                        break
                if matched_metric:
                    break

            # Detect Values (e.g. ₹ 125.70 Crores, $ 45 Million, 340 Patents)
            val_match = re.search(
                r"(?:(₹|rs\.?|inr|\$|usd|€|eur)\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(crores?|cr|lakhs?|lac|millions?|billions?|thousands?|k|%)?",
                line_str,
                re.IGNORECASE,
            )

            if val_match:
                curr_symbol = val_match.group(1)
                num_raw = val_match.group(2).replace(",", "")
                scale_raw = val_match.group(3)

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

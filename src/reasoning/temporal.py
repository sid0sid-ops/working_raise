"""
RAISE Temporal Reasoning & Event Interval Engine
Models temporal facts as explicit intervals and event sequences.
Supports:
  - AS_OF(date)
  - BEFORE(date)
  - AFTER(date)
  - DURING(interval)
  - LATEST_BEFORE(date)
  - FIRST_AFTER(date)
  - AGE_ON(date, birth_date)
  - ELAPSED_FULL_YEARS(d1, d2)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EventInterval:
    entity: str
    event_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    status: str = "OCCURRED"  # "OCCURRED", "ACTIVE", "CONCLUDED"
    relation: str = "EVENT"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active_on(self, target_date: date) -> bool:
        if self.start_date and target_date < self.start_date:
            return False
        if self.end_date and target_date > self.end_date:
            return False
        return True


class TemporalEngine:
    """
    Deterministic executor for temporal intervals, event ordering, and calendar math.
    """

    MONTH_MAP = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12
    }

    @classmethod
    def parse_flexible_date(cls, text: str) -> Optional[date]:
        """
        Parses dates from diverse representations:
        '1990-05-12', 'July 1, 2024', '1 July 2024', '1990'.
        """
        if not text:
            return None
        t_clean = text.strip().lower()

        # ISO format YYYY-MM-DD
        m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", t_clean)
        if m_iso:
            try:
                return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            except ValueError:
                pass

        # Month Day, Year (e.g. July 1, 2024)
        m_mdy = re.match(r"^([a-z]+)\s+(\d{1,2}),?\s+(\d{4})$", t_clean)
        if m_mdy:
            m_str, d_str, y_str = m_mdy.groups()
            if m_str in cls.MONTH_MAP:
                try:
                    return date(int(y_str), cls.MONTH_MAP[m_str], int(d_str))
                except ValueError:
                    pass

        # Day Month Year (e.g. 1 July 2024)
        m_dmy = re.match(r"^(\d{1,2})\s+([a-z]+),?\s+(\d{4})$", t_clean)
        if m_dmy:
            d_str, m_str, y_str = m_dmy.groups()
            if m_str in cls.MONTH_MAP:
                try:
                    return date(int(y_str), cls.MONTH_MAP[m_str], int(d_str))
                except ValueError:
                    pass

        # Year only (e.g. 1990) -> Default to July 1 of that year
        m_y = re.match(r"^(\d{4})$", t_clean)
        if m_y:
            return date(int(m_y.group(1)), 7, 1)

        return None

    @classmethod
    def elapsed_full_years(cls, date_start: date, date_end: date) -> int:
        """
        Calculates exact elapsed full years according to civil calendar:
        Base = Y2 - Y1.
        If (M2 < M1) or (M2 == M1 and D2 < D1): base - 1, else base.
        """
        base = date_end.year - date_start.year
        if (date_end.month < date_start.month) or (
            date_end.month == date_start.month and date_end.day < date_start.day
        ):
            return base - 1
        return base

    @classmethod
    def age_on_date(cls, birth_date: date, event_date: date) -> int:
        """
        Calculates exact age on date of event.
        """
        return cls.elapsed_full_years(birth_date, event_date)

    @classmethod
    def find_latest_event_before(cls, events: List[EventInterval], reference_date: date) -> Optional[EventInterval]:
        """
        Returns the event with the latest start/end date strictly before reference_date.
        """
        candidates = [
            e for e in events
            if (e.end_date and e.end_date <= reference_date) or (e.start_date and e.start_date <= reference_date)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.end_date or e.start_date or date.min)

    @classmethod
    def find_first_event_after(cls, events: List[EventInterval], reference_date: date) -> Optional[EventInterval]:
        """
        Returns the event with the earliest start date strictly after reference_date.
        """
        candidates = [e for e in events if e.start_date and e.start_date >= reference_date]
        if not candidates:
            return None
        return min(candidates, key=lambda e: e.start_date or date.max)

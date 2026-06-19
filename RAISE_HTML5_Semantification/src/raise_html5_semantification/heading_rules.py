from __future__ import annotations

import re
from statistics import median

from raise_html5_semantification.models import Block
from raise_html5_semantification.profiler import SemanticProfile
from raise_html5_semantification.utils import normalized_type

SECTION_KEYWORDS = {
    "department",
    "research",
    "publications",
    "grants",
    "patents",
    "faculty",
    "awards",
    "collaboration",
    "workshop",
    "conference",
    "outreach",
    "activities",
}


def font_size_baseline(blocks: list[Block]) -> float:
    sizes = [block.font_size for block in blocks if block.font_size]
    return float(median(sizes)) if sizes else 11.0


def contains_section_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in SECTION_KEYWORDS)


def is_uppercase_heading(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and sum(char.isupper() for char in letters) / len(letters) >= 0.8


def classify_heading(
    block: Block,
    baseline_font_size: float | None = None,
    profile: SemanticProfile | None = None,
) -> int | None:
    text = block.text.strip()
    if not text:
        return None

    guess = normalized_type(block.block_type_guess)
    if guess in {"heading", "title", "section-heading", "h1", "h2", "h3"}:
        if guess == "h3":
            return 3
        if guess == "h2" or contains_section_keyword(text):
            return 2
        return 1 if guess == "title" else 2

    words = re.findall(r"\w+", text)
    short_limit = profile.short_heading_word_limit if profile else 12
    short_text = len(words) <= short_limit
    baseline = profile.body_font_size if profile else baseline_font_size or 11.0
    font_size = block.font_size or baseline
    heading_font_size = profile.heading_font_size if profile else baseline + 2.0
    h1_font_size = profile.h1_font_size if profile else baseline + 5.0
    large = font_size >= heading_font_size
    very_large = font_size >= h1_font_size
    bold = bool(block.is_bold)
    uppercase = is_uppercase_heading(text)
    keyword = contains_section_keyword(text) or bool(block.section_hint)

    heading_signals = very_large or (large and bold) or (bold and uppercase) or (bold and keyword)
    if short_text and heading_signals:
        if very_large or uppercase and font_size >= baseline + 3.0:
            return 1
        if keyword or large:
            return 2
        return 3

    return None

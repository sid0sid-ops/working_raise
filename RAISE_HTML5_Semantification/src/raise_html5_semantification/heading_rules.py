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
    # Devanagari / Hindi keywords for state/central university annual reports
    "विभाग",
    "अनुसंधान",
    "प्रकाशन",
    "पेटेंट",
    "पुरस्कार",
    "सहयोग",
    "संगोष्ठी",
    "गतिविधियाँ",
    "विवरण",
    "बजट",
}

DOT_LEADER_RE = re.compile(r"\.{4,}")
WORD_RE = re.compile(r"[^\W\d_]+(?:[’'-][^\W\d_]+)*", re.UNICODE)
TITLE_NUMBER_RE = re.compile(r"(?:\d{4}(?:\s*[-–]\s*\d{2,4})?|\d+(?:st|nd|rd|th))", re.I)
LEADING_MARKERS_RE = re.compile(r"^[\s*#\-–—:.;]+")
FACULTY_RE = re.compile(r"^faculty\s+of\b", re.I)
DEPARTMENT_RE = re.compile(r"^department(?:\s+of)?\b", re.I)
SUBSECTION_RE = re.compile(
    r"^(?:major activities(?: and achievements)?|honou?rs(?:/distinctions)?|"
    r"publications?|research publications?(?:/ research articles?)?|journals?|"
    r"books?(?: and book chapters?)?|book chapters?|research projects?|"
    r"patents?(?: filed/granted)?|seminars?(?: organized| organised)?|"
    r"conferences?(?: organized| organised)?|faculty strength|"
    r"placement details|extension and outreach activities|"
    r"national/international mous? signed|other inter-institutional collaboration|"
    r"students? under exchange programme|number of m\.?phil\.?/ph\.?d\.? degrees awarded|"
    r"financial allocation and utilization|library development|facilities|"
    r"other significant information)\b",
    re.I,
)


def font_size_baseline(blocks: list[Block]) -> float:
    sizes = [block.font_size for block in blocks if block.font_size]
    return float(median(sizes)) if sizes else 11.0


def contains_section_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in SECTION_KEYWORDS)


def is_uppercase_heading(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and sum(char.isupper() for char in letters) / len(letters) >= 0.8


def is_plausible_heading_text(text: str, short_limit: int = 12) -> bool:
    """Reject common PDF table/OCR fragments before applying layout signals."""
    stripped = text.strip()
    words = WORD_RE.findall(stripped)
    if (not words and not TITLE_NUMBER_RE.fullmatch(stripped)) or len(words) > short_limit:
        return False
    if DOT_LEADER_RE.search(stripped):
        return False
    if len([line for line in stripped.splitlines() if line.strip()]) > 2:
        return False

    letters = sum(char.isalpha() for char in stripped)
    alphanumeric = sum(char.isalnum() for char in stripped)
    return bool(TITLE_NUMBER_RE.fullmatch(stripped)) or (
        letters >= 2 and (not alphanumeric or letters / alphanumeric >= 0.45)
    )


def semantic_heading_level(text: str) -> int | None:
    """Return levels for stable annual-report organizational labels."""
    if re.match(r"^\s*(?:[-*•]+|\d+[.)]|[a-zA-Z][.)])\s+", text):
        return None
    normalized = LEADING_MARKERS_RE.sub("", " ".join(text.split())).strip()
    if FACULTY_RE.match(normalized):
        return 1
    if DEPARTMENT_RE.match(normalized):
        return 2
    if SUBSECTION_RE.match(normalized):
        return 3
    return None


def _is_bold(block: Block) -> bool:
    font_name = (block.font_name or "").lower()
    return bool(block.is_bold) or "bold" in font_name or "black" in font_name


def classify_heading(
    block: Block,
    baseline_font_size: float | None = None,
    profile: SemanticProfile | None = None,
) -> int | None:
    text = block.text.strip()
    if not text:
        return None

    short_limit = profile.short_heading_word_limit if profile else 12
    if not is_plausible_heading_text(text, short_limit):
        return None

    guess = normalized_type(block.block_type_guess)
    decimal_match = re.match(r"^\s*(\d+(?:\.\d+)*)\.?\s+[A-Za-z]", text)
    if decimal_match and "\n" not in text:
        parts = decimal_match.group(1).split(".")
        if len(parts) == 1:
            return 1
        elif len(parts) == 2:
            return 2
        elif len(parts) >= 3:
            return 3

    semantic_level = semantic_heading_level(text)
    if semantic_level is not None:
        return semantic_level
    if guess in {"heading", "title", "section-heading", "h1", "h2", "h3"}:
        if guess == "h3":
            return 3
        if guess == "h2":
            return 2
        return 1 if guess in {"title", "h1"} else 2

    words = re.findall(r"\w+", text)
    short_text = len(words) <= short_limit
    
    # Retrieve page-specific localized body font size baseline if available
    baseline = profile.body_font_size if profile else baseline_font_size or 11.0
    if profile and hasattr(profile, "page_body_font_sizes") and profile.page_body_font_sizes:
        baseline = profile.page_body_font_sizes.get(str(block.page_number), baseline)
        
    font_size = block.font_size or baseline
    learned_heading_size = profile.heading_font_size if profile else baseline + 2.0
    learned_h1_size = profile.h1_font_size if profile else baseline + 5.0
    
    # Scale heading thresholds proportionally to the localized baseline
    heading_font_size = max(learned_heading_size, baseline * 1.15, baseline + 1.5)
    h1_font_size = max(learned_h1_size, baseline * 1.45, baseline + 4.0)
    large = font_size >= heading_font_size
    very_large = font_size >= h1_font_size
    bold = _is_bold(block)
    uppercase = is_uppercase_heading(text)
    keyword = contains_section_keyword(text) or bool(block.section_hint)

    score = 0
    score += 3 if very_large else 2 if large else 0
    score += 2 if bold else 0
    score += 1 if uppercase else 0
    score += 2 if keyword else 0
    score += 1 if len(words) <= 8 else 0
    score += 1 if "\n" not in text else -1

    if short_text and score >= 5:
        if very_large and score >= 6:
            return 1
        if keyword or large or uppercase:
            return 2
        return 3

    return None

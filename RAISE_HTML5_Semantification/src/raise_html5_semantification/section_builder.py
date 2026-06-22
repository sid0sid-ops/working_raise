from __future__ import annotations

import re

from raise_html5_semantification.heading_rules import classify_heading, font_size_baseline
from raise_html5_semantification.image_builder import is_image_like
from raise_html5_semantification.models import Block, HtmlNode
from raise_html5_semantification.profiler import SemanticProfile, learn_semantic_profile
from raise_html5_semantification.table_builder import is_table_like
from raise_html5_semantification.utils import normalized_type

BULLET_RE = re.compile(r"^\s*(?:[-*•]|[a-zA-Z]\)|\d+[.)])\s+")
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+")


def classify_block(
    block: Block,
    baseline: float,
    profile: SemanticProfile | None = None,
) -> tuple[str, int | None]:
    if is_image_like(block):
        return "image", None
    heading_level = classify_heading(block, baseline, profile)
    if heading_level:
        return "heading", heading_level

    guess = normalized_type(block.block_type_guess)
    if is_table_like(block):
        return "table", None
    if guess in {"list", "list-item", "bullet", "bullet-list", "numbered-list"} or BULLET_RE.match(
        block.text
    ):
        return "ordered-list" if NUMBERED_RE.match(block.text) else "unordered-list", None
    low_confidence_threshold = profile.low_confidence_threshold if profile else 0.45
    if block.confidence is not None and block.confidence < low_confidence_threshold:
        return "aside", None
    return "paragraph", None


def build_section_tree(
    blocks: list[Block],
    profile: SemanticProfile | None = None,
) -> list[HtmlNode]:
    active_profile = profile or learn_semantic_profile(blocks)
    baseline = active_profile.body_font_size or font_size_baseline(blocks)
    roots: list[HtmlNode] = []
    stack: list[HtmlNode] = []

    for block in blocks:
        if not block.text and not is_table_like(block) and not is_image_like(block):
            continue
        kind, level = classify_block(block, baseline, active_profile)
        node = HtmlNode(kind=kind, block=block, level=level)

        if kind == "heading":
            while stack and (stack[-1].level or 0) >= (level or 1):
                stack.pop()
            if stack:
                stack[-1].children.append(node)
            else:
                roots.append(node)
            stack.append(node)
            continue

        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)

    return roots

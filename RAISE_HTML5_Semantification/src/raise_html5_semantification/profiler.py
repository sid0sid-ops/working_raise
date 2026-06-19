from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from pydantic import BaseModel, Field

from raise_html5_semantification.models import Block
from raise_html5_semantification.utils import ensure_parent, normalized_type


class SemanticProfile(BaseModel):
    """Learned layout thresholds converted into deterministic semantification rules."""

    source_name: str = "learned-profile"
    block_count: int = 0
    body_font_size: float = 11.0
    heading_font_size: float = 14.0
    h1_font_size: float = 16.0
    low_confidence_threshold: float = 0.45
    short_heading_word_limit: int = 12
    common_block_types: list[str] = Field(default_factory=list)
    learned_notes: list[str] = Field(default_factory=list)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return float(ordered[index])


def learn_semantic_profile(
    blocks: list[Block], source_name: str = "learned-profile"
) -> SemanticProfile:
    font_sizes = [float(block.font_size) for block in blocks if block.font_size]
    confidences = [float(block.confidence) for block in blocks if block.confidence is not None]
    heading_sizes = [
        float(block.font_size)
        for block in blocks
        if block.font_size
        and normalized_type(block.block_type_guess) in {"heading", "title", "h1", "h2", "h3"}
    ]
    block_types = sorted({normalized_type(block.block_type_guess) for block in blocks})

    body_font = float(median(font_sizes)) if font_sizes else 11.0
    learned_heading = float(median(heading_sizes)) if heading_sizes else max(body_font + 2.0, 13.0)
    h1_font = max(_percentile(font_sizes, 0.9), learned_heading + 1.0) if font_sizes else 16.0
    low_confidence = min(0.6, max(0.45, _percentile(confidences, 0.1))) if confidences else 0.45

    notes = [
        "Profile is learned from prepared JSON metadata, not from PDF parsing.",
        "Font-size thresholds are deterministic and reusable for future similar reports.",
    ]
    if heading_sizes:
        notes.append("Explicit upstream heading labels were used to calibrate heading thresholds.")
    else:
        notes.append(
            "No explicit heading labels found; heading thresholds use font-size distribution."
        )

    return SemanticProfile(
        source_name=source_name,
        block_count=len(blocks),
        body_font_size=round(body_font, 3),
        heading_font_size=round(learned_heading, 3),
        h1_font_size=round(h1_font, 3),
        low_confidence_threshold=round(low_confidence, 3),
        common_block_types=block_types,
        learned_notes=notes,
    )


def save_semantic_profile(profile: SemanticProfile, output_path: str | Path) -> None:
    path = Path(output_path)
    ensure_parent(path)
    path.write_text(json.dumps(profile.model_dump(), indent=2), encoding="utf-8")


def load_semantic_profile(input_path: str | Path | None) -> SemanticProfile | None:
    if not input_path:
        return None
    raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return SemanticProfile.model_validate(raw)

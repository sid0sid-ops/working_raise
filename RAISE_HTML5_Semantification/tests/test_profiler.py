from pathlib import Path

from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.profiler import learn_semantic_profile


def test_learn_semantic_profile_creates_reusable_thresholds() -> None:
    blocks = load_blocks(Path("tests/fixtures/target_blocks.json"))
    profile = learn_semantic_profile(blocks, source_name="fixture")

    assert profile.block_count == 5
    assert profile.body_font_size > 0
    assert profile.heading_font_size >= profile.body_font_size
    assert profile.low_confidence_threshold >= 0.45
    assert "paragraph" in profile.common_block_types

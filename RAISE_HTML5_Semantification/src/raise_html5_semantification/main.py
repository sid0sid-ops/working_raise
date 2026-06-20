from __future__ import annotations

from pathlib import Path

from raise_html5_semantification.html_writer import write_html
from raise_html5_semantification.loader import load_blocks
from raise_html5_semantification.profiler import (
    learn_semantic_profile,
    load_semantic_profile,
    save_semantic_profile,
)
from raise_html5_semantification.section_builder import build_section_tree
from raise_html5_semantification.validator import validate_html_string, write_validation_report


def build_report(
    input_path: str | Path = "data/input/target_blocks.json",
    output_path: str | Path = "data/output/report.html",
    validation_output_path: str | Path = "data/output/validation_report.json",
    profile_input_path: str | Path | None = None,
    profile_output_path: str | Path | None = "data/output/semantic_profile.json",
    schema_path: str | Path | None = None,
) -> str:
    blocks = load_blocks(input_path, schema_path=schema_path)
    profile = load_semantic_profile(profile_input_path) or learn_semantic_profile(
        blocks, source_name=str(input_path)
    )
    if profile_output_path:
        save_semantic_profile(profile, profile_output_path)
    nodes = build_section_tree(blocks, profile=profile)
    html = write_html(nodes, output_path)
    summary = validate_html_string(html, expected_blocks=len(blocks))
    write_validation_report(summary, validation_output_path)
    return html

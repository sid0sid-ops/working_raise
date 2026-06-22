from __future__ import annotations

from pathlib import Path

from raise_html5_semantification.artifacts import build_ai_chunks, build_section_map, write_models
from raise_html5_semantification.html_writer import write_html, write_source_map
from raise_html5_semantification.input_quality import (
    build_input_quality_report,
    write_input_quality_report,
)
from raise_html5_semantification.loader import load_blocks, load_raw_blocks
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
    source_map_output_path: str | Path | None = "data/output/source_map.json",
    section_map_output_path: str | Path | None = "data/output/section_map.json",
    ai_chunks_output_path: str | Path | None = "data/output/ai_chunks.json",
    input_quality_output_path: str | Path | None = "data/output/input_quality_report.json",
    outline_depth: int = 2,
) -> str:
    raw_blocks = load_raw_blocks(input_path, schema_path=schema_path)
    blocks = load_blocks(input_path, schema_path=schema_path)
    profile = load_semantic_profile(profile_input_path) or learn_semantic_profile(
        blocks, source_name=str(input_path)
    )
    if profile_output_path:
        save_semantic_profile(profile, profile_output_path)
    nodes = build_section_tree(blocks, profile=profile)
    html = write_html(nodes, output_path, outline_depth=outline_depth)
    source_map_entry_count = 0
    if source_map_output_path:
        source_map = write_source_map(nodes, source_map_output_path, input_block_count=len(blocks))
        source_map_entry_count = len(source_map.blocks)
    sections = build_section_map(nodes)
    if section_map_output_path:
        write_models(sections, section_map_output_path)
    chunks = build_ai_chunks(nodes)
    if ai_chunks_output_path:
        write_models(chunks, ai_chunks_output_path)
    input_quality_report = build_input_quality_report(raw_blocks)
    if input_quality_output_path:
        write_input_quality_report(input_quality_report, input_quality_output_path)
    summary = validate_html_string(
        html,
        expected_blocks=len(blocks),
        chunk_count=len(chunks),
        source_map_entry_count=source_map_entry_count,
        input_quality_report=input_quality_report,
    )
    write_validation_report(summary, validation_output_path)
    return html

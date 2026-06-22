from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from raise_html5_semantification.loader import InputValidationError, load_blocks
from raise_html5_semantification.main import build_report
from raise_html5_semantification.profiler import learn_semantic_profile, save_semantic_profile
from raise_html5_semantification.section_builder import classify_block
from raise_html5_semantification.validator import validate_input_file

app = typer.Typer(help="RAISE clean HTML5 semantification for prepared block JSON.")
console = Console()
INPUT_OPTION = typer.Option(Path("data/input/target_blocks.json"), "--input", "-i")
OUTPUT_OPTION = typer.Option(Path("data/output/report.html"), "--output", "-o")
VALIDATION_OUTPUT_OPTION = typer.Option(
    Path("data/output/validation_report.json"), "--validation-output"
)
SOURCE_MAP_OUTPUT_OPTION = typer.Option(Path("data/output/source_map.json"), "--source-map-output")
SECTION_MAP_OUTPUT_OPTION = typer.Option(
    Path("data/output/section_map.json"), "--section-map-output"
)
AI_CHUNKS_OUTPUT_OPTION = typer.Option(Path("data/output/ai_chunks.json"), "--ai-chunks-output")
INPUT_QUALITY_OUTPUT_OPTION = typer.Option(
    Path("data/output/input_quality_report.json"), "--input-quality-output"
)
OUTLINE_DEPTH_OPTION = typer.Option(2, "--outline-depth", min=1, max=3)
BUILD_PROFILE_OUTPUT_OPTION = typer.Option(
    Path("data/output/semantic_profile.json"), "--profile-output"
)
LEARN_PROFILE_OUTPUT_OPTION = typer.Option(
    Path("data/output/semantic_profile.json"), "--profile-output", "--output"
)
PROFILE_INPUT_OPTION = typer.Option(None, "--profile-input")
SCHEMA_OPTION = typer.Option(None, "--schema")


@app.command()
def build(
    input: Path = INPUT_OPTION,
    output: Path = OUTPUT_OPTION,
    validation_output: Path = VALIDATION_OUTPUT_OPTION,
    source_map_output: Path = SOURCE_MAP_OUTPUT_OPTION,
    section_map_output: Path = SECTION_MAP_OUTPUT_OPTION,
    ai_chunks_output: Path = AI_CHUNKS_OUTPUT_OPTION,
    input_quality_output: Path = INPUT_QUALITY_OUTPUT_OPTION,
    outline_depth: int = OUTLINE_DEPTH_OPTION,
    profile_input: Path | None = PROFILE_INPUT_OPTION,
    profile_output: Path | None = BUILD_PROFILE_OUTPUT_OPTION,
    schema: Path | None = SCHEMA_OPTION,
) -> None:
    """Build semantic HTML5 and validation report from prepared block JSON."""
    try:
        build_report(
            input,
            output,
            validation_output,
            profile_input,
            profile_output,
            schema_path=schema,
            source_map_output_path=source_map_output,
            section_map_output_path=section_map_output,
            ai_chunks_output_path=ai_chunks_output,
            input_quality_output_path=input_quality_output,
            outline_depth=outline_depth,
        )
    except (InputValidationError, ValueError, OSError) as exc:
        console.print(f"[red]Build failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Wrote semantic HTML:[/green] {output}")
    console.print(f"[green]Wrote validation report:[/green] {validation_output}")
    console.print(f"[green]Wrote source map:[/green] {source_map_output}")
    console.print(f"[green]Wrote section map:[/green] {section_map_output}")
    console.print(f"[green]Wrote AI-ready chunks:[/green] {ai_chunks_output}")
    console.print(f"[green]Wrote input quality report:[/green] {input_quality_output}")
    if profile_output:
        console.print(f"[green]Wrote semantic profile:[/green] {profile_output}")


@app.command("learn-profile")
def learn_profile(
    input: Path = INPUT_OPTION,
    output: Path = LEARN_PROFILE_OUTPUT_OPTION,
) -> None:
    """Learn reusable semantification thresholds from prepared JSON metadata."""
    try:
        blocks = load_blocks(input)
        profile = learn_semantic_profile(blocks, source_name=str(input))
        save_semantic_profile(profile, output)
    except (InputValidationError, ValueError, OSError) as exc:
        console.print(f"[red]Profile learning failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Wrote learned semantic profile:[/green] {output}")


@app.command()
def validate(input: Path = INPUT_OPTION) -> None:
    """Validate input JSON structure."""
    summary = validate_input_file(input)
    if summary.ok:
        console.print(f"[green]Input is valid.[/green] Blocks: {summary.input_block_count}")
    else:
        for issue in summary.issues:
            console.print(f"[red]{issue.severity.upper()}[/red] {issue.message}")
        raise typer.Exit(1)


@app.command()
def inspect(input: Path = INPUT_OPTION) -> None:
    """Inspect block classification decisions."""
    blocks = load_blocks(input)
    profile = learn_semantic_profile(blocks, source_name=str(input))
    baseline = 11.0
    sizes = [block.font_size for block in blocks if block.font_size]
    if sizes:
        baseline = sorted(sizes)[len(sizes) // 2]

    table = Table(title="RAISE Block Inspection")
    table.add_column("Order")
    table.add_column("Block ID")
    table.add_column("Page")
    table.add_column("Kind")
    table.add_column("Level")
    table.add_column("Text")

    for block in blocks:
        kind, level = classify_block(block, baseline, profile)
        table.add_row(
            "" if block.reading_order is None else str(block.reading_order),
            block.block_id,
            "" if block.page_number is None else str(block.page_number),
            kind,
            "" if level is None else str(level),
            block.text[:72],
        )
    console.print(table)

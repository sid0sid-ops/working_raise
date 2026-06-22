import json
import os
import shutil
import tempfile
from pathlib import Path

import nbformat
from bs4 import BeautifulSoup

NOTEBOOK = Path("notebooks/RAISE_HTML5_Semantification_Colab.ipynb")
FIXTURES = [
    Path("tests/fixtures/target_blocks.json"),
    Path("tests/fixtures/alternate_format.json"),
    Path("tests/fixtures/tough_annual_report_nested.json"),
    Path("tests/fixtures/tough_annual_report_tables.json"),
    Path("tests/fixtures/tough_annual_report_minimal.json"),
]


def _notebook_cells() -> dict[str, str]:
    notebook = nbformat.read(NOTEBOOK, nbformat.NO_CONVERT)
    return {cell.get("id"): "".join(cell.source) for cell in notebook.cells}


def test_colab_notebook_uploads_json_not_pdf() -> None:
    cells = _notebook_cells()

    assert "files.upload()" in cells["upload-json"]
    assert "PDF" in "".join(nbformat.read(NOTEBOOK, nbformat.NO_CONVERT).cells[0].source)
    download_cell = cells["download-outputs"]
    assert "files.download(output_path)" in download_cell
    assert "raise_html5_semantification_outputs.zip" in download_cell
    for filename in (
        "report.html",
        "source_map.json",
        "section_map.json",
        "ai_chunks.json",
        "validation_report.json",
        "input_quality_report.json",
    ):
        assert filename in cells["run-semantification"] or filename in download_cell


def test_colab_notebook_detects_gpu_tpu_or_cpu_runtime() -> None:
    runtime_cell = _notebook_cells()["colab-runtime-check"]

    assert "nvidia-smi" in runtime_cell
    assert "GPU runtime detected" in runtime_cell
    assert "TPU runtime detected" in runtime_cell
    assert "CPU runtime detected" in runtime_cell


def test_colab_notebook_requires_github_package_install() -> None:
    install_cell = _notebook_cells()["github-install-hook"]

    assert "GITHUB_PACKAGE" in install_cell
    assert "subprocess.check_call" in install_cell
    assert '"--no-cache-dir"' in install_cell
    assert "self-contained" not in install_cell
    assert "except" not in install_cell


def test_colab_notebook_explains_each_workflow_stage() -> None:
    cells = _notebook_cells()
    required_notes = {
        "upload-notes",
        "dependency-notes",
        "github-install-notes",
        "runtime-notes",
        "engine-notes",
        "smoke-tests-notes",
        "conversion-notes",
        "preview-notes",
        "download-notes",
    }

    assert required_notes <= cells.keys()
    notebook_text = "\n".join(cells.values()).lower()
    assert "your own file" not in notebook_text
    assert "during the presentation" not in notebook_text
    assert "json robustness smoke tests" in notebook_text


def test_colab_engine_runs_standard_and_alternate_json_shapes() -> None:
    cells = _notebook_cells()

    assert "from raise_html5_semantification.main import build_report" in cells["engine-code"]
    assert "def classify_block" not in cells["engine-code"]
    assert "build_report(" in cells["run-semantification"]

    smoke_namespace: dict[str, object] = {}
    exec(cells["engine-code"], smoke_namespace)
    exec(cells["smoke-tests-code"], smoke_namespace)
    assert all(result["ok"] for result in smoke_namespace["smoke_results"])

    for fixture in FIXTURES:
        namespace: dict[str, object] = {}
        exec(cells["engine-code"], namespace)
        temp_dir = Path(tempfile.mkdtemp())
        shutil.copy(fixture, temp_dir / fixture.name)
        current_dir = Path.cwd()
        try:
            os.chdir(temp_dir)
            namespace["input_filename"] = fixture.name
            exec(cells["run-semantification"], namespace)

            report_html = Path("report.html").read_text(encoding="utf-8")
            validation_report = json.loads(Path("validation_report.json").read_text())
            soup = BeautifulSoup(report_html, "lxml")

            assert validation_report["ok"]
            assert Path("source_map.json").exists()
            assert Path("section_map.json").exists()
            assert Path("ai_chunks.json").exists()
            assert Path("input_quality_report.json").exists()
            assert soup.find("main", attrs={"aria-label": "Semantic annual report content"})
            assert soup.find("article", attrs={"id": "semantic-report"})
            assert soup.find("nav", attrs={"id": "document-outline"})
            assert soup.find(attrs={"data-semantic-role": "section"})
        finally:
            os.chdir(current_dir)

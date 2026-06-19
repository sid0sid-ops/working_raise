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
    assert "files.download(semantic_html_path)" in cells["download-outputs"]


def test_colab_engine_runs_standard_and_alternate_json_shapes() -> None:
    cells = _notebook_cells()

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
            assert soup.find("main", attrs={"aria-label": "Semantic annual report content"})
            assert soup.find("article", attrs={"id": "semantic-report"})
            assert soup.find("nav", attrs={"id": "document-outline"})
            assert soup.find(attrs={"data-semantic-role": "section"})
        finally:
            os.chdir(current_dir)

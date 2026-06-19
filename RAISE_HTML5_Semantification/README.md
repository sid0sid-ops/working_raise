# RAISE HTML5 Semantification

Module owner: **Siddharth Tripathi**

This module folder implements Siddharth Tripathi's RAISE project module:
**RAISE: Research Assessment Intelligence & Semantic Extraction**.

Main repository:

```text
https://github.com/semanticClimate/RAISE.git
```

Branch:

```text
siddharth-semantification
```

Module folder:

```text
RAISE_HTML5_Semantification
```

The module starts after PDF parsing, PDF filtering, and upstream block preparation are complete. It receives structured annual-report block JSON and converts it into clean, valid, traceable, semantic HTML5 for the next AI extraction stage.

## Boundary

This module does **not** perform PDF parsing. It does **not** perform PDF filtering. It does **not** perform AI structured extraction. It does **not** perform final JSON extraction. It does **not** perform CERIF or Wikidata mapping.

The only task here is HTML5 semantification.

## Input

Expected input file:

```text
data/input/target_blocks.json
```

The input may be either a list of blocks or an object containing `blocks`, `target_blocks`, or `content_blocks`.

Example:

```json
{
  "source_file": "university_annual_report.pdf",
  "blocks": [
    {
      "block_id": "page1_block4",
      "page_number": 1,
      "text": "RESEARCH ACTIVITIES",
      "bbox": [72, 100, 420, 130],
      "font_size": 18,
      "font_name": "Times-Bold",
      "is_bold": true,
      "is_italic": false,
      "reading_order": 4,
      "block_type_guess": "heading",
      "confidence": 0.98,
      "section_hint": "Research",
      "source_file": "university_annual_report.pdf"
    }
  ]
}
```

## Output

Primary output:

```text
data/output/report.html
```

Validation output:

```text
data/output/validation_report.json
```

Learned semantic profile output:

```text
data/output/semantic_profile.json
```

For the next teammate, use:

```python
semantic_html_path = "data/output/report.html"
validation_report_path = "data/output/validation_report.json"
semantic_profile_path = "data/output/semantic_profile.json"
```

The next AI extraction stage should read `semantic_html_path`. Every meaningful HTML element contains traceability attributes:

```html
<p
  id="p-page1-block4"
  data-page="1"
  data-source-block="page1_block4"
  data-block-type="paragraph"
  data-bbox="[72, 100, 420, 130]"
  data-confidence="0.980"
  data-reading-order="4">
  ...
</p>
```

The output also includes an accessible document outline, `aria-labelledby` links between sections
and headings, `data-semantic-role`, source file metadata, generated-ID flags, table cell
coordinates, list-item indexes, captions, and stable IDs for meaningful list/table children.

## HTML5 Semantics

The writer uses semantic HTML elements including `html`, `head`, `body`, `header`, `main`, `footer`, `section`, `h1`, `h2`, `h3`, `p`, `aside`, `ul`, `ol`, `li`, `table`, `thead`, `tbody`, `tr`, `th`, `td`, `figure`, `figcaption`, and `pre`.

Heading detection is rule based:

- Respect `block_type_guess` when it says heading/title/h1/h2/h3.
- Use font size, bold text, short text, uppercase text, and section keywords.
- Section keywords include Department, Research, Publications, Grants, Patents, Faculty, Awards, Collaboration, Workshop, Conference, Outreach, and Activities.

Table handling is intentionally limited:

- If upstream data marks a block as `table` or `table-candidate`, this module converts already-present rows or simple delimited text into an HTML table.
- If structure is unclear, the text is preserved inside `figure > pre`.
- This module does not extract tables from PDFs.

## Learned Semantic Profile

The module can learn deterministic layout thresholds from prepared JSON metadata. This is not
PDF parsing and not AI extraction. It learns reusable semantification signals such as body font
size, heading font size, H1 threshold, low-confidence threshold, and common upstream block labels.

The learned profile is saved as JSON and can be reused for future reports with similar formatting:

```bash
uv run python -m raise_html5_semantification learn-profile \
  --input data/input/target_blocks.json \
  --output data/output/semantic_profile.json
```

Build with a saved profile:

```bash
uv run python -m raise_html5_semantification build \
  --input data/input/target_blocks.json \
  --output data/output/report.html \
  --profile-input data/output/semantic_profile.json
```

## Setup

```bash
uv sync --extra dev
```

If you prefer installing from requirements:

```bash
uv pip install -r requirements.txt
```

## Commands

Build semantic HTML:

```bash
uv run python -m raise_html5_semantification build --input data/input/target_blocks.json --output data/output/report.html
```

Validate input JSON:

```bash
uv run python -m raise_html5_semantification validate --input data/input/target_blocks.json
```

Inspect classification decisions:

```bash
uv run python -m raise_html5_semantification inspect --input data/input/target_blocks.json
```

Run quality checks:

```bash
uv run ruff check .
uv run pytest
```

## Colab Demo

Use this Colab notebook:

```text
notebooks/RAISE_HTML5_Semantification_Colab.ipynb
```

Colab link:

```text
https://colab.research.google.com/github/semanticClimate/RAISE/blob/siddharth-semantification/RAISE_HTML5_Semantification/notebooks/RAISE_HTML5_Semantification_Colab.ipynb
```

The notebook uploads JSON, not PDF. It installs dependencies, uploads `target_blocks.json`, runs semantification, generates `report.html` and `validation_report.json`, and downloads both files.

It also generates and downloads `semantic_profile.json`. The notebook includes a Colab runtime
check that reports whether a TPU runtime is active. HTML5 semantification is deterministic string
and JSON processing, so it does not require a TPU; TPU availability is only reported for the demo
environment.

## Limitations

- Rule-based headings can be imperfect when upstream metadata is weak.
- Table conversion only works for table-like blocks already identified upstream.
- Reading order depends on the upstream `reading_order` field.
- The module preserves traceability but does not judge research-assessment meaning.

## Next Improvements Within This Module

- Add configurable heading thresholds per university/report template.
- Add richer list grouping for multi-block bullet lists.
- Add optional CSS themes for reviewer-friendly HTML.
- Add an HTML diff tool for comparing semantification rule changes.

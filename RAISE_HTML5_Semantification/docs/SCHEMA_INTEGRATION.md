# Future Schema Integration

## Current Status

The schema at
`src/raise_html5_semantification/semantic_input.schema.json` is a temporary schema for current
development and Colab verification. It is packaged with the Python module so validation works in
a clean Colab installation without depending on the repository working directory.

This temporary schema is not the final inter-module contract. The authoritative schema and the
actual prepared JSON input will be supplied by the team member responsible for the upstream stage.

## Current Data Flow

1. The upstream stage extracts and filters annual-report content into prepared JSON blocks.
2. `load_blocks()` validates that JSON against the selected schema.
3. The loader locates the block list and maps supported field aliases into the `Block` model.
4. `build_report()` classifies the blocks and writes semantic HTML, a validation report, and a
   learned semantic profile.
5. The Colab notebook calls `build_report()` from the package installed from GitHub.

PDF files are not inputs to this module.

## Required Team Handoff

Collect these items before replacing the temporary schema:

- The authoritative JSON Schema file and its declared draft version.
- At least one representative valid JSON document.
- Invalid or edge-case examples that validation must reject.
- The schema version, owner, and expected change process.
- The exact root structure and path containing the content blocks.
- Required and optional fields, nullability rules, and default behavior.
- Field meanings and units, especially page numbers, bounding boxes, font sizes, confidence values,
  reading order, tables, and source identifiers.
- Rules for stable block IDs and source traceability.
- Any enums or controlled values for block type and semantic hints.

## Integration Options

### Replace the Packaged Default

Use this when the authoritative schema becomes the default contract for every caller:

1. Replace `src/raise_html5_semantification/semantic_input.schema.json` with the authoritative
   schema while retaining that packaged filename.
2. Review `FIELD_ALIASES` and the `Block` model in
   `src/raise_html5_semantification/models.py` against every schema property.
3. Review `BLOCK_CONTAINER_KEYS`, extraction, and normalization in
   `src/raise_html5_semantification/loader.py` against the final root structure.
4. Add the supplied valid, invalid, and edge-case documents as test fixtures.
5. Run the package, clean-wheel, and Colab notebook tests before publishing the branch.

### Supply an External Schema

Use this during migration or when multiple schema versions must be tested. The API already accepts
an explicit path:

```python
from raise_html5_semantification.main import build_report

build_report(
    input_path="target_blocks.json",
    output_path="report.html",
    validation_output_path="validation_report.json",
    profile_output_path="semantic_profile.json",
    schema_path="authoritative_schema.json",
)
```

The command-line equivalent is:

```bash
raise-html5-semantification build \
  --input target_blocks.json \
  --schema authoritative_schema.json \
  --output report.html
```

When the Colab workflow needs an external schema, upload or fetch the versioned schema before the
conversion cell and pass its path as `schema_path`. Do not silently fall back to the temporary
schema if the authoritative schema was requested.

## Compatibility Review

Schema validation alone is not enough. Confirm that the runtime model and transformation rules
preserve the final contract:

- Every required schema field is represented or intentionally ignored.
- Aliases do not map two different source meanings into one field.
- Numeric and string coercion is acceptable to the upstream owner.
- Missing IDs are either rejected or generated according to the agreed policy.
- Reading order is stable and deterministic.
- Table rows retain their original cell order and values.
- Low-confidence content is preserved and traceable rather than discarded.
- Generated HTML elements retain `data-source-block` and related provenance attributes.

## Acceptance Checks

The authoritative schema integration is complete only when:

1. All supplied valid examples load and produce valid semantic HTML.
2. All supplied invalid examples fail with clear validation messages.
3. A clean built wheel contains the schema and runs outside the repository directory.
4. The Colab notebook imports the installed GitHub package and completes all smoke tests.
5. The validation report has no traceability errors.
6. The schema version and representative fixture are recorded in the repository documentation.

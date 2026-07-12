from raise_html5_semantification.models import Block
from raise_html5_semantification.table_builder import table_rows


def test_converts_homogeneous_object_list_to_header_and_rows() -> None:
    block = Block(
        block_id="table",
        block_type_guess="table",
        rows=[
            {"Name": "A", "Count": 2},
            {"Count": 3, "Name": "B"},
        ],
    )

    assert table_rows(block) == [["Name", "Count"], ["A", "2"], ["B", "3"]]


def test_converts_object_to_field_value_table() -> None:
    block = Block(
        block_id="table",
        block_type_guess="table",
        table={"Institution": "Example University", "Year": 2025},
    )

    assert table_rows(block) == [
        ["Field", "Value"],
        ["Institution", "Example University"],
        ["Year", "2025"],
    ]


def test_preserves_empty_cells_and_pads_uneven_rows() -> None:
    block = Block(block_id="table", block_type_guess="table", text="A||C\n1|2")

    assert table_rows(block) == [["A", "", "C"], ["1", "2", ""]]


def test_converts_heterogeneous_object_list_with_missing_keys_to_header_and_rows() -> None:
    block = Block(
        block_id="table",
        block_type_guess="table",
        rows=[
            {"Name": "A", "Count": 2},
            {"Name": "B", "Year": 2024},
        ],
    )

    assert table_rows(block) == [
        ["Name", "Count", "Year"],
        ["A", "2", ""],
        ["B", "", "2024"],
    ]


def test_merges_text_wrapped_rows() -> None:
    block = Block(
        block_id="table",
        block_type_guess="table",
        rows=[
            ["1", "Prof. John Doe", "Development of Novel Vaccine"],
            ["", "", "and Adjuvants"],
            ["2", "Dr. Jane Smith", "AI-based Drug Discovery"],
        ],
    )

    assert table_rows(block) == [
        ["1", "Prof. John Doe", "Development of Novel Vaccine and Adjuvants"],
        ["2", "Dr. Jane Smith", "AI-based Drug Discovery"],
    ]

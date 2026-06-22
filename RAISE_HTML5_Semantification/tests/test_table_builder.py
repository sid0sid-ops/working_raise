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

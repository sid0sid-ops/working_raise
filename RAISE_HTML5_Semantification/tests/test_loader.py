from pathlib import Path

from raise_html5_semantification.loader import load_blocks

FIXTURE = Path("tests/fixtures/target_blocks.json")


def test_load_blocks_sorts_by_reading_order() -> None:
    blocks = load_blocks(FIXTURE)

    assert len(blocks) == 5
    assert blocks[0].block_id == "b001"
    assert blocks[-1].reading_order == 5

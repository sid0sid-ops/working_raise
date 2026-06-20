from pathlib import Path

from raise_html5_semantification.loader import load_blocks

FIXTURE = Path("tests/fixtures/target_blocks.json")


def test_load_blocks_sorts_by_reading_order() -> None:
    blocks = load_blocks(FIXTURE)

    assert len(blocks) == 5
    assert blocks[0].block_id == "b001"
    assert blocks[-1].reading_order == 5


def test_default_schema_is_available_outside_repository_root(tmp_path, monkeypatch) -> None:
    fixture = FIXTURE.resolve()
    monkeypatch.chdir(tmp_path)

    blocks = load_blocks(fixture)

    assert len(blocks) == 5

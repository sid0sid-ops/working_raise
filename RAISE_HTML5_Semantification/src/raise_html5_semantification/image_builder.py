from __future__ import annotations

from raise_html5_semantification.models import Block
from raise_html5_semantification.utils import normalized_type

IMAGE_BLOCK_TYPES = {"image", "figure", "chart", "diagram"}


def is_image_like(block: Block) -> bool:
    return normalized_type(block.block_type_guess) in IMAGE_BLOCK_TYPES or any(
        (block.image_path, block.image_src, block.caption, block.alt_text)
    )


def image_source(block: Block) -> str | None:
    return block.image_src or block.image_path

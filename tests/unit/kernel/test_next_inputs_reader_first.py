"""Readers of `next.inputs` ship one release before the first producer.

The Change that makes the first producer emit `inputs` deletes this module, and nothing else of
the reader's tests.
"""

import re
from pathlib import Path

_PRODUCT = Path(__file__).resolve().parents[3] / "src/ethos"


def test_no_producer_emits_inputs_before_their_reader_has_shipped() -> None:
    """Only the contract and the result model name the inputs, so no operation can set them."""
    naming = [
        path.relative_to(_PRODUCT).as_posix()
        for path in sorted(_PRODUCT.rglob("*.py"))
        if re.search(r"\b(next_inputs|NextInput)\b", path.read_text(encoding="utf-8"))
    ]

    assert naming == ["contracts/next_step.py", "result.py"]

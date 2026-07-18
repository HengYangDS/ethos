"""Shared subprocess and registry helpers for architecture tests."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def run_json(root: Path, command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def tool_block(root: Path, concern: str) -> str:
    text = (root / "system" / "tools.toml").read_text(encoding="utf-8")
    marker = f'concern = "{concern}"'
    assert marker in text
    before, after = text.split(marker, 1)
    block_start = before.rfind("[[tool]]")
    next_block = after.find("[[tool]]")
    body = marker + (after if next_block == -1 else after[:next_block])
    return before[block_start:] + body

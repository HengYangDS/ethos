"""Run reusable architecture probes and isolated executable fixtures."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
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


def isolated_path(tmp_path: Path, executables: Mapping[str, str]) -> dict[str, str]:
    """Materialize executable fixtures on a minimal cross-platform PATH."""
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    for name, body in executables.items():
        path = fake_bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(fake_bin), "/bin", "/usr/bin"))
    return env

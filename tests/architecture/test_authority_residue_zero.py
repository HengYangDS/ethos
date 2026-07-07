from __future__ import annotations

import re
import subprocess
from pathlib import Path

AUTHORITY_PREDECESSOR_RESIDUE_RE = re.compile(
    rb"judg(?:e)?ment(?:[\s._/-]+)?sources?",
    re.IGNORECASE,
)


def test_repository_has_no_authority_predecessor_residue() -> None:
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        text=False,
    ).split(b"\0")
    hits: list[str] = []

    for raw_path in paths:
        if not raw_path:
            continue

        relative = raw_path.decode("utf-8", errors="surrogateescape")
        if AUTHORITY_PREDECESSOR_RESIDUE_RE.search(raw_path):
            hits.append(f"path:{relative}")

        data = Path(relative).read_bytes()
        for line_number, line in enumerate(data.splitlines(), 1):
            if AUTHORITY_PREDECESSOR_RESIDUE_RE.search(line):
                text = line.decode("utf-8", errors="replace").strip()
                hits.append(f"content:{relative}:{line_number}:{text}")

    assert hits == []

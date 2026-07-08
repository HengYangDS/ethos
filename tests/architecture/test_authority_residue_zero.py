from __future__ import annotations

import re
import subprocess
from pathlib import Path

AUTHORITY_PREDECESSOR_RESIDUE_RE = re.compile(
    rb"judg(?:e)?ment(?:[\s._/-]+)?sources?",
    re.IGNORECASE,
)
HISTORICAL_PREFIXES = (
    "evidence/",
    "openspec/changes/archive/",
)
HISTORICAL_RECORDS_WITH_PREDECESSOR = (
    "evidence/chronicle/productization-convergence/2026-07-01.md",
    "openspec/changes/archive/2026-07-01-ethos-productization-convergence/design.md",
    "openspec/changes/archive/2026-07-08-authority-kernel-head-rename/proposal.md",
)
PREDECESSOR_TERM = "Judgment" + "Source"


def _tracked_paths() -> list[bytes]:
    return [
        raw_path
        for raw_path in subprocess.check_output(
            ["git", "ls-files", "-z", "--cached"],
            text=False,
        ).split(b"\0")
        if raw_path
    ]


def _is_historical_record(relative: str) -> bool:
    return relative.startswith(HISTORICAL_PREFIXES)


def test_current_truth_surfaces_have_no_authority_predecessor_residue() -> None:
    hits: list[str] = []

    for raw_path in _tracked_paths():
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        if _is_historical_record(relative):
            continue
        if AUTHORITY_PREDECESSOR_RESIDUE_RE.search(raw_path):
            hits.append(f"path:{relative}")

        data = Path(relative).read_bytes()
        for line_number, line in enumerate(data.splitlines(), 1):
            if AUTHORITY_PREDECESSOR_RESIDUE_RE.search(line):
                text = line.decode("utf-8", errors="replace").strip()
                hits.append(f"content:{relative}:{line_number}:{text}")

    assert hits == []


def test_historical_records_preserve_authority_predecessor_vocabulary() -> None:
    missing = [
        relative
        for relative in HISTORICAL_RECORDS_WITH_PREDECESSOR
        if PREDECESSOR_TERM not in Path(relative).read_text(encoding="utf-8")
    ]

    assert missing == []

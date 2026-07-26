from __future__ import annotations

import re
import subprocess
from pathlib import Path

AUTHORITY_PREDECESSOR_RESIDUE_RE = re.compile(
    rb"judg(?:e)?ment(?:[\s._/-]+)?sources?",
    re.IGNORECASE,
)


def _git_admissible_paths() -> list[bytes]:
    return [
        raw_path
        for raw_path in subprocess.check_output(
            [
                "git",
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            text=False,
        ).split(b"\0")
        if raw_path
    ]


def _read_path_payload(path: Path) -> bytes:
    if path.is_symlink():
        return str(path.readlink()).encode("utf-8", errors="surrogateescape")
    return path.read_bytes()


def test_no_authority_predecessor_residue_in_git_admissible_repository() -> None:
    hits: list[str] = []

    for raw_path in _git_admissible_paths():
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        path = Path(relative)
        if path.is_dir():
            hits.append(f"directory-returned-by-git:{relative}")
            continue
        if not (path.is_file() or path.is_symlink()):
            if relative in _deleted_paths():
                continue
            hits.append(f"missing-or-special:{relative}")
            continue
        if AUTHORITY_PREDECESSOR_RESIDUE_RE.search(raw_path):
            hits.append(f"path:{relative}")

        data = _read_path_payload(path)
        for line_number, line in enumerate(data.splitlines() or [data], 1):
            if AUTHORITY_PREDECESSOR_RESIDUE_RE.search(line):
                text = line.decode("utf-8", errors="replace").strip()
                hits.append(f"content:{relative}:{line_number}:{text}")

    assert hits == []


def _deleted_paths() -> set[str]:
    return set(
        subprocess.check_output(
            ["git", "ls-files", "--deleted"],
            text=True,
        ).splitlines()
    )

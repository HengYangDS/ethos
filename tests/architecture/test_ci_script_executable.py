from __future__ import annotations

import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_DIRECT_SCRIPT_RE = re.compile(r"^\s*-\s+(tools/ci/scripts/[^\s]+\.sh)\s*$")


def _direct_ci_scripts() -> set[Path]:
    ci_text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    return {
        ROOT / match.group(1)
        for line in ci_text.splitlines()
        if (match := CI_DIRECT_SCRIPT_RE.match(line))
    }


def test_gitlab_direct_owner_scripts_are_executable() -> None:
    """GitLab executes direct script entries by path, so owner scripts need +x."""
    missing = [
        path.relative_to(ROOT).as_posix()
        for path in sorted(_direct_ci_scripts())
        if not path.exists() or not path.stat().st_mode & stat.S_IXUSR
    ]

    assert missing == []

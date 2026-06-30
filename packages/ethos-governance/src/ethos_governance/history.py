from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ethos_governance.commit_policy import commit_subject_ok

EXPECTED_AUTHOR = "Yang HENG <heng.yang.ds@hotmail.com>"
EXPECTED_NAME = "Yang HENG"
EXPECTED_EMAIL = "heng.yang.ds@hotmail.com"


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout


def history_identity_report(root: Path) -> dict[str, Any]:
    raw = _git(root, "log", "--all", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%G?%x00%s")
    commits: list[dict[str, str]] = []
    raw_mismatches: list[str] = []
    unsigned_commits: list[str] = []
    subject_mismatches: list[str] = []
    for line in raw.splitlines():
        if not line:
            continue
        commit, author_name, author_email, committer_name, committer_email, signature, subject = (
            line.split("\x00", 6)
        )
        record = {
            "commit": commit,
            "author": f"{author_name} <{author_email}>",
            "committer": f"{committer_name} <{committer_email}>",
            "signature": signature,
            "subject": subject,
        }
        commits.append(record)
        if author_name != EXPECTED_NAME or author_email != EXPECTED_EMAIL:
            raw_mismatches.append(f"author:{commit}")
        if committer_name != EXPECTED_NAME or committer_email != EXPECTED_EMAIL:
            raw_mismatches.append(f"committer:{commit}")
        if signature != "G":
            unsigned_commits.append(commit)
        if not commit_subject_ok(subject):
            subject_mismatches.append(commit)
    return {
        "ok": not raw_mismatches and not unsigned_commits and not subject_mismatches,
        "expected_author": EXPECTED_AUTHOR,
        "raw_mismatches": raw_mismatches,
        "unsigned_commits": unsigned_commits,
        "subject_mismatches": subject_mismatches,
        "commits": commits,
    }

from __future__ import annotations

import re
import subprocess
from pathlib import Path

EXPECTED_NAME = "Yang HENG"
EXPECTED_EMAIL = "heng.yang.ds@hotmail.com"
EXPECTED_AUTHOR = f"{EXPECTED_NAME} <{EXPECTED_EMAIL}>"
CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)(\([a-z0-9-]+\))?: .+"
)


def commit_subject_ok(subject: str) -> bool:
    return bool(CONVENTIONAL_RE.match(subject))


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def signature_policy_report(root: Path | None = None) -> dict[str, object]:
    repo = root or Path.cwd()
    name = _git(repo, "config", "--get", "user.name")
    email = _git(repo, "config", "--get", "user.email")
    gpgsign = _git(repo, "config", "--get", "commit.gpgsign")
    gpg_format = _git(repo, "config", "--get", "gpg.format")
    signing_key = _git(repo, "config", "--get", "user.signingkey")
    subject = _git(repo, "log", "-1", "--pretty=%s")
    signature = _git(repo, "log", "-1", "--pretty=%G?")
    expected_name, expected_email = EXPECTED_NAME, EXPECTED_EMAIL
    gaps: list[str] = []
    if name != expected_name:
        gaps.append("git_user_name_mismatch")
    if email != expected_email:
        gaps.append("git_user_email_mismatch")
    if gpgsign != "true":
        gaps.append("commit_signing_disabled")
    if gpg_format != "ssh":
        gaps.append("commit_signing_format_not_ssh")
    if not signing_key:
        gaps.append("commit_signing_key_missing")
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "expected_author": EXPECTED_AUTHOR,
        "configured_author": f"{name} <{email}>",
        "signing_required": True,
        "gpg_format": gpg_format,
        "signing_key": signing_key,
        "head_subject": subject,
        "head_subject_ok": commit_subject_ok(subject),
        "head_signature_status": signature,
        "head_signature_ok": signature == "G",
    }

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

# Default subject grammar is intentionally permissive: the product ships without
# imposing one house style. An adopter narrows it (e.g. to Conventional Commits or
# an imperative-mood rule) through .ethos/workspace.toml [commit_policy].
DEFAULT_SUBJECT_PATTERN = r".+"


def _subject_re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def commit_subject_ok(subject: str, *, pattern: str = DEFAULT_SUBJECT_PATTERN) -> bool:
    return bool(_subject_re(pattern).match(subject))


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def load_commit_policy(root: Path) -> dict[str, object]:
    """Read the adopter's commit policy from .ethos/workspace.toml [commit_policy].

    ETHOS is a generic product: it hardcodes no author identity or subject grammar.
    An adopter binds its own expectations (e.g. the identity its forge marks as
    Verified) through configuration; an unconfigured field means "do not enforce it".
    """
    default: dict[str, object] = {
        "expected_name": "",
        "expected_email": "",
        "subject_pattern": DEFAULT_SUBJECT_PATTERN,
        "signing_required": False,
        "signing_format": "",
    }
    path = root / ".ethos" / "workspace.toml"
    if not path.exists():
        return default
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return default
    raw = payload.get("commit_policy")
    if not isinstance(raw, dict):
        return default
    return {
        "expected_name": _str(raw.get("expected_name"), ""),
        "expected_email": _str(raw.get("expected_email"), ""),
        "subject_pattern": _str(raw.get("subject_pattern"), DEFAULT_SUBJECT_PATTERN),
        "signing_required": bool(raw.get("signing_required", False)),
        "signing_format": _str(raw.get("signing_format"), ""),
    }


def _str(value: object, fallback: str) -> str:
    return value if isinstance(value, str) else fallback


def _identity_ok(actual: str, expected: str) -> bool:
    # With a configured expectation the value must match it; without one, any
    # non-empty value self-certifies.
    return actual == expected if expected else bool(actual)


def _authorship_gaps(
    *, name: str, email: str, expected_name: str, expected_email: str
) -> list[str]:
    # A configured expected identity is enforced; otherwise the repo's own git
    # identity self-certifies, and only its presence is required. Both the mismatch
    # and the missing-identity failures reduce to the same governance gap so the
    # kernel taxonomy classifies them under one node.
    gaps: list[str] = []
    if not _identity_ok(name, expected_name):
        gaps.append("git_user_name_mismatch")
    if not _identity_ok(email, expected_email):
        gaps.append("git_user_email_mismatch")
    return gaps


def _signing_gaps(
    *, gpgsign: str, gpg_format: str, signing_key: str, expected_format: str
) -> list[str]:
    gaps: list[str] = []
    if gpgsign != "true":
        gaps.append("commit_signing_disabled")
    if expected_format and gpg_format != expected_format:
        gaps.append("commit_signing_format_mismatch")
    if not signing_key:
        gaps.append("commit_signing_key_missing")
    return gaps


def signature_policy_report(root: Path | None = None) -> dict[str, object]:
    repo = root or Path.cwd()
    policy = load_commit_policy(repo)
    expected_name = str(policy["expected_name"])
    expected_email = str(policy["expected_email"])
    subject_pattern = str(policy["subject_pattern"])
    signing_required = bool(policy["signing_required"])
    expected_format = str(policy["signing_format"])

    name = _git(repo, "config", "--get", "user.name")
    email = _git(repo, "config", "--get", "user.email")
    gpgsign = _git(repo, "config", "--get", "commit.gpgsign")
    gpg_format = _git(repo, "config", "--get", "gpg.format")
    signing_key = _git(repo, "config", "--get", "user.signingkey")
    subject = _git(repo, "log", "-1", "--pretty=%s")
    signature = _git(repo, "log", "-1", "--pretty=%G?")

    gaps = _authorship_gaps(
        name=name, email=email, expected_name=expected_name, expected_email=expected_email
    )
    if signing_required:
        gaps.extend(
            _signing_gaps(
                gpgsign=gpgsign,
                gpg_format=gpg_format,
                signing_key=signing_key,
                expected_format=expected_format,
            )
        )

    expected_author = f"{expected_name} <{expected_email}>" if expected_name else ""
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "expected_author": expected_author,
        "configured_author": f"{name} <{email}>",
        "signing_required": signing_required,
        "gpg_format": gpg_format,
        "signing_key": signing_key,
        "head_subject": subject,
        "head_subject_ok": commit_subject_ok(subject, pattern=subject_pattern),
        "head_signature_status": signature,
        "head_signature_ok": signature == "G",
    }

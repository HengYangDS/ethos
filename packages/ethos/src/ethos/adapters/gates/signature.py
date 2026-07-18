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
        "allowed_identities": [],
        "identity_mode": "presence",
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
    identities = _identity_entries(raw.get("allowed_identities"))
    identity_mode = _str(raw.get("identity_mode"), "")
    if not identity_mode:
        identity_mode = "allowlist" if identities else "presence"
    return {
        "expected_name": _str(raw.get("expected_name"), ""),
        "expected_email": _str(raw.get("expected_email"), ""),
        "allowed_identities": identities,
        "identity_mode": identity_mode,
        "subject_pattern": _str(raw.get("subject_pattern"), DEFAULT_SUBJECT_PATTERN),
        "signing_required": bool(raw.get("signing_required", False)),
        "signing_format": _str(raw.get("signing_format"), ""),
    }


def _str(value: object, fallback: str) -> str:
    return value if isinstance(value, str) else fallback


def _identity_entries(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    entries: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "role": _str(item.get("role"), ""),
                "name": _str(item.get("name"), ""),
                "email": _str(item.get("email"), ""),
            }
        )
    return entries


def _policy_allowed_identities(policy: dict[str, object]) -> list[dict[str, str]]:
    return _identity_entries(policy.get("allowed_identities"))


def _matches_allowed_identity(
    *, name: str, email: str, allowed_identities: list[dict[str, str]]
) -> bool:
    return any(
        name == identity.get("name", "") and email == identity.get("email", "")
        for identity in allowed_identities
    )


def _authorship_gaps(
    *,
    actual_identity: tuple[str, str],
    expected_identity: tuple[str, str],
    allowed_identities: list[dict[str, str]],
    identity_mode: str,
) -> list[str]:
    # Legacy adopter configs may still set a single expected identity; when they
    # do, preserve exact matching for backwards compatibility. New product
    # configs use role-based identity modes so authority is not a single author.
    name, email = actual_identity
    expected_name, expected_email = expected_identity
    gaps: list[str] = []
    if expected_name or expected_email:
        if name != expected_name:
            gaps.append("git_user_name_mismatch")
        if email != expected_email:
            gaps.append("git_user_email_mismatch")
        return gaps
    if not name:
        gaps.append("git_user_name_mismatch")
    if not email:
        gaps.append("git_user_email_mismatch")
    if (
        name
        and email
        and identity_mode == "allowlist"
        and allowed_identities
        and not _matches_allowed_identity(
            name=name, email=email, allowed_identities=allowed_identities
        )
    ):
        gaps.append("git_identity_not_allowed")
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
    allowed_identities = _policy_allowed_identities(policy)
    identity_mode = str(policy.get("identity_mode", "presence"))
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
        actual_identity=(name, email),
        expected_identity=(expected_name, expected_email),
        allowed_identities=allowed_identities,
        identity_mode=identity_mode,
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
    allowed_roles = sorted(
        {
            str(identity.get("role", ""))
            for identity in allowed_identities
            if isinstance(identity, dict)
        }
    )
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "expected_author": expected_author,
        "allowed_identity_count": len(allowed_identities),
        "allowed_identity_roles": allowed_roles,
        "configured_identity_allowed": not any(gap.startswith("git_identity") for gap in gaps),
        "identity_mode": identity_mode,
        "configured_author": f"{name} <{email}>",
        "signing_required": signing_required,
        "gpg_format": gpg_format,
        "signing_key": signing_key,
        "head_subject": subject,
        "head_subject_ok": commit_subject_ok(subject, pattern=subject_pattern),
        "head_signature_status": signature,
        "head_signature_ok": signature == "G",
    }

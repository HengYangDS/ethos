"""Push-range Git identity admission — the configured-user commit-identity check.

Split out of admission.core to keep each admission module a cohesive, bounded unit:
this is the self-contained "who authored the pushed commits" policy (opt-in via
`ethos.pushIdentityPolicy = configured-user`), used only by push_admission_report. It
touches git plumbing (config / cat-file / rev-list / show) and nothing else in the
admission surface.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

_COMMIT_IDENTITY_FIELDS = (
    "author_name",
    "author_email",
    "committer_name",
    "committer_email",
)


def _git(root: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=False, text=text, capture_output=True)


def commit_contained_in(root: Path, commit: str, branch: str) -> bool:
    """Return whether `commit` is already contained in `branch`.

    A candidate move to a commit the accepted branch already contains is a
    refresh-from-accepted rewind (or a no-op): it re-points candidate at already-accepted,
    already-proven truth and promotes nothing, so the candidate proof precondition does not
    apply. Missing branch or any git error → False (fall back to requiring proof — safe).
    """
    return _git(root, "merge-base", "--is-ancestor", commit, branch).returncode == 0


def _git_config(root: Path, key: str) -> str:
    return _git(root, "config", "--get", key, text=True).stdout.strip()


def _commit_exists(root: Path, revision: str) -> bool:
    if not revision or revision == "0" * 40:
        return False
    return _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode == 0


def _pushed_commit_range(root: Path, *, pushed_head: str, remote_head: str) -> list[str]:
    if not _commit_exists(root, pushed_head):
        return []
    revspec = pushed_head
    if _commit_exists(root, remote_head):
        revspec = f"{remote_head}..{pushed_head}"
    completed = _git(root, "rev-list", revspec, text=True)
    if completed.returncode != 0:
        return []
    return completed.stdout.splitlines()


def _pushed_commit_range_excluding(
    root: Path, *, pushed_head: str, trusted_baselines: tuple[str, ...]
) -> list[str]:
    """List only commits absent from every explicitly trusted baseline."""
    if not _commit_exists(root, pushed_head):
        return []
    completed = _git(root, "rev-list", pushed_head, "--not", *trusted_baselines, text=True)
    return completed.stdout.splitlines() if completed.returncode == 0 else []


def _commit_identity(root: Path, revision: str) -> dict[str, str]:
    completed = _git(root, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", revision, text=True)
    parts = completed.stdout.rstrip("\n").split("\x00")
    if completed.returncode == 0 and len(parts) == len(_COMMIT_IDENTITY_FIELDS):
        return dict(zip(_COMMIT_IDENTITY_FIELDS, parts, strict=True))
    return dict.fromkeys(_COMMIT_IDENTITY_FIELDS, "")


def _identity_range_base(
    root: Path,
    *,
    pushed_head: str,
    remote_head: str,
    trusted_baseline: str,
) -> tuple[str, bool, list[str]]:
    if remote_head != "0" * 40 or not trusted_baseline:
        return remote_head, True, []
    if not _commit_exists(root, trusted_baseline):
        return "", False, [f"push_identity_submit_baseline_missing:{trusted_baseline}"]
    if not _commit_exists(root, pushed_head) or commit_contained_in(
        root, trusted_baseline, pushed_head
    ):
        return trusted_baseline, True, []
    return "", False, [f"push_identity_submit_baseline_not_ancestor:{trusted_baseline}"]


def reconciliation_receipt_payload(
    *, submit_branch: str, source_head: str, origin_head: str, github_head: str
) -> dict[str, object]:
    """Build the deterministic, non-authorizing dual-remote observation payload."""
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "submit-reconciliation",
        "submit_branch": submit_branch,
        "source_head": source_head,
        "origin_ref": "origin/dev",
        "origin_head": origin_head,
        "github_ref": "github/dev",
        "github_head": github_head,
        "mints_authority": False,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {**payload, "payload_digest": hashlib.sha256(encoded).hexdigest()}


def _read_reconciliation_receipt(path: str) -> dict[str, object] | None:
    if not path:
        return None
    try:
        payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _reconciliation_baselines(
    root: Path,
    *,
    pushed_head: str,
    submit_branch: str,
    primary_baseline: str,
    reconciliation_receipt_path: str,
    observed_origin_head: str,
    observed_github_head: str,
) -> tuple[tuple[str, ...], list[str]]:
    """Read one exact receipt; it scopes history but never grants mutation authority."""
    if not submit_branch or not _commit_exists(root, pushed_head):
        return (), []
    if _commit_exists(root, primary_baseline) and commit_contained_in(
        root, primary_baseline, pushed_head
    ):
        return (), []
    if not reconciliation_receipt_path:
        return (), ["push_identity_reconciliation_receipt_required"]
    receipt = _read_reconciliation_receipt(reconciliation_receipt_path)
    if receipt is None:
        return (), ["push_identity_reconciliation_receipt_invalid"]
    expected = reconciliation_receipt_payload(
        submit_branch=submit_branch,
        source_head=pushed_head,
        origin_head=str(receipt.get("origin_head") or ""),
        github_head=str(receipt.get("github_head") or ""),
    )
    gaps: list[str] = []
    for field, expected_value in expected.items():
        if receipt.get(field) != expected_value:
            gaps.append(f"push_identity_reconciliation_receipt_{field}_mismatch")
    origin_head = str(receipt.get("origin_head") or "")
    github_head = str(receipt.get("github_head") or "")
    if observed_origin_head != origin_head:
        gaps.append("push_identity_reconciliation_origin_head_stale")
    if observed_github_head != github_head:
        gaps.append("push_identity_reconciliation_github_head_stale")
    missing = [head for head in (origin_head, github_head) if not _commit_exists(root, head)]
    if missing:
        gaps.extend(f"push_identity_reconciliation_baseline_missing:{head}" for head in missing)
    return (origin_head, github_head) if not gaps else (), gaps


def push_identity_policy_report(
    root: Path,
    pushed_head: str,
    remote_head: str = "",
    trusted_baseline: str = "",
    reconciliation_submit_branch: str = "",
    reconciliation_receipt_path: str = "",
    observed_origin_head: str = "",
    observed_github_head: str = "",
) -> dict[str, object]:
    """Report optional push-range Git identity admission.

    The mechanism is intentionally repository-local and opt-in: ETHOS remains
    organization-native and does not hardcode a product author. Repositories that
    need a canonical forge identity enable ``ethos.pushIdentityPolicy`` in local or
    repo config. ``configured-user`` means every newly pushed commit must have both
    author and committer equal to the checkout's configured ``user.name`` and
    ``user.email``.
    """
    mode = _git_config(root, "ethos.pushIdentityPolicy")
    if mode != "configured-user":
        return {
            "ok": True,
            "mode": mode or "disabled",
            "expected_identity": "",
            "checked_commit_count": 0,
            "violations": [],
            "required_gaps": [],
        }
    expected_name = _git_config(root, "user.name")
    expected_email = _git_config(root, "user.email")
    expected_identity = (
        f"{expected_name} <{expected_email}>" if expected_name or expected_email else ""
    )
    gaps: list[str] = []
    violations: list[dict[str, str]] = []
    if not expected_name:
        gaps.append("push_identity_user_name_missing")
    if not expected_email:
        gaps.append("push_identity_user_email_missing")
    head_exists = _commit_exists(root, pushed_head)
    trusted_reconciliation_baselines, reconciliation_gaps = _reconciliation_baselines(
        root,
        pushed_head=pushed_head,
        submit_branch=reconciliation_submit_branch,
        primary_baseline=trusted_baseline,
        reconciliation_receipt_path=reconciliation_receipt_path,
        observed_origin_head=observed_origin_head,
        observed_github_head=observed_github_head,
    )
    range_base, range_is_trusted, baseline_gaps = _identity_range_base(
        root,
        pushed_head=pushed_head,
        remote_head=remote_head,
        trusted_baseline=trusted_baseline,
    )
    gaps.extend(reconciliation_gaps)
    if not trusted_reconciliation_baselines:
        gaps.extend(baseline_gaps)
    commits = (
        _pushed_commit_range_excluding(
            root,
            pushed_head=pushed_head,
            trusted_baselines=trusted_reconciliation_baselines,
        )
        if trusted_reconciliation_baselines
        else (
            _pushed_commit_range(root, pushed_head=pushed_head, remote_head=range_base)
            if head_exists and range_is_trusted
            else []
        )
    )
    if pushed_head and not head_exists:
        gaps.append("push_identity_commit_range_unreadable")
    for commit in commits:
        identity = _commit_identity(root, commit)
        author_ok = (
            identity["author_name"] == expected_name and identity["author_email"] == expected_email
        )
        committer_ok = (
            identity["committer_name"] == expected_name
            and identity["committer_email"] == expected_email
        )
        if author_ok and committer_ok:
            continue
        violation = {
            "commit": commit,
            "author": f"{identity['author_name']} <{identity['author_email']}>",
            "committer": f"{identity['committer_name']} <{identity['committer_email']}>",
        }
        violations.append(violation)
        if not author_ok:
            gaps.append(f"pushed_commit_author_not_configured_identity:{commit}")
        if not committer_ok:
            gaps.append(f"pushed_commit_committer_not_configured_identity:{commit}")
    return {
        "ok": not gaps,
        "mode": mode,
        "expected_identity": expected_identity,
        "checked_commit_count": len(commits),
        "violations": violations,
        "required_gaps": gaps,
    }

"""Push-range Git identity admission — the configured-user commit-identity check.

Split out of admission.core to keep each admission module a cohesive, bounded unit:
this is the self-contained "who authored the pushed commits" policy (opt-in via
`ethos.pushIdentityPolicy = configured-user`), used only by push_admission_report. It
touches git plumbing (config / cat-file / rev-list / show) and nothing else in the
admission surface.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_COMMIT_IDENTITY_FIELDS = ("author_name", "author_email", "committer_name", "committer_email")


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


def push_identity_policy_report(
    root: Path, pushed_head: str, remote_head: str = "", trusted_baseline: str = ""
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
    range_base, range_is_trusted, baseline_gaps = _identity_range_base(
        root,
        pushed_head=pushed_head,
        remote_head=remote_head,
        trusted_baseline=trusted_baseline,
    )
    gaps.extend(baseline_gaps)
    commits = (
        _pushed_commit_range(root, pushed_head=pushed_head, remote_head=range_base)
        if head_exists and range_is_trusted
        else []
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

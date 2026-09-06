"""Configured Git identity admission for newly pushed commits."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import observe_commit

if TYPE_CHECKING:
    from pathlib import Path

_ZERO = "0" * 40


def _git(root: Path, *args: str):
    return run_git(root, *args, check=False)


def commit_contained_in(root: Path, commit: str, branch: str) -> bool:
    """Return whether Git proves commit is contained in branch."""
    return _git(root, "merge-base", "--is-ancestor", commit, branch).returncode == 0


def _exists(root: Path, revision: str) -> bool:
    return (
        bool(revision and revision != _ZERO)
        and _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode == 0
    )


def _pushed_commit_range(
    root: Path, *, pushed_head: str, remote_head: str
) -> tuple[list[str], bool]:
    if not _exists(root, pushed_head):
        return [], False
    revision = f"{remote_head}..{pushed_head}" if _exists(root, remote_head) else pushed_head
    result = _git(root, "rev-list", revision)
    return (result.stdout.splitlines(), True) if result.returncode == 0 else ([], False)


def _range_base(root: Path, pushed: str, remote: str, trusted: str) -> tuple[str, list[str]]:
    if remote != _ZERO or not trusted:
        return remote, []
    if not _exists(root, trusted):
        return "", [f"push_identity_proposal_baseline_missing:{trusted}"]
    if not _exists(root, pushed) or commit_contained_in(root, trusted, pushed):
        return trusted, []
    return "", [f"push_identity_proposal_baseline_not_ancestor:{trusted}"]


def push_identity_policy_report(
    root: Path,
    pushed_head: str,
    remote_head: str = "",
    trusted_baseline: str = "",
) -> dict[str, object]:
    """Require configured author and committer identity for newly pushed commits."""
    mode = _git(root, "config", "--get", "ethos.pushIdentityPolicy").stdout.strip()
    if mode != "configured-user":
        return {
            "verdict": "pass",
            "mode": mode or "disabled",
            "expected_identity": "",
            "checked_commit_count": 0,
            "violations": [],
            "required_gaps": [],
        }
    name = _git(root, "config", "--get", "user.name").stdout.strip()
    email = _git(root, "config", "--get", "user.email").stdout.strip()
    gaps = [
        gap
        for value, gap in (
            (name, "push_identity_user_name_missing"),
            (email, "push_identity_user_email_missing"),
        )
        if not value
    ]
    head_exists = _exists(root, pushed_head)
    range_base, baseline_gaps = _range_base(root, pushed_head, remote_head, trusted_baseline)
    gaps.extend(baseline_gaps)
    commits, range_readable = (
        _pushed_commit_range(root, pushed_head=pushed_head, remote_head=range_base)
        if head_exists and not baseline_gaps
        else ([], True)
    )
    if pushed_head and (not head_exists or not range_readable):
        gaps.append("push_identity_commit_range_unreadable")
    violations = []
    for commit in commits:
        observation = observe_commit(root, commit)
        author = cast("dict[str, str]", observation["author"])
        committer = cast("dict[str, str]", observation["committer"])
        author_ok = (author["name"], author["email"]) == (name, email)
        committer_ok = (committer["name"], committer["email"]) == (name, email)
        if author_ok and committer_ok:
            continue
        violations.append(
            {
                "commit": commit,
                "author": f"{author['name']} <{author['email']}>",
                "committer": f"{committer['name']} <{committer['email']}>",
            }
        )
        if not author_ok:
            gaps.append(f"pushed_commit_author_not_configured_identity:{commit}")
        if not committer_ok:
            gaps.append(f"pushed_commit_committer_not_configured_identity:{commit}")
    return {
        "verdict": "block" if gaps else "pass",
        "mode": mode,
        "expected_identity": f"{name} <{email}>" if name or email else "",
        "checked_commit_count": len(commits),
        "violations": violations,
        "required_gaps": gaps,
    }

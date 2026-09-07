"""Configured Git identity admission for newly pushed commits."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import observe_commit

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *args: str):
    return run_git(root, *args, check=False)


def push_identity_policy_report(
    root: Path,
    revisions: tuple[str, ...],
) -> dict[str, object]:
    """Require configured identity for one already-derived commit sequence."""
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
    violations = []
    checked_commit_count = 0
    for commit in revisions:
        observation = observe_commit(root, commit)
        observation_gaps = [
            str(gap) for gap in cast("list[object]", observation.get("required_gaps", []))
        ]
        if observation_gaps:
            gap = f"push_identity_commit_unreadable:{commit}"
            gaps.append(gap)
            violations.append(
                {"commit": commit, "author": "", "committer": "", "required_gaps": [gap]}
            )
            continue
        checked_commit_count += 1
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
                "required_gaps": [],
            }
        )
        if not author_ok:
            gap = f"pushed_commit_author_not_configured_identity:{commit}"
            gaps.append(gap)
            cast("list[str]", violations[-1]["required_gaps"]).append(gap)
        if not committer_ok:
            gap = f"pushed_commit_committer_not_configured_identity:{commit}"
            gaps.append(gap)
            cast("list[str]", violations[-1]["required_gaps"]).append(gap)
    return {
        "verdict": "block" if gaps else "pass",
        "mode": mode,
        "expected_identity": f"{name} <{email}>" if name or email else "",
        "checked_commit_count": checked_commit_count,
        "revisions": list(revisions),
        "violations": violations,
        "required_gaps": gaps,
    }

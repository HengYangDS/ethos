"""Name the proposals that an applied accepted publication absorbed on each peer it moved.

The names only lead to the existing retirement probe, which observes every fact again before any
deletion, so this listing grants nothing.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.repo.commit.conservation import accepted_contribution
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import report_verdict
from ethos.repository.paradigm.parameters import seconds

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.publication import PublicationEffect


def absorbed_proposals(
    root: Path, effect: PublicationEffect
) -> tuple[dict[str, list[str]], list[str]]:
    """Return each moved peer's proposals that the published head preserves, and unlisted peers.

    A peer counts as moved when the effect set its accepted branch; preservation is judged by the
    contribution observer that proposal retirement admits, so patch equivalence never counts.
    """
    policy = load_branch_role_policy(root)
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    namespace = f"refs/heads/{policy.proposal_branch_prefix}"
    absorbed: dict[str, list[str]] = {}
    unobserved: list[str] = []
    for target in effect.targets:
        head = next(
            (
                update.desired
                for update in target.updates
                if update.target_ref == accepted_ref and not update.deletion
            ),
            "",
        )
        if not head:
            continue
        try:
            listing = git.run_network_git(
                root, "ls-remote", target.remote, f"{namespace}*", timeout=seconds("git")
            )
        except (subprocess.TimeoutExpired, git.GitExecutionError, OSError):
            listing = None
        if listing is None or listing.returncode:
            unobserved.append(target.id)
            continue
        rows = (line.split() for line in listing.stdout.splitlines())
        refs = sorted(
            row[1]
            for row in rows
            if len(row) == 2 and row[1].startswith(namespace) and _preserved(root, row[0], head)
        )
        if refs:
            absorbed[target.id] = refs
    return absorbed, unobserved


def _preserved(root: Path, tip: str, head: str) -> bool:
    try:
        return report_verdict(accepted_contribution(root, tip, head)) == "pass"
    except (git.GitExecutionError, OSError, ValueError):
        return False

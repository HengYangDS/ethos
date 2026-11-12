"""Name the proposals that an applied accepted publication absorbed on each peer it moved.

The names only lead to the existing retirement probe, which observes every fact again before any
deletion, so this listing grants nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.publication.observation import observe_remote_namespaces
from ethos.adapters.repo.commit.conservation import accepted_contribution
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.publication import PublicationEffect


def absorbed_proposals(
    root: Path, effect: PublicationEffect
) -> tuple[dict[str, list[str]], list[str]]:
    """Return each moved peer's proposals that the published head preserves, and unlisted peers.

    A peer counts as moved when the effect set its accepted branch; preservation is judged by the
    contribution observer that proposal retirement admits, so patch equivalence never counts. The
    peer's proposal namespace is listed through the one bounded peer observer.
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
        listing = observe_remote_namespaces(root, target.remote, (f"{namespace}*",))
        if listing.failure is not None:
            unobserved.append(target.id)
            continue
        refs = sorted(
            ref
            for ref, tip in listing.refs.items()
            if ref.startswith(namespace) and _preserved(root, tip, head)
        )
        if refs:
            absorbed[target.id] = refs
    return absorbed, unobserved


def _preserved(root: Path, tip: str, head: str) -> bool:
    try:
        return report_verdict(accepted_contribution(root, tip, head)) == "pass"
    except (git.GitExecutionError, OSError, ValueError):
        return False

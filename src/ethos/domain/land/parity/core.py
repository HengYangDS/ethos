"""Parity evidence freshness reducers for product and adopter heads."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git_adapter
from ethos.repository.evidence.parity.core import PARITY_RELEVANT_PATHS

if TYPE_CHECKING:
    from pathlib import Path


def acceptable_parity_product_heads(root: Path, adopter: str | None) -> tuple[str, ...]:
    """Product heads accepted as parity-evidence-current.

    A recorded product_head is current when nothing under PARITY_RELEVANT_PATHS changed
    between it and HEAD — commits that touched only parity-irrelevant paths do not stale
    the evidence. This removes the shared-evidence-file serialization bottleneck: a lane
    that changes no parity-relevant source need not re-touch the evidence file, and an
    unrelated commit no longer forces a parity re-run.
    """
    current_head = git_adapter.current_tracked_head(root)
    if not current_head:
        return ()
    return git_adapter.commits_equivalent_over_paths(
        root, current_head, relevant_paths=PARITY_RELEVANT_PATHS
    )


def acceptable_parity_target_heads(
    root: Path,
    target: Path | None,
    adopter: str | None,
) -> tuple[str, ...]:
    """Target heads accepted as parity-evidence-current for a shadow target.

    Same parity-relevant-tree currency as the product heads, evaluated in the target's
    own history — only meaningful when the target shares this repository's history.
    """
    if target is None:
        return ()
    current_head = git_adapter.current_tracked_head(target)
    if not current_head:
        return ()
    if not git_adapter.same_git_repository(root, target):
        return (current_head,)
    return git_adapter.commits_equivalent_over_paths(
        target, current_head, relevant_paths=PARITY_RELEVANT_PATHS
    )

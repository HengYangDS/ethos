"""Derive the sole executable continuation of one Work Lane retirement."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.retirement import RetirementOperation
    from ethos.contracts.retirement import RetirementProgress

RECEIPT_INVALIDATING_GAPS = frozenset(
    {"retirement_accepted_coordinate_drift", "retirement_content_drift"}
)


def _lane(root: Path, *words: str) -> str:
    return shlex.join(["ethos", "lane", *words, "--root", root.as_posix(), "--json"])


def content_review_command(root: Path, branch: str, *, path: str = "") -> str:
    """Request an exact content review, without authorizing its eventual disposal."""
    return _lane(
        root,
        "retire",
        "abandon",
        *(("--path", path) if path else ("--branch", branch)),
        "--review-content",
        "--reason-code",
        "content-review",
        "--reason",
        "Review nontracked content and preserve required custody before disposal",
    )


def recovery_command(root: Path, receipt: Mapping[str, object]) -> str:
    """Resume the same immutable receipt; valid only while that receipt can still apply."""
    return shlex.join(
        [
            "ethos",
            "lane",
            "retire",
            "recover",
            "--receipt",
            str(receipt.get("path") or ""),
            "--receipt-sha256",
            str(receipt.get("sha256") or ""),
            "--authorize",
            "--apply",
            "--root",
            root.as_posix(),
            "--json",
        ]
    )


def _abandon(request: RetirementOperation) -> tuple[str, ...]:
    code, reason = (str(request.reason.get(key) or "") for key in ("code", "summary"))
    return (
        "retire",
        "abandon",
        "--branch",
        request.branch,
        "--reason-code",
        code,
        "--reason",
        reason,
    )


def _linked_command(root: Path, request: RetirementOperation) -> str:
    """Re-derive the same request while its worktree is still linked."""
    if request.reviewed_content:
        path = "" if request.branch else request.worktree_path
        return content_review_command(root, request.branch, path=path)
    landed = ("retire", "landed", "--branch", request.branch)
    words = {"landed": landed, "abandon": _abandon(request)}.get(request.mode, ("status",))
    return _lane(root, *words)


def _unbound_command(root: Path, request: RetirementOperation, progress: RetirementProgress) -> str:
    """Select the native unbound route once the worktree is already gone."""
    accepted = ref_head(root, request.accepted_branch)
    held = request.lease_state == "valid" and progress.observation.lease_state == "expected"
    head = ("--branch", request.branch, "--expect-head", request.head)
    reason = str(request.reason.get("summary") or "")
    words: tuple[str, ...] = ("status",)
    if accepted and "delete_ref" in progress.remaining_effects:
        if is_ancestor(root, request.head, accepted):
            if held:
                route = (*head, "--path", request.worktree_path, "--absorbed-by", accepted)
                words = ("retire", "superseded", *route, "--reason", reason)
            elif "revoke_lease" not in request.effects:
                words = ("retire", "absorbed-ref", *head, "--accepted-head", accepted)
        elif held and not is_ancestor(root, accepted, request.head):
            words = _abandon(request)
    return _lane(root, *words)


def fresh_retirement_command(
    root: Path, request: RetirementOperation, progress: RetirementProgress
) -> str:
    """Derive a new native admission for the remaining carriers from current facts."""
    if "remove_worktree" in progress.remaining_effects:
        return _linked_command(root, request)
    return _unbound_command(root, request, progress)


def retirement_continuation(
    root: Path,
    request: RetirementOperation,
    receipt: Mapping[str, object],
    progress: RetirementProgress | None,
    failure: Mapping[str, object] | None,
) -> str:
    """Return the one next action that current facts can still execute."""
    gaps = set(string_sequence((failure or {}).get("required_gaps")))
    if gaps == {"retirement_content_review_required"}:
        return content_review_command(root, request.branch)
    if progress is not None and gaps & RECEIPT_INVALIDATING_GAPS:
        try:
            return fresh_retirement_command(root, request, progress)
        except (GitExecutionError, OSError, RuntimeError, ValueError):
            return _lane(root, "status")
    if "retirement_operation_state_drift" in gaps:
        return _lane(root, "status")
    if progress is None or progress.remaining_effects:
        return recovery_command(root, receipt)
    return shlex.join(["ethos", "status", "--root", root.as_posix(), "--json"])

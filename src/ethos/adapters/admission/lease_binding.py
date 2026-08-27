"""Resolve current Work Lane authoring authority from fresh exact facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.projection import integer_value

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ethos.contracts.semantic import Commitment
    from ethos.contracts.verdict import Verdict


@dataclass(frozen=True, slots=True)
class CurrentAuthority:
    """One current Lease-bound authoring decision and its exact coordinates."""

    verdict: Verdict
    reason: str
    branch: str
    actor: str
    lease: dict[str, object]
    current_head: str
    current_tree: str
    commitment: Commitment | None
    binding_head: str = ""
    head_source: str = "head"
    required: bool = True

    def projection(self) -> dict[str, object]:
        """Project the same authority facts for readers, guards, and hooks."""
        return {
            "verdict": self.verdict,
            "required": self.required,
            "branch": self.branch,
            "holder_ref": str(self.lease.get("holder_ref") or ""),
            "invocation_holder_ref": self.actor,
            "lease_id": str(self.lease.get("lease_id") or ""),
            "epoch": integer_value(self.lease.get("epoch")),
            "expected_head": str(self.lease.get("expected_head") or ""),
            "expected_tree": str(self.lease.get("expected_tree") or ""),
            "base_commitment_path": str(self.lease.get("base_commitment_path") or ""),
            "base_commitment_bytes_sha256": str(
                self.lease.get("base_commitment_bytes_sha256") or ""
            ),
            "base_commitment_digest": str(self.lease.get("base_commitment_digest") or ""),
            "current_head": self.current_head,
            "current_tree": self.current_tree,
            "binding_head": self.binding_head or self.current_head,
            "head_source": self.head_source,
            "scope": list(self.commitment.scope) if self.commitment is not None else [],
            "reason": self.reason,
            "required_gaps": [] if self.verdict == "pass" else [self.reason],
        }


def resolve_current_authority(
    *,
    root: Path,
    branch: str,
    lease: dict[str, object],
    actor: str,
    current_head: str,
    binding_head: str = "",
    head_source: str = "head",
    required: bool = True,
    commitment_loader: Callable[..., Commitment] | None = None,
) -> CurrentAuthority:
    """Resolve the sole current authoring verdict from exact mutable facts."""
    authoritative_head = binding_head or current_head
    observed_tree = current_tree(root, authoritative_head) if authoritative_head else ""
    if not required:
        return CurrentAuthority(
            "pass",
            "not_required",
            branch,
            actor,
            lease,
            current_head,
            observed_tree,
            None,
            authoritative_head,
            head_source,
            required=False,
        )
    lease_state = str(lease.get("lease_state") or "missing")
    reason = (
        f"work_lane_lease_unknown:{branch}"
        if lease_state == "unknown"
        else f"work_lane_lease_expired:{branch}"
        if lease_state == "expired"
        else f"work_lane_missing_lease:{branch}"
        if lease_state != "valid" or not lease.get("holder_ref")
        else f"invocation_actor_missing:{branch}"
        if not actor
        else f"lease_holder_mismatch:{branch}"
        if actor != str(lease.get("holder_ref") or "")
        else f"lease_generation_missing:{branch}"
        if not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1
        else f"lease_head_stale:{branch}"
        if str(lease.get("expected_head") or "") != authoritative_head
        else f"lease_tree_stale:{branch}"
        if str(lease.get("expected_tree") or "") != observed_tree
        else ""
    )
    commitment = None
    if not reason:
        try:
            loader = commitment_loader or load_lease_bound_commitment
            commitment = loader(root, lease=lease)
        except ValueError as error:
            reason = str(error)
            if reason.startswith("lease_base_"):
                reason = f"{reason}:{branch}"
    verdict: Verdict = "unknown" if lease_state == "unknown" else "block" if reason else "pass"
    return CurrentAuthority(
        verdict,
        reason or "matched",
        branch,
        actor,
        lease,
        current_head,
        observed_tree,
        commitment,
        authoritative_head,
        head_source,
    )


def observe_current_authority(
    *,
    root: Path,
    branch: str,
    actor: str,
    required: bool,
    head_source: str = "head",
) -> CurrentAuthority:
    """Read the current Lease and Git coordinates once, then resolve authority."""
    lease = leases_by_branch(root).get(branch, {}) if required else {}
    current_head = git_stdout(root, "rev-parse", "HEAD")
    binding_head = (
        git_stdout(root, "rev-parse", "--verify", f"refs/heads/{branch}")
        if head_source == "rebase_branch_ref"
        else current_head
    )
    return resolve_current_authority(
        root=root,
        branch=branch,
        lease=lease,
        actor=actor,
        current_head=current_head,
        binding_head=binding_head,
        head_source=head_source,
        required=required,
    )

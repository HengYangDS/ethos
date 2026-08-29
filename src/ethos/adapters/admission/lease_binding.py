"""Resolve current Work Lane authoring authority from the minimal Lease relation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.projection import integer_value

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


@dataclass(frozen=True, slots=True)
class CurrentAuthority:
    """One actor-to-lane Lease decision plus fresh Git observations."""

    verdict: Verdict
    reason: str
    branch: str
    actor: str
    lease: dict[str, object]
    current_head: str
    current_tree: str
    binding_head: str = ""
    head_source: str = "head"
    required: bool = True

    def projection(self) -> dict[str, object]:
        """Project the same minimal authority for readers, guards, and hooks."""
        return {
            "verdict": self.verdict,
            "required": self.required,
            "branch": self.branch,
            "holder_ref": str(self.lease.get("holder_ref") or ""),
            "invocation_holder_ref": self.actor,
            "generation": integer_value(self.lease.get("generation")),
            "expires_at": str(self.lease.get("expires_at") or ""),
            "current_head": self.current_head,
            "current_tree": self.current_tree,
            "binding_head": self.binding_head or self.current_head,
            "head_source": self.head_source,
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
    **_retired: object,
) -> CurrentAuthority:
    """Resolve authoring solely from role, holder equality, generation, and expiry."""
    authoritative_head = binding_head or current_head
    observed_tree = current_tree(root, authoritative_head) if authoritative_head else ""
    if not required:
        return CurrentAuthority(
            verdict="pass",
            reason="not_required",
            branch=branch,
            actor=actor,
            lease=lease,
            current_head=current_head,
            current_tree=observed_tree,
            binding_head=authoritative_head,
            head_source=head_source,
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
        if integer_value(lease.get("generation")) < 1
        else ""
    )
    verdict: Verdict = "unknown" if lease_state == "unknown" else "block" if reason else "pass"
    return CurrentAuthority(
        verdict,
        reason or "matched",
        branch,
        actor,
        lease,
        current_head,
        observed_tree,
        authoritative_head,
        head_source,
    )


def observe_current_authority(
    *, root: Path, branch: str, actor: str, required: bool, head_source: str = "head"
) -> CurrentAuthority:
    """Read the minimal Lease and fresh Git coordinates once."""
    lease = leases_by_branch(root).get(branch, {}) if required else {}
    head = git_stdout(root, "rev-parse", "HEAD")
    binding = (
        git_stdout(root, "rev-parse", "--verify", f"refs/heads/{branch}")
        if head_source == "rebase_branch_ref"
        else head
    )
    return resolve_current_authority(
        root=root,
        branch=branch,
        lease=lease,
        actor=actor,
        current_head=head,
        binding_head=binding,
        head_source=head_source,
        required=required,
    )

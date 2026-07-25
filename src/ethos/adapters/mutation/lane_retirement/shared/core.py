from __future__ import annotations

import os

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.contracts.transition import TransitionRequest


def current_holder_ref() -> str:
    """Return the invocation actor without minting authority."""
    return os.environ.get("ETHOS_ACTOR", "").strip()


def retire_mutation_envelope(  # noqa: PLR0913, RUF100 - exact state-bound decision
    *,
    command: str,
    action: str,
    branch: str | None,
    expect_head: str | None,
    apply: bool,
    confirmed: bool,
    required_gaps: list[str],
    holder_ref: str = "",
    required_holder_ref: str = "",
    extra_state: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the common retirement mutation envelope."""
    holder_ref = holder_ref.strip()
    required_holder_ref = required_holder_ref.strip()
    expected = (expect_head or "").strip()
    ref = f"refs/heads/{branch}" if branch else ""
    return mutation_envelope(
        TransitionRequest(
            command=command,
            apply=apply,
            authorized=confirmed,
            expect_head=expect_head,
        ),
        action=action,
        resource=ref or branch or "work-lane",
        expected_state={
            "ref": ref,
            "head": expected,
            "invocation_holder_ref": holder_ref,
            "required_holder_ref": required_holder_ref,
            **(extra_state or {}),
        },
        verdict="allow" if not required_gaps else "block",
        required_gaps=tuple(sorted(set(required_gaps))),
        state="ready" if not required_gaps else "blocked",
        identity_basis=("exact_lease_generation" if required_holder_ref else "not_evaluated"),
        evidence_boundary="current_git_lane_and_lease_observation",
        enforcement_boundary=(
            "sqlite_generation_lock_and_git_ref_transaction"
            if required_holder_ref
            else "git_ref_and_worktree_transition"
        ),
        verifier_provenance="current_runner",
    )

"""Exact-request admission contracts.

Admission evaluates one action over current facts. It is not a truth store,
identity directory, capability grant, or reusable authorization token.
"""

from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

Verdict = Literal["allow", "block", "defer"]


class MutationSubject(BaseModel):
    """The exact action, resource, and mutable pre-state being evaluated."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    expected_state: dict[str, Any] = Field(default_factory=dict)


class DecisionBasis(BaseModel):
    """Orthogonal facts supporting a verdict; dimensions never compensate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enforcement_boundary: str = Field(min_length=1)
    identity_basis: str = Field(min_length=1)
    state_bindings: tuple[str, ...] = ()
    evidence_boundary: str = Field(min_length=1)
    verifier_provenance: str = Field(min_length=1)
    time_basis: str = Field(min_length=1)


class AdmissionDecision(BaseModel):
    """Non-reusable verdict for one fully bound mutation subject."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: Verdict
    subject: MutationSubject
    policy_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    basis: DecisionBasis
    why: tuple[str, ...] = ()
    next: tuple[str, ...] = ()
    required_gaps: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Return the public decision envelope."""
        return {
            "verdict": self.verdict,
            "subject": self.subject.model_dump(mode="json"),
            "policy_refs": list(self.policy_refs),
            "evidence_refs": list(self.evidence_refs),
            "decision_basis": self.basis.model_dump(mode="json"),
            "why": list(self.why),
            "next": list(self.next),
            "required_gaps": list(self.required_gaps),
            "mints_authority": False,
            "reusable_authorization": False,
            "recheck_required": True,
        }

    @staticmethod
    def action_preview(
        *,
        action: str,
        resource: str,
        blocked_actions: tuple[str, ...],
        why: tuple[str, ...],
    ) -> dict[str, object]:
        """Return a reader-only preview that cannot be replayed as admission."""
        if not action or not resource:
            raise ValueError("action preview requires action and resource")  # noqa: EM101, RUF100, TRY003 - machine-readable gap token is the exception contract
        return {
            "candidate_actions": [action],
            "blocked_actions": list(blocked_actions),
            "why": list(why),
            "mints_authority": False,
            "recheck_required": True,
        }

"""Exact-request admission contracts.

Admission evaluates one action over current facts. It is not a truth store,
identity directory, capability grant, or reusable authorization token.
"""

from __future__ import annotations

import os
from typing import Annotated
from typing import Any
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field

Verdict = Literal["allow", "block", "defer"]
_PATH_REQUIRED = "path-bound admission request fields require a filesystem path"


def _path_text(value: object) -> str:
    """Normalize one filesystem path-like value into the portable request form."""
    if isinstance(value, str):
        return value
    if isinstance(value, os.PathLike):
        return os.fspath(cast("os.PathLike[str]", value))
    raise ValueError(_PATH_REQUIRED)


FilesystemPath = Annotated[str, BeforeValidator(_path_text)]


class HookAdmissionRequest(BaseModel):
    """One hook-layer admission request bound to its exact local context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root: FilesystemPath
    layer: str
    paths: tuple[FilesystemPath, ...] = ()
    editor_root: FilesystemPath | None = None
    require_editor_root: bool = False
    command: str = ""
    expected_root: FilesystemPath | None = None


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
            msg = "action preview requires action and resource"
            raise ValueError(msg)
        return {
            "candidate_actions": [action],
            "blocked_actions": list(blocked_actions),
            "why": list(why),
            "mints_authority": False,
            "recheck_required": True,
        }

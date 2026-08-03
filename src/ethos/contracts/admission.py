"""Exact-request admission contracts.

Admission evaluates one action over current facts. It is not a truth store,
identity directory, capability grant, or reusable authorization token.
"""

import os
from typing import Annotated
from typing import Any
from typing import Self
from typing import cast

from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

_PATH_REQUIRED = "path-bound admission request fields require a filesystem path"
READONLY_ROOT_COMMANDS = frozenset({"plan", "status"})
MUTATING_COMMAND_FLAGS = frozenset({"--apply", "--authorize", "--execute"})
_MUTATING_COMMANDS = frozenset(
    {
        ("ethos", "adopt"),
        ("ethos", "land"),
        ("ethos", "publish"),
        ("openspec", "archive"),
    }
)


def _mutation_flag_present(arguments: list[str] | tuple[str, ...]) -> bool:
    return any(
        argument == flag or argument.startswith(f"{flag}=")
        for argument in arguments
        for flag in MUTATING_COMMAND_FLAGS
    )


def root_command(arguments: list[str] | tuple[str, ...]) -> str:
    """Return the root command without mistaking an option value for it."""
    skip_value = False
    for argument in arguments:
        if skip_value:
            skip_value = False
        elif argument == "--root":
            skip_value = True
        elif not argument.startswith("-"):
            return argument
    return ""


def ethos_command_is_readonly(command: list[str] | tuple[str, ...]) -> bool:
    """Return whether one argv vector invokes an admitted ETHOS reader."""
    return (
        bool(command)
        and command[0].rsplit("/", maxsplit=1)[-1] == "ethos"
        and root_command(command[1:]) in READONLY_ROOT_COMMANDS
        and not _mutation_flag_present(command)
    )


def ethos_command_mutates(command: list[str] | tuple[str, ...]) -> bool:
    """Return whether one argv vector explicitly requests an ETHOS effect."""
    executable = command[0].rsplit("/", maxsplit=1)[-1] if command else ""
    return (
        _mutation_flag_present(command)
        or (
            executable,
            root_command(command[1:]),
        )
        in _MUTATING_COMMANDS
    )


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

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: FilesystemPath
    layer: str
    paths: FrozenTuple[FilesystemPath] = ()
    editor_root: FilesystemPath | None = None
    require_editor_root: bool = False
    command: str = ""
    expected_root: FilesystemPath | None = None


class MutationSubject(BaseModel):
    """The exact action, resource, and mutable pre-state being evaluated."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    expected_state: JsonObject = Field(default_factory=dict, validate_default=True)


class DecisionBasis(BaseModel):
    """Orthogonal facts supporting a verdict; dimensions never compensate."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    enforcement_boundary: str = Field(min_length=1)
    identity_basis: str = Field(min_length=1)
    state_bindings: tuple[str, ...] = ()
    evidence_boundary: str = Field(min_length=1)
    verifier_provenance: str = Field(min_length=1)
    time_basis: str = Field(min_length=1)


class AdmissionDecision(BaseModel):
    """Non-reusable verdict for one fully bound mutation subject."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    verdict: Verdict
    subject: MutationSubject
    policy_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    basis: DecisionBasis
    why: tuple[str, ...] = ()
    next_action: str = ""
    required_gaps: tuple[str, ...] = ()

    @model_validator(mode="after")
    def reject_false_pass(self) -> Self:
        require_closed_verdict(self.verdict, self.required_gaps)
        return self

    def to_payload(self) -> dict[str, Any]:
        """Return the public decision envelope."""
        return {
            "verdict": self.verdict,
            "subject": self.subject.model_dump(mode="json"),
            "policy_refs": list(self.policy_refs),
            "evidence_refs": list(self.evidence_refs),
            "decision_basis": self.basis.model_dump(mode="json"),
            "why": list(self.why),
            "next_action": self.next_action,
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
        """Return a reader-only preview that cannot authorize admission."""
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

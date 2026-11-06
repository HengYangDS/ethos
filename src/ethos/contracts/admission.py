"""Exact-request admission contracts.

Admission evaluates one action over current facts. It is not a truth store,
identity directory, capability grant, or reusable authorization token.
"""

import os
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Self
from typing import cast
from typing import get_args

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


# What one ETHOS step does, ordered from the least to the most consequential effect.
StepEffect = Literal[
    "read",
    "remote-read",
    "execute",
    "local-evidence-write",
    "local-write",
    "host-write",
    "remote-write",
    "opaque",
]
STEP_EFFECTS: tuple[StepEffect, ...] = get_args(StepEffect)
# The authority a step's argv carries, from none to a person's decision.
StepAuthorization = Literal[
    "none", "apply", "authorize", "confirm-irreversible", "attestation", "human"
]
# The strongest authority token in an argv names its kind; a person decides the rest.
_AUTHORITY_TOKENS: tuple[tuple[str, StepAuthorization], ...] = (
    ("--authorization", "attestation"),
    ("--confirm-irreversible", "confirm-irreversible"),
    ("--authorize", "authorize"),
    ("--apply", "apply"),
)
# Hook admission admits only root readers; a step also reads when it names a lane reader.
_READ_COMMAND_PATHS = frozenset({*((name,) for name in READONLY_ROOT_COMMANDS), ("lane", "status")})
_REMOTE_ROOT_COMMANDS = frozenset({"publish"})
_Row = tuple[tuple[str, ...], frozenset[str]]


def _rows(*shapes: str) -> tuple[_Row, ...]:
    """Read `path words: tokens` shapes; a row matches a path prefix with every token present."""
    rows = (shape.partition(":") for shape in shapes)
    return tuple((tuple(path.split()), frozenset(tokens.split())) for path, _sep, tokens in rows)


# A command that runs a caller's command cannot see that command's effects.
_OPAQUE = _rows("host run", "mcp")
_TOKENLESS_WRITES = _rows("hook install", "land: --closeout")
_HOST_WRITES = _rows(
    "hook install",
    "hook retire-supply: --apply",
    "lane start: --apply",
    "lane candidate: --apply",
    "adopt: --select-runtime --apply",
)
# Each shape selects the deletion of something it does not recreate. Cleanup that another
# operation performs under a liveness check is not counted; that operation reports it.
_DESTRUCTIVE = _rows(
    "lane retire abandon: --receipt --receipt-sha256 --apply --authorize",
    "lane retire recover: --receipt --receipt-sha256 --apply --authorize",
    "lane retire superseded: --apply --authorize",
    "lane retire landed: --apply --authorize",
    "lane retire absorbed-ref: --apply --authorize --confirm-irreversible",
    "lane housekeeping: --apply --authorize",
    "lane handoff revoke-source: --apply",
    "lane candidate: --refresh-from-accepted --apply --authorize --confirm-irreversible",
    "publish: --retire --apply --authorize",
    "attestation release: --apply",
    "adopt: --exit --apply --authorize --expect-head --expect-plan-digest",
    "land: --retag --apply --authorize",
    "hook retire-supply: --apply --authorize --expect-plan",
    "hook install: --reset-state --authorize",
)


def ethos_command_path(arguments: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Return up to three command words of one ETHOS argv, never an option value."""
    words: list[str] = []
    skip_value = False
    for argument in arguments[1:]:
        if skip_value:
            skip_value = False
        elif argument == "--root":
            skip_value = True
        elif argument.startswith("-"):
            if words:
                break
        elif len(words) == 3:
            break
        else:
            words.append(argument)
    return tuple(words)


def _flags(arguments: list[str] | tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        argument.partition("=")[0] for argument in arguments if argument.startswith("--")
    )


def _matched(arguments: list[str] | tuple[str, ...], rows: tuple[_Row, ...]) -> bool:
    path, flags = ethos_command_path(arguments), _flags(arguments)
    return any(path[: len(words)] == words and tokens <= flags for words, tokens in rows)


def ethos_step_effects(arguments: list[str] | tuple[str, ...]) -> tuple[StepEffect, ...]:
    """Return what one ETHOS argv does, from the least to the most consequential effect."""
    if _matched(arguments, _OPAQUE):
        return ("execute", "opaque")
    path = ethos_command_path(arguments)
    flags = _flags(arguments)
    if path in _READ_COMMAND_PATHS and not flags & MUTATING_COMMAND_FLAGS:
        return ("read",)
    remote = bool(path) and path[0] in _REMOTE_ROOT_COMMANDS
    writes = bool(flags & {"--apply", "--authorize"}) or _matched(arguments, _TOKENLESS_WRITES)
    present = {
        "remote-read": remote,
        "execute": "--execute" in flags,
        "local-evidence-write": True,
        "local-write": writes and not remote,
        "host-write": _matched(arguments, _HOST_WRITES),
        "remote-write": writes and remote,
    }
    return tuple(effect for effect in STEP_EFFECTS if present.get(effect, False))


def ethos_step_authorization(
    arguments: list[str] | tuple[str, ...], effects: tuple[StepEffect, ...]
) -> StepAuthorization:
    """Name the strongest authority token in one argv; an opaque step needs a person."""
    if "opaque" in effects:
        return "human"
    flags = _flags(arguments)
    return next((kind for token, kind in _AUTHORITY_TOKENS if token in flags), "none")


def ethos_step_destructive(
    arguments: list[str] | tuple[str, ...], effects: tuple[StepEffect, ...]
) -> bool:
    """Return whether one argv selects the deletion of something it does not recreate."""
    return "opaque" in effects or _matched(arguments, _DESTRUCTIVE)


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


class RepositoryIdentityTransition(BaseModel):
    """One explicit identity edge bound to a native ref program and object database."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    operation: Literal["repository.identity-transition"] = "repository.identity-transition"
    target_ref: str = Field(min_length=1)
    expected_head: str = Field(min_length=1)
    expected_tree: str = Field(min_length=1)
    desired_head: str = Field(min_length=1)
    desired_tree: str = Field(min_length=1)
    old_identity: str = Field(min_length=1)
    new_identity: str = Field(min_length=1)
    common_directory: FilesystemPath
    common_device: int
    common_inode: int

    @model_validator(mode="after")
    def require_distinct_identities(self) -> Self:
        """Identity equivalence must never be inferred from storage continuity."""
        if self.old_identity == self.new_identity:
            message = "repository_identity_transition_not_required"
            raise ValueError(message)
        return self


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

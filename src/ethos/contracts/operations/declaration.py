"""How a command declares its request and the operations its selectors choose between.

An operation names the selector predicates that choose it, the other fields it takes and what
running it does. A request selects the one operation whose predicates its set fields satisfy, and a
field that operation does not take refuses, so every transport refuses the same requests alike. A
field that many requests take is one `Annotated` type, and each request lists the fields it takes.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Annotated
from typing import Any
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.contracts.admission import StepAuthorization
from ethos.contracts.admission import StepEffect

# A boolean selector is `true` or `false`; any other selector is `set` or `unset`.
Predicate = Literal["true", "false", "set", "unset"]
# `observe` exits 0 on every verdict; `verdict` exits 0 only when the verdict passes; `process`
# exits with the child's status that `data.exit_status` carries, and prints no frame.
ExitKind = Literal["observe", "verdict", "process"]
_HOLDS = frozenset({"true", "set"})
_PREVIEWED = "read local-evidence-write"
# The fields that recur across requests, each one type with its help text.
Apply = Annotated[
    bool, Field(kw_only=True, description="Apply the selected operation instead of previewing it.")
]
Authorize = Annotated[bool, Field(kw_only=True, description="Authorize the selected operation.")]
Reason = Annotated[str, Field(kw_only=True, description="Why the operation is requested.")]


class CommandRequest(BaseModel):
    """One command's request: every field any of its operations reads, keyword-only."""

    model_config = ConfigDict(frozen=True, extra="forbid", defer_build=True)


def described(default: object, description: str) -> Any:
    """Declare one keyword-only request field with the help text every transport shows.

    A default of `...` makes the field one that every request sets.
    """
    return Field(default=default, kw_only=True, description=description)


def switch(description: str) -> Any:
    """Declare one keyword-only boolean request field, unset by default."""
    return Field(default=False, kw_only=True, description=description)


@dataclass(frozen=True, slots=True)
class Operation:
    """One mode of a command: what selects it, the fields it takes and what running it does."""

    id: str
    summary: str
    selectors: tuple[tuple[str, Predicate], ...]
    request: frozenset[str]
    effects: tuple[StepEffect, ...]
    authorization: StepAuthorization = "none"
    destructive: bool = False
    exit: ExitKind = "observe"
    # Formation binds a target that does not exist yet instead of the containing worktree.
    creates_root: bool = False

    @property
    def accepted(self) -> frozenset[str]:
        """Every field this operation takes: its selectors and its request fields."""
        return self.request | {name for name, _want in self.selectors}

    def failed(self, present: frozenset[str]) -> tuple[str, ...]:
        """Return each predicate that the set fields fail, as `field=predicate`."""
        return tuple(
            f"{name}={want}"
            for name, want in self.selectors
            if (name in present) != (want in _HOLDS)
        )


def operation(
    identity: str,
    summary: str,
    *,
    select: str,
    request: str = "",
    effects: str,
    authorization: StepAuthorization = "none",
    destructive: bool = False,
    exit_kind: ExitKind = "observe",
    creates_root: bool = False,
) -> Operation:
    """Declare one operation from `field=predicate` selectors and space-separated names."""
    selectors = tuple(item.partition("=") for item in select.split())
    return Operation(
        id=identity,
        summary=summary,
        selectors=tuple((name, cast("Predicate", want)) for name, _sep, want in selectors),
        request=frozenset(request.split()),
        effects=cast("tuple[StepEffect, ...]", tuple(effects.split())),
        authorization=authorization,
        destructive=destructive,
        exit=exit_kind,
        creates_root=creates_root,
    )


def modes(
    identity: str,
    preview: str,
    apply: str,
    *,
    request: str,
    authorization: StepAuthorization = "apply",
    destructive: bool = False,
    preview_exit: ExitKind = "observe",
    writes: str = "local-write",
) -> tuple[Operation, Operation]:
    """Declare a command's preview and its apply, which `apply` selects and adds its writes to.

    Both take the request fields; an apply authorized by `--authorize` also takes `authorize`.
    """
    authorized = f"authorize {request}" if authorization == "authorize" else request
    return (
        operation(
            f"{identity}.preview",
            preview,
            select="apply=false",
            request=request,
            effects=_PREVIEWED,
            exit_kind=preview_exit,
        ),
        operation(
            f"{identity}.apply",
            apply,
            select="apply=true",
            request=authorized,
            effects=f"{_PREVIEWED} {writes}",
            authorization=authorization,
            destructive=destructive,
            exit_kind="verdict",
        ),
    )


@dataclass(frozen=True, slots=True)
class Group:
    """A path prefix that groups commands, with the help its group command shows."""

    name: str
    help: str
    # A hidden group runs and documents its commands but is not listed in the bare help.
    hidden: bool = False


@dataclass(frozen=True, slots=True)
class Selection:
    """The operation a request selects, or the gaps and the detail of its refusal."""

    operation: Operation | None
    gaps: tuple[str, ...] = ()
    detail: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Command:
    """One command: its request model and the operations its selectors choose between."""

    # The command's path of up to three words, such as `land` or `attestation record`.
    name: str
    summary: str
    request: type[CommandRequest]
    operations: tuple[Operation, ...]
    # The flag words that differ from a field's name with `_` spelled `-`.
    spellings: tuple[tuple[str, str], ...] = ()
    # The fields that command-line words bind, in order; a last tuple field takes every later word.
    positionals: tuple[str, ...] = ()
    # The fields whose values may start with `-`, such as a command passed through.
    hyphen: tuple[str, ...] = ()

    def flag(self, name: str) -> str:
        """Return the command-line flag of one request field."""
        return "--" + dict(self.spellings).get(name, name.replace("_", "-"))

    def valued(self, name: str) -> bool:
        """Return whether one field's flag takes a value; a boolean flag takes none."""
        return self.request.model_fields[name].annotation is not bool

    def present(self, request: CommandRequest) -> frozenset[str]:
        """Return the fields a request sets to anything other than their defaults."""
        return frozenset(
            name
            for name, info in self.request.model_fields.items()
            if getattr(request, name) != info.default
        )

    def select(self, present: frozenset[str]) -> Selection:
        """Select the operation whose predicates the set fields satisfy, refusing what it lacks."""
        matched = [item for item in self.operations if not item.failed(present)]
        if not matched:
            names = dict.fromkeys(name for item in self.operations for name, _ in item.selectors)
            return Selection(
                None,
                (f"command_operation_unmatched:{self.name}",),
                {
                    "command": self.name,
                    "selectors": {name: name in present for name in names},
                    "operations": [
                        {
                            "id": item.id,
                            "summary": item.summary,
                            "failed": list(item.failed(present)),
                        }
                        for item in self.operations
                    ],
                },
            )
        chosen = matched[0]
        refused = sorted(present - chosen.accepted)
        if refused:
            return Selection(
                None,
                tuple(f"command_field_refused:{name}" for name in refused),
                {
                    "command": self.name,
                    "operation": chosen.id,
                    "refused": {name: self.flag(name) for name in refused},
                },
            )
        return Selection(chosen)

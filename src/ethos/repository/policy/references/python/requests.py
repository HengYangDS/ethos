"""Keep native formal-input obligations separate from concrete invocation evidence."""

from __future__ import annotations

from dataclasses import dataclass

from ethos.repository.policy.references.python.native import PROCESS_PARAMETERS
from ethos.repository.policy.references.python.native import PROCESS_SIGNATURE
from ethos.repository.policy.references.python.native import PROCESS_WRAPPER_KEYWORDS
from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import ExecutableLookup
from ethos.repository.policy.references.python.values import Expansion
from ethos.repository.policy.references.python.values import FormalInput
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import MappingValue
from ethos.repository.policy.references.python.values import Sequence
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value
from ethos.repository.policy.references.python.values import join
from ethos.repository.policy.references.python.values import reachable_values


@dataclass(frozen=True, slots=True)
class NativeReferenceRequest:
    """A static input-consumption contract carries no invocation or effect authority."""

    kind: str
    native: str
    line: int
    inputs: tuple[FormalInput, ...]
    path: str = ""


def native_request(
    call: BoundCall, kind: str, *, values: Value | None = None
) -> NativeReferenceRequest | None:
    """Represent only direct native input consumption, never an unknown transformation."""
    if len(call.targets) != 1 or not isinstance(target := next(iter(call.targets)), Imported):
        return None
    if values is None:
        values = process_request_values(call) if kind == "executable" else call.argument(0, "key")
    if any(isinstance(atom, Unknown) for atom in reachable_values(values)):
        return None
    if kind == "value" and any(
        not isinstance(atom, FormalInput)
        and not (isinstance(atom, Literal) and isinstance(atom.value, str))
        for atom in values
    ):
        return None
    inputs = tuple(
        sorted(
            (atom for atom in reachable_values(values) if isinstance(atom, FormalInput)),
            key=lambda item: (item.scope, item.line, item.name),
        )
    )
    return (
        NativeReferenceRequest(kind, target.name, call.line, inputs, call.path) if inputs else None
    )


def process_request_values(call: BoundCall) -> Value:
    """Bind closed arguments natively and preserve formal open keyword shapes."""
    bindings = call.keyword_bindings(retain_formals=True)
    if not all(_process_shape(call, keywords) for keywords in bindings):
        return UNKNOWN
    values = join(
        call.args[index]
        for name in ("args", "executable", "shell")
        if (index := PROCESS_PARAMETERS.index(name)) < len(call.args)
    )
    for name, value in call.keywords:
        if name in {"args", "shell", "executable"}:
            values |= value
        elif name is None:
            values |= join(
                frozenset({atom})
                if isinstance(atom, FormalInput)
                else atom.remainder
                | join(bound for key, bound in atom.items if key in {"args", "shell", "executable"})
                if isinstance(atom, MappingValue)
                else UNKNOWN
                for atom in value
            )
    return values


def _process_shape(call: BoundCall, keywords: dict[str, Value] | None) -> bool:
    """Native signatures and explicit control semantics reject invalid known shapes."""
    if keywords is None:
        return False
    for target in call.targets:
        if target == Imported("subprocess.check_output") and {"check", "stdout"} & keywords.keys():
            return False
        selected = {
            name: value
            for name, value in keywords.items()
            if name not in PROCESS_WRAPPER_KEYWORDS.get(target, frozenset())
        }
        try:
            arguments = PROCESS_SIGNATURE.bind_partial(*call.args, **selected).arguments
        except TypeError:
            return False
        if not _argv_shape(arguments.get("args", UNKNOWN)):
            return False
        if not all(
            isinstance(atom, FormalInput)
            or (
                isinstance(atom, Literal)
                and (
                    isinstance(atom.value, bool)
                    if name == "shell"
                    else isinstance(atom.value, str) or atom.value is None
                )
            )
            for name in ("shell", "executable")
            for atom in arguments.get(name, frozenset())
        ):
            return False
    return True


def _argv_shape(values: Value) -> bool:
    """Known argv members must be supported strings; formals remain conditional."""
    pending = list(values)
    while pending:
        atom = pending.pop()
        if isinstance(atom, Sequence):
            pending.extend(item for value in atom.items for item in value)
        elif isinstance(atom, Expansion):
            pending.extend(atom.value)
        elif not (
            isinstance(atom, FormalInput | ExecutableLookup | Unknown)
            or (isinstance(atom, Literal) and isinstance(atom.value, str))
        ):
            return False
    return True

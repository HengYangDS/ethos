"""Interpret resolved native Python consumers without executing repository code."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.repository.policy.references.commands.invocation import ArgumentVector
from ethos.repository.policy.references.commands.observation import command_executables
from ethos.repository.policy.references.commands.observation import shell_executables
from ethos.repository.policy.references.python.native import ENVIRONMENT_TARGETS
from ethos.repository.policy.references.python.native import PROCESS_PARAMETERS
from ethos.repository.policy.references.python.native import PROCESS_TARGETS
from ethos.repository.policy.references.python.program import PythonBindings
from ethos.repository.policy.references.python.program import bind_python
from ethos.repository.policy.references.python.requests import NativeReferenceRequest
from ethos.repository.policy.references.python.requests import native_request
from ethos.repository.policy.references.python.requests import process_request_values
from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import ExecutableLookup
from ethos.repository.policy.references.python.values import Expansion
from ethos.repository.policy.references.python.values import FormalInput
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import MappingMethod
from ethos.repository.policy.references.python.values import Sequence
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value

if TYPE_CHECKING:
    from ast import AST


@dataclass(slots=True)
class PythonReferences:
    """Resolved identities and unresolved consumer kinds are independent evidence."""

    imports: set[str] = field(default_factory=set)
    executables: set[str] = field(default_factory=set)
    inputs: set[str] = field(default_factory=set)
    unresolved: set[str] = field(default_factory=set)
    requests: list[NativeReferenceRequest] = field(default_factory=list)


def observe_python(
    tree: AST,
    text: str,
    npm_scripts: dict[str, set[str]],
    *,
    binding: PythonBindings | None = None,
) -> PythonReferences:
    """Observe the supported native-call surface with explicit partial coverage."""
    binding = binding if binding is not None else bind_python(tree, text)
    result = PythonReferences(imports=set(binding.imports))
    result.unresolved.update(
        _unknown_target_kinds(binding.unresolved)
        | ({"reference"} if not binding.compiler_valid else set())
    )
    for call in binding.calls:
        observed = PythonReferences()
        kinds: set[str] = set()
        for target in call.targets:
            if isinstance(target, Imported):
                if target in PROCESS_TARGETS:
                    kinds.add("executable")
                    _process(call, npm_scripts, observed)
                elif target in ENVIRONMENT_TARGETS:
                    kinds.add("value")
                    _environment(call, observed)
            elif isinstance(target, Unknown):
                observed.unresolved.update(_unknown_target_kinds(target.origins))
            elif isinstance(target, MappingMethod) and target.name in {"get", "__getitem__"}:
                _mapping_inputs(call, target, observed)
        if any(isinstance(target, Unknown) for target in call.targets):
            observed.unresolved.update(kinds)
        result.executables.update(observed.executables)
        result.inputs.update(observed.inputs)
        result.imports.update(observed.imports)
        result.unresolved.update(observed.unresolved)
        result.requests.extend(observed.requests)
    return result


def _environment(call: BoundCall, result: PythonReferences) -> None:
    """Keep source-defined key requests distinct from concrete environment identities."""
    request = native_request(call, "value")
    if request is not None:
        result.requests.append(request)
    _strings(
        call.argument(0, "key"),
        result.inputs,
        result.unresolved,
        "value",
        conditional=request is not None,
    )


def _mapping_inputs(call: BoundCall, target: MappingMethod, result: PythonReferences) -> None:
    """Copied entries retain input provenance, not the identity of values they contain."""
    key = call.argument(0, "key")
    if target.owner.environment_read(key):
        _strings(key, result.inputs, result.unresolved, "value")
    else:
        for remainder in target.owner.remainder:
            if isinstance(remainder, Unknown):
                result.unresolved.update(_unknown_target_kinds(remainder.origins))


def _unknown_target_kinds(identities: frozenset[str]) -> set[str]:
    native_kinds = {"subprocess": "executable", "shutil": "executable", "os": "value"}
    return ({"reference"} if "unavailable_source" in identities else set()) | {
        kind
        for identity in identities
        if (kind := native_kinds.get(identity.partition(".")[0])) is not None
    }


def _strings(
    value: Value, into: set[str], unresolved: set[str], kind: str, *, conditional: bool = False
) -> None:
    for atom in value:
        if isinstance(atom, Literal) and isinstance(atom.value, str):
            into.add(atom.value)
        elif not (conditional and isinstance(atom, FormalInput)):
            unresolved.add(kind)


def _process(call: BoundCall, scripts: dict[str, set[str]], result: PythonReferences) -> None:
    """Interpret one keyword alternative at a time without crossing its branch facts."""
    values = process_request_values(call)
    request = native_request(call, "executable", values=values)
    if request is not None:
        result.requests.append(request)
    elif values == UNKNOWN:
        result.unresolved.add("executable")
    for keywords in call.keyword_bindings(retain_formals=request is not None):
        bound = BoundCall(
            call.line,
            call.targets,
            call.args,
            tuple(keywords.items())
            if keywords is not None
            else ((None, call.argument(0, "args")),),
        )
        _process_arguments(bound, scripts, result, conditional=request is not None)


def _process_arguments(
    call: BoundCall,
    scripts: dict[str, set[str]],
    result: PythonReferences,
    *,
    conditional: bool = False,
) -> None:
    shell = call.argument(
        PROCESS_PARAMETERS.index("shell"), "shell", frozenset({Literal(value=False)})
    )
    executable = call.argument(
        PROCESS_PARAMETERS.index("executable"), "executable", frozenset({Literal(None)})
    )
    modes = (
        alternative
        for mode in shell
        for alternative in (
            (Literal(value=False), Literal(value=True))
            if conditional and isinstance(mode, FormalInput)
            else (mode,)
        )
    )
    for mode in modes:
        if not isinstance(mode, Literal) or not isinstance(mode.value, bool):
            result.unresolved.add("executable")
            continue
        for replacement in executable:
            if replacement != Literal(None):
                _strings(
                    frozenset({replacement}),
                    result.executables,
                    result.unresolved,
                    "executable",
                    conditional=conditional,
                )
            if replacement == Literal(None) or mode.value:
                _arguments(
                    call.argument(0, "args"),
                    scripts,
                    result,
                    shell_language=mode.value,
                    conditional=conditional,
                )


def _arguments(
    arguments: Value,
    scripts: dict[str, set[str]],
    result: PythonReferences,
    *,
    shell_language: bool,
    conditional: bool = False,
) -> None:
    for argument in arguments:
        if conditional and isinstance(argument, FormalInput):
            continue
        if isinstance(argument, ExecutableLookup) and not shell_language:
            result.executables.update(
                command_executables((argument.identity,), scripts, unresolved=result.unresolved)
            )
        elif isinstance(argument, Sequence) and not shell_language:
            tokens = _vector(argument)
            if conditional and tokens.words and tokens.words[0] is None:
                continue
            result.executables.update(
                command_executables(
                    tokens, scripts, module_imports=result.imports, unresolved=result.unresolved
                )
            )
        elif isinstance(argument, Sequence):
            _arguments(
                argument.items[0] if argument.items else frozenset({Unknown()}),
                scripts,
                result,
                shell_language=True,
                conditional=conditional,
            )
        elif isinstance(argument, Literal) and isinstance(argument.value, str):
            if shell_language:
                result.executables.update(
                    shell_executables(argument.value, scripts, module_imports=result.imports)
                )
            else:
                # shell=False strings are one executable, never shell words.
                result.executables.update(
                    command_executables(
                        (argument.value,),
                        scripts,
                        module_imports=result.imports,
                        unresolved=result.unresolved,
                    )
                )
        else:
            result.unresolved.add("executable")


def _vector(argument: Sequence) -> ArgumentVector:
    tokens: list[str | None] = []
    pending = deque(argument.items)
    while pending:
        item = pending.popleft()
        if len(item) == 1:
            atom = next(iter(item))
            if isinstance(atom, Expansion):
                if len(atom.value) == 1 and isinstance(nested := next(iter(atom.value)), Sequence):
                    pending.extendleft(reversed(nested.items))
                    continue
                return ArgumentVector(tuple(tokens), open_tail=True)
            if isinstance(atom, ExecutableLookup) and not tokens:
                tokens.append(atom.identity)
                continue
            if isinstance(atom, Literal) and isinstance(atom.value, str):
                tokens.append(atom.value)
                continue
        tokens.append(None)
    return ArgumentVector(tuple(tokens))

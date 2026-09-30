"""Interpret resolved native Python consumers without executing repository code."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.repository.policy.references.commands.invocation import ArgumentVector
from ethos.repository.policy.references.commands.observation import command_executables
from ethos.repository.policy.references.commands.observation import shell_executables
from ethos.repository.policy.references.python.binding import bind_python
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import ExecutableLookup
from ethos.repository.policy.references.python.values import Expansion
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import Sequence
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value

if TYPE_CHECKING:
    from ast import AST

_PROCESS = frozenset(
    f"subprocess.{name}" for name in ("run", "Popen", "call", "check_call", "check_output")
)
_ENVIRONMENT = frozenset({"os.getenv", "os.environ.get", "os.environ.__getitem__"})


@dataclass(slots=True)
class PythonReferences:
    """Resolved identities and unresolved consumer kinds are independent evidence."""

    imports: set[str] = field(default_factory=set)
    executables: set[str] = field(default_factory=set)
    inputs: set[str] = field(default_factory=set)
    unresolved: set[str] = field(default_factory=set)


def observe_python(tree: AST, text: str, npm_scripts: dict[str, set[str]]) -> PythonReferences:
    """Observe the supported native-call surface with explicit partial coverage."""
    binding = bind_python(tree, text)
    result = PythonReferences(imports=set(binding.imports))
    if not binding.compiler_valid:
        result.unresolved.add("reference")
    for call in binding.calls:
        kinds: set[str] = set()
        for target in call.targets:
            if isinstance(target, Imported):
                if target.name in _PROCESS:
                    kinds.add("executable")
                    _process(call, npm_scripts, result)
                elif target.name in _ENVIRONMENT:
                    kinds.add("value")
                    _strings(call.argument(0, "key"), result.inputs, result.unresolved, "value")
            elif isinstance(target, Unknown):
                result.unresolved.update(_unknown_target_kinds(target.origins))
        if any(isinstance(target, Unknown) for target in call.targets):
            result.unresolved.update(kinds)
    return result


def _unknown_target_kinds(identities: frozenset[str]) -> set[str]:
    native_kinds = {"subprocess": "executable", "shutil": "executable", "os": "value"}
    return {
        kind
        for identity in identities
        if (kind := native_kinds.get(identity.partition(".")[0])) is not None
    }


def _strings(value: Value, into: set[str], unresolved: set[str], kind: str) -> None:
    for atom in value:
        if isinstance(atom, Literal) and isinstance(atom.value, str):
            into.add(atom.value)
        else:
            unresolved.add(kind)


def _process(call: BoundCall, scripts: dict[str, set[str]], result: PythonReferences) -> None:
    shell = call.argument(8, "shell", frozenset({Literal(value=False)}))
    executable = call.argument(2, "executable", frozenset({Literal(None)}))
    for mode in shell:
        if not isinstance(mode, Literal) or not isinstance(mode.value, bool):
            result.unresolved.add("executable")
            continue
        for replacement in executable:
            if replacement != Literal(None):
                _strings(
                    frozenset({replacement}), result.executables, result.unresolved, "executable"
                )
            if replacement == Literal(None) or mode.value:
                _arguments(call.argument(0, "args"), scripts, result, shell_language=mode.value)


def _arguments(
    arguments: Value,
    scripts: dict[str, set[str]],
    result: PythonReferences,
    *,
    shell_language: bool,
) -> None:
    for argument in arguments:
        if isinstance(argument, ExecutableLookup) and not shell_language:
            result.executables.update(
                command_executables((argument.identity,), scripts, unresolved=result.unresolved)
            )
        elif isinstance(argument, Sequence) and not shell_language:
            tokens = _vector(argument)
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

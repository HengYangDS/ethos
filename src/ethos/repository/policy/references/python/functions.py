"""Bind local-call arguments with Python's native signature semantics."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from inspect import Parameter
from inspect import Signature
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.scope import Scope
from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import Expansion
from ethos.repository.policy.references.python.values import FormalInput
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import LocalFunction
from ethos.repository.policy.references.python.values import MappingValue
from ethos.repository.policy.references.python.values import Sequence
from ethos.repository.policy.references.python.values import join
from ethos.repository.policy.references.python.values import substitute_inputs

if TYPE_CHECKING:
    import ast
    import symtable

    from ethos.repository.policy.references.python.binding import PythonFlow
    from ethos.repository.policy.references.python.values import Value


@dataclass(frozen=True, slots=True)
class FunctionObservation:
    """One parametric body result, consumed calls and mutation footprint, without execution."""

    result: Value
    calls: tuple[BoundCall, ...]
    invalidated: Value

    def bind(self, identity: LocalFunction, values: dict[str, Value]) -> FunctionObservation:
        """Compose explicit parameter relations without rerunning the function body."""
        bindings = {
            FormalInput(identity.name, identity.line, name, identity.path): value
            for name, value in values.items()
        }
        return FunctionObservation(
            substitute_inputs(self.result, bindings),
            tuple(
                replace(
                    call,
                    targets=substitute_inputs(call.targets, bindings),
                    args=tuple(substitute_inputs(value, bindings) for value in call.args),
                    keywords=tuple(
                        (name, substitute_inputs(value, bindings)) for name, value in call.keywords
                    ),
                )
                for call in self.calls
            ),
            substitute_inputs(self.invalidated, bindings),
        )


def function_tables(table: symtable.SymbolTable) -> dict[tuple[str, int], symtable.SymbolTable]:
    """Index compiler-owned callable and class scopes without parsing their spellings."""
    tables = {}
    pending = [table]
    while pending:
        current = pending.pop()
        if current.get_type() in {"function", "class"}:
            tables[current.get_name(), current.get_lineno()] = current
        pending.extend(current.get_children())
    return tables


def function_signature(
    arguments: ast.arguments,
    defaults: tuple[Value, ...],
    keyword_defaults: tuple[Value | None, ...],
) -> Signature:
    """Project AST parameter kinds and already-evaluated defaults into a signature."""
    positional = (*arguments.posonlyargs, *arguments.args)
    first_default = len(positional) - len(defaults)
    parameters = [
        Parameter(
            argument.arg,
            Parameter.POSITIONAL_ONLY
            if index < len(arguments.posonlyargs)
            else Parameter.POSITIONAL_OR_KEYWORD,
            default=defaults[index - first_default] if index >= first_default else Parameter.empty,
        )
        for index, argument in enumerate(positional)
    ]
    if arguments.vararg is not None:
        parameters.append(Parameter(arguments.vararg.arg, Parameter.VAR_POSITIONAL))
    parameters.extend(
        Parameter(
            argument.arg,
            Parameter.KEYWORD_ONLY,
            default=default if default is not None else Parameter.empty,
        )
        for argument, default in zip(arguments.kwonlyargs, keyword_defaults, strict=True)
    )
    if arguments.kwarg is not None:
        parameters.append(Parameter(arguments.kwarg.arg, Parameter.VAR_KEYWORD))
    return Signature(parameters)


def call_arguments(signature: Signature, call: BoundCall) -> dict[str, Value]:
    """Preserve supported native binding; expansions and invalid calls stay unknown."""
    if any(isinstance(atom, Expansion) for value in call.args for atom in value):
        return dict.fromkeys(signature.parameters, UNKNOWN)
    alternatives: list[dict[str, Value]] = []
    for keywords in call.keyword_bindings():
        if keywords is None:
            alternatives.append(dict.fromkeys(signature.parameters, UNKNOWN))
            continue
        try:
            bound = signature.bind(*call.args, **keywords)
        except TypeError:
            alternatives.append(dict.fromkeys(signature.parameters, UNKNOWN))
            continue
        bound.apply_defaults()
        alternatives.append(
            {
                name: frozenset({Sequence(value)})
                if signature.parameters[name].kind == Parameter.VAR_POSITIONAL
                else frozenset({MappingValue((call.line, -1), tuple(value.items()))})
                if signature.parameters[name].kind == Parameter.VAR_KEYWORD
                else value
                for name, value in bound.arguments.items()
            }
        )
    return {
        name: join(alternative.get(name, UNKNOWN) for alternative in alternatives)
        for name in signature.parameters
    }


def local_call(
    flow: PythonFlow, identity: LocalFunction, call: BoundCall, caller: Scope | None = None
) -> Value:
    """Observe one bounded concrete invocation without executing source code."""
    if identity.path != flow.path:
        return flow.invoke(identity, call, caller) if flow.invoke else UNKNOWN
    if identity in flow.active or len(flow.active) >= 32:
        flow.incomplete.add(identity)
        return UNKNOWN
    flow.local_attempts += 1
    node, parent, signature = flow.functions[identity]
    scope = Scope(flow.tables[(node.name, node.lineno)], parent)
    scope.values.update(
        call_arguments(
            signature,
            BoundCall(call.line, call.targets, (), ((None, UNKNOWN),), call.path)
            if node.decorator_list
            else call,
        )
    )
    flow.active.add(identity)
    previous, flow.current = flow.current, identity
    flow.returns.append([])
    try:
        falls_through = flow.block(node.body, scope)
        values = flow.returns[-1]
        if falls_through:
            values.append(frozenset({Literal(None)}))
        return UNKNOWN if node.decorator_list else join(values) or UNKNOWN
    finally:
        flow.returns.pop()
        flow.active.remove(identity)
        flow.current = previous
        if caller is not None:
            caller.invalidate(scope.invalidated)

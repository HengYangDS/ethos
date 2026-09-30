"""Bind local-call arguments with Python's native signature semantics."""

from __future__ import annotations

from inspect import Parameter
from inspect import Signature
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import Expansion
from ethos.repository.policy.references.python.values import Sequence

if TYPE_CHECKING:
    import ast

    from ethos.repository.policy.references.python.values import BoundCall
    from ethos.repository.policy.references.python.values import Value


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
    if any(key is None for key, _ in call.keywords) or any(
        isinstance(atom, Expansion) for value in call.args for atom in value
    ):
        return dict.fromkeys(signature.parameters, UNKNOWN)
    try:
        bound = signature.bind(
            *call.args, **{key: value for key, value in call.keywords if key is not None}
        )
    except TypeError:
        return dict.fromkeys(signature.parameters, UNKNOWN)
    bound.apply_defaults()
    return {
        name: frozenset({Sequence(value)})
        if signature.parameters[name].kind == Parameter.VAR_POSITIONAL
        else UNKNOWN
        if signature.parameters[name].kind == Parameter.VAR_KEYWORD
        else value
        for name, value in bound.arguments.items()
    }

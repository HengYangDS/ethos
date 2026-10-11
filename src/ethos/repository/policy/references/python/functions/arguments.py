"""Native signature binding preserves proven slots beside uncertain argument packs."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ParameterProjection

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.functions.returns import FunctionDefinition


def bound_arguments(
    definition: FunctionDefinition,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
) -> dict[str, BindingValue] | None:
    """Use the same native signature/default relation for summaries and actual calls."""
    if None in keywords:
        return None
    named = dict(definition.captured_keywords) | cast("dict[str, BindingValue]", keywords)
    positional = (*definition.captured, *args)
    spread = next((index for index, value in enumerate(positional) if value.spread), None)
    binder = definition.signature.bind if spread is None else definition.signature.bind_partial
    try:
        bound = binder(*positional[:spread], **named)
    except TypeError:
        return None
    assigned = frozenset(bound.arguments)
    bound.apply_defaults()
    values = bound_values(definition, bound)
    if spread is None:
        return values
    tail = BindingValue(unknown=True)
    for value in positional[spread:]:
        tail = tail.join(value.element or BindingValue(unknown=True) if value.spread else value)
    for name, parameter in definition.signature.parameters.items():
        if parameter.kind == parameter.VAR_POSITIONAL:
            prefix = values.get(name, BindingValue(items=(), ordered=True)).iterated()
            values[name] = BindingValue(element=prefix.join(tail), unknown=True)
        elif name not in assigned:
            if parameter.kind in {parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD}:
                values[name] = tail.join(values[name]) if name in values else tail
            elif parameter.kind == parameter.KEYWORD_ONLY and parameter.default is parameter.empty:
                return None
    return values


def bound_values(
    definition: FunctionDefinition, bound: inspect.BoundArguments
) -> dict[str, BindingValue]:
    """Project native bound slots, packing variadic positional and keyword arguments."""
    kinds = {name: item.kind for name, item in definition.signature.parameters.items()}
    return {
        name: BindingValue(items=argument, ordered=True)
        if kinds[name] == inspect.Parameter.VAR_POSITIONAL
        else BindingValue(entries=tuple(argument.items()))
        if kinds[name] == inspect.Parameter.VAR_KEYWORD
        else argument
        for name, argument in bound.arguments.items()
    }


def symbolic_arguments(definition: FunctionDefinition) -> dict[str, BindingValue]:
    """Parameterize only runtime slots; a declared classmethod receiver is already bound."""
    values = {
        parameter.name: BindingValue(
            parameters=frozenset({ParameterProjection(parameter.name, owner=definition.key)})
        )
        for parameter in definition.signature.parameters.values()
    }
    if definition.receiver:
        values[next(iter(values))] = BindingValue(targets=frozenset({definition.receiver}))
    return values

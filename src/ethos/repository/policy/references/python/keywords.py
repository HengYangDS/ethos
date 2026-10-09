"""Complete native keyword shapes and bounded call alternatives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue

if TYPE_CHECKING:
    import ast

    from ethos.repository.policy.references.python.flow import PythonReferenceFlow
    from ethos.repository.policy.references.python.scope import BindingScope


def keyword_arguments(
    flow: PythonReferenceFlow, arguments: list[ast.keyword], scope: BindingScope
) -> list[dict[str | None, BindingValue]]:
    """Expand only complete native keyword shapes, retaining ambiguous call alternatives."""
    alternatives: list[dict[str | None, BindingValue]] = [{}]
    for argument in arguments:
        value = flow.expression(argument.value, scope)
        if argument.arg is not None:
            for keywords in alternatives:
                keywords[argument.arg] = value
            continue
        if flow.sources is not None:
            value = flow.sources.invocations.resolve(value, scope, flow.result, deep=False)
        value = scope.resolve(value)
        if value.entries is None or value.unknown or value.deferred or value.parameters:
            for keywords in alternatives:
                keywords[None] = value
        else:
            alternatives = expand_keywords(alternatives, value)
    return alternatives


def expand_keywords(
    alternatives: list[dict[str | None, BindingValue]], value: BindingValue
) -> list[dict[str | None, BindingValue]]:
    """A duplicate key or exhausted finite expansion remains an unresolved invocation."""
    shapes = value.closed_mapping_shapes()
    if len(alternatives) * len(shapes) > 64:
        return [{**keywords, None: BindingValue(unknown=True)} for keywords in alternatives]
    expanded = []
    for keywords in alternatives:
        for shape in shapes:
            branch = dict(keywords)
            if branch.keys() & dict(shape).keys():
                branch[None] = BindingValue(unknown=True)
            else:
                branch.update(shape)
            expanded.append(branch)
    return expanded

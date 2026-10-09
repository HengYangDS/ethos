"""Opaque escape capability observation and immutable native-value qualification."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.custody import InvocationCustody
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
    from ethos.repository.policy.references.python.functions.returns import FunctionDefinition
    from ethos.repository.policy.references.python.scope import BindingScope


def immutable_native_value(value: BindingValue) -> bool:
    """Certify closed native leaves and tuples, not opaque or reachable mutable custody."""
    pending, seen = [value], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        remainder = replace(
            current,
            strings=frozenset(),
            truths=frozenset(),
            executable_origins=frozenset(),
            path=False,
            items=None,
            ordered=False,
        )
        if remainder != BindingValue():
            return False
        if current.items is not None:
            pending.extend(current.items)
        elif not (current.strings or current.truths or current.executable_origins or current.path):
            return False
    return True


def escaped_capabilities(
    custody: InvocationCustody,
    values: tuple[BindingValue, ...],
    scope: BindingScope,
    observer: PythonConsumption,
) -> frozenset[str]:
    """Follow actual reachable and lazy inputs, not every callable in the module."""
    pending, seen, aggregates, found, captures = (
        [(value, scope) for value in values],
        set(),
        set(),
        set(),
        set(),
    )
    while pending:
        value, owner = pending.pop()
        identities = {(identity, owner.identity) for identity in value.aggregates}
        site = id(value), owner.identity
        if site in seen or (identities and identities <= aggregates):
            continue
        seen.add(site)
        aggregates.update(identities)
        value = custody.sources.call_identity(
            custody.sources.invocations.resolve(value, owner, observer, deep=False)
        )
        found.update(
            target
            for target in value.targets
            if observer.kind(target) or observer.module_kinds(target)
        )
        pending.extend((item, owner) for item in value.items or ())
        pending.extend((item, owner) for _, item in (*(value.entries or ()), *(value.fields or ())))
        pending.extend((method.receiver, owner) for method in value.methods)
        if value.element is not None:
            pending.append((value.element, owner))
        for target in value.targets | value.instance_types:
            definition = custody.sources.definitions.get(target)
            if definition is not None and (target, owner.identity) not in captures:
                captures.add((target, owner.identity))
                pending.extend(custody.capture_roots(definition, definition.parent))
            pending.extend(custody.record_roots(target, owner))
    return frozenset(found)


def invocation_roots(
    request: SourceInvocation,
) -> tuple[list[tuple[BindingValue, BindingScope]], list[tuple[FunctionDefinition, BindingScope]]]:
    """Completed returns export their actual custody; unresolved calls retain input roots."""
    if request.returned is not None:
        if immutable_native_value(request.returned):
            return [], []
        if (
            request.returned.allocation_complete
            and request.returned.aggregates
            and not request.returned.context_limited
        ) or not (
            request.returned.unknown
            or request.returned.deferred
            or request.returned.context_limited
        ):
            return [(request.returned, request.caller)], []
    return [
        *((item, request.caller) for item in request.arguments),
        *((item, request.caller) for item in request.keywords.values()),
        *(((request.returned, request.caller),) if request.returned is not None else ()),
    ], [(request.definition, request.parent)]

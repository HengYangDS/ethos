"""Finite bound reference selection for escaped source callables and retained values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.functions.effects import observe_calls
from ethos.repository.policy.references.python.functions.effects import substitute
from ethos.repository.policy.references.python.functions.effects import symbolic_arguments

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import BindingScope
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


def escaped_capabilities(
    sources: PythonSourceReturns,
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
        value = sources.invocations.resolve(value, owner, observer, deep=False)
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
        for target in value.targets:
            definition = sources.definitions.get(target)
            if definition is not None and (target, owner.identity) not in captures:
                captures.add((target, owner.identity))
                summary = sources.invocations.summary_for(definition, observer, owner)
                arguments = dict.fromkeys(
                    symbolic_arguments(definition), BindingValue(unknown=True)
                )
                for name, parameter in definition.signature.parameters.items():
                    if isinstance(parameter.default, BindingValue):
                        arguments[name] = arguments[name].join(parameter.default)
                observed = type(observer)(definition.flow.path, observer.npm_scripts, sources)
                observe_calls(
                    summary,
                    arguments,
                    owner,
                    sources,
                    observed,
                    owner=target,
                    transitive=True,
                )
                observer.absorb(observed)
                found.update(
                    item.target for item in observed.uncertainties if item.state == "unknown"
                )
                pending.append(
                    (
                        substitute(
                            summary.returned,
                            arguments,
                            owner,
                            sources,
                            observer,
                            owner=target,
                        ),
                        owner,
                    )
                )
            pending.extend(sources.invocations.custody.record_roots(target, owner))
    return frozenset(found)

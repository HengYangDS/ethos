"""Signature-substituted effect relationships, distinct from actual return custody."""

from __future__ import annotations

import inspect
import itertools
import shlex
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import LexicalRead
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.bindings import ParameterProjection
from ethos.repository.policy.references.python.native.scalars import concatenate
from ethos.repository.policy.references.python.native.scalars import native_scalar

if TYPE_CHECKING:
    import ast

    from ethos.repository.policy.references.python.bindings import BindingScope
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
    from ethos.repository.policy.references.python.functions.returns import FunctionDefinition
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
    from ethos.repository.policy.references.python.syntax import LexicalBindings


@dataclass(frozen=True, slots=True)
class EffectCall:
    """A source or callback edge retaining actual argument substitutions and its site."""

    callee: BindingValue
    arguments: tuple[BindingValue, ...]
    keywords: dict[str | None, BindingValue]
    node: ast.expr
    path: str
    scope: str


@dataclass(frozen=True, slots=True)
class MemberRead:
    """A demanded heap relation and its supplying lexical program point."""

    namespace: BindingScope
    subject: BindingValue
    demand: MemberDemand
    value: BindingValue
    later: bool = False


@dataclass(slots=True)
class EffectSummary:
    """Tracked native effects, parameterized calls and externally observable footprints."""

    direct: bool = False
    context_limited: bool = False
    context_depth: int = 0
    answers: dict[tuple[BindingValue, ...], BindingValue] = field(default_factory=dict)
    calls: list[EffectCall] = field(default_factory=list)
    footprints: list[BindingValue] = field(default_factory=list)
    reads: dict[tuple[int, str, bool], LexicalRead] = field(default_factory=dict)
    members: dict[tuple[int, bool, BindingValue, MemberDemand], MemberRead] = field(
        default_factory=dict
    )
    returned: BindingValue = field(
        default_factory=lambda: BindingValue(deferred=True, unknown=True, context_limited=True)
    )
    observation: PythonConsumption | None = None
    pending: tuple[
        tuple[
            ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
            BindingScope,
            LexicalBindings,
            BindingValue,
        ],
        ...,
    ] = ()


def bound_arguments(
    definition: FunctionDefinition,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
) -> dict[str, BindingValue] | None:
    """Use the same native signature/default relation for summaries and actual calls."""
    if None in keywords or any(value.spread for value in args):
        return None
    try:
        bound = definition.signature.bind(
            *args, **{name: value for name, value in keywords.items() if name is not None}
        )
    except TypeError:
        return None
    bound.apply_defaults()
    values = {}
    for name, argument in bound.arguments.items():
        kind = definition.signature.parameters[name].kind
        values[name] = (
            BindingValue(items=argument, ordered=True)
            if kind == inspect.Parameter.VAR_POSITIONAL
            else BindingValue(entries=tuple(argument.items()))
            if kind == inspect.Parameter.VAR_KEYWORD
            else argument
        )
    return values


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


def observe_calls(
    summary: EffectSummary,
    arguments: dict[str, BindingValue],
    scope: BindingScope,
    sources: PythonSourceReturns,
    observer: PythonConsumption,
    *,
    owner: str,
    transitive: bool = False,
) -> None:
    """Instantiate native effect edges at their defining source sites, not generic findings."""
    pending = [(owner, summary, arguments)]
    seen = set()
    while pending:
        owner, summary, arguments = pending.pop()
        if len(seen) >= 128:
            arguments = dict.fromkeys(arguments, BindingValue(unknown=True, context_limited=True))
        key = owner, tuple(arguments.items())
        if key in seen:
            continue
        seen.add(key)
        observe_summary(summary, arguments, scope, sources, observer, owner=owner)
        if not transitive:
            continue
        for call in summary.calls:
            callee = substitute(call.callee, arguments, scope, sources, observer, owner=owner)
            selected = sources.call_identity(callee)
            for target in frozenset(t for t in selected.targets if t in sources.definitions):
                definition = sources.definitions[target]
                actual = bound_arguments(
                    definition,
                    tuple(
                        substitute(value, arguments, scope, sources, observer, owner=owner)
                        for value in call.arguments
                    ),
                    {
                        name: substitute(value, arguments, scope, sources, observer, owner=owner)
                        for name, value in call.keywords.items()
                    },
                )
                if actual is not None:
                    pending.append(
                        (
                            target,
                            sources.invocations.summary_for(definition, observer, scope),
                            actual,
                        )
                    )


def observe_summary(
    summary: EffectSummary,
    arguments: dict[str, BindingValue],
    scope: BindingScope,
    sources: PythonSourceReturns,
    observer: PythonConsumption,
    *,
    owner: str,
) -> None:
    """Replay one context's native sites while retaining their source identities."""
    if summary.observation is not None:
        observer.absorb(summary.observation)
    for call in tuple(summary.calls):
        callee = sources.call_identity(
            substitute(call.callee, arguments, scope, sources, observer, owner=owner)
        )
        targets = frozenset(
            target for target in callee.targets if target not in sources.definitions
        )
        if (
            targets
            or callee.selection
            or callee.unknown
            or callee.local
            or callee.parameters
            or (callee.deferred and not callee.targets)
        ):
            site = scope.fork()
            site.name = call.scope
            observation = type(observer)(call.path, observer.npm_scripts, sources=sources)
            observation.native_call(
                replace(callee, targets=targets),
                tuple(
                    substitute(value, arguments, scope, sources, observer, owner=owner)
                    for value in call.arguments
                ),
                {
                    name: substitute(value, arguments, scope, sources, observer, owner=owner)
                    for name, value in call.keywords.items()
                },
                call.node,
                site,
            )
            observer.absorb(observation)


def substitute(
    value: BindingValue,
    arguments: dict[str, BindingValue],
    scope: BindingScope,
    sources: PythonSourceReturns,
    observer: PythonConsumption,
    *,
    owner: str,
) -> BindingValue:
    """Instantiate template children before inserting actual values with intact heap custody."""
    held = frozenset(key for key in value.aggregates if scope.member(key) != BindingValue())
    value = scope.resolve(value) if held else value
    selected_slots = frozenset(item for item in value.parameters if item.owner == owner)
    methods = frozenset(
        method
        if (
            receiver := substitute(
                method.receiver, arguments, scope, sources, observer, owner=owner
            )
        )
        is method.receiver
        else replace(method, receiver=receiver)
        for method in value.methods
    )
    items = (
        tuple(
            substitute(item, arguments, scope, sources, observer, owner=owner)
            for item in value.items
        )
        if value.items is not None
        else None
    )
    entries = (
        tuple(
            (name, substitute(item, arguments, scope, sources, observer, owner=owner))
            for name, item in value.entries
        )
        if value.entries is not None
        else None
    )
    fields = (
        tuple(
            (name, substitute(item, arguments, scope, sources, observer, owner=owner))
            for name, item in value.fields
        )
        if value.fields is not None
        else None
    )
    element = (
        substitute(value.element, arguments, scope, sources, observer, owner=owner)
        if value.element is not None
        else None
    )
    if all(left is right for left, right in zip(value.items or (), items or (), strict=True)):
        items = value.items
    if all(
        left is right
        for (_, left), (_, right) in zip(value.entries or (), entries or (), strict=True)
    ):
        entries = value.entries
    if all(
        left is right
        for (_, left), (_, right) in zip(value.fields or (), fields or (), strict=True)
    ):
        fields = value.fields
    current = (
        value
        if not selected_slots
        and held == value.aggregates
        and methods == value.methods
        and items is value.items
        and entries is value.entries
        and fields is value.fields
        and element is value.element
        else replace(
            value,
            parameters=value.parameters - selected_slots,
            aggregates=held,
            methods=methods,
            items=items,
            entries=entries,
            fields=fields,
            element=element,
        )
    )
    for projection in selected_slots:
        selected = arguments.get(projection.name, BindingValue(unknown=True))
        for member in projection.members:
            selector = (
                substitute(member.selector, arguments, scope, sources, observer, owner=owner)
                if member.selector is not None
                else None
            )
            default = (
                substitute(member.default, arguments, scope, sources, observer, owner=owner)
                if member.default is not None
                else None
            )
            selected = project(
                selected,
                replace(member, selector=selector, default=default),
                scope,
                sources,
                observer,
            )
        current = current.join(selected)
    return current


def mapping_get(value: BindingValue, demand: MemberDemand) -> BindingValue:
    """Select native missing-key defaults without conflating absence with UNKNOWN."""
    selector = demand.selector or BindingValue(strings=frozenset({str(demand.key)}))
    selected = BindingValue(
        deferred=selector.deferred or value.deferred,
        unknown=selector.unknown or value.unknown,
    )
    for name in selector.strings:
        selected = selected.join(
            dict(value.entries or ()).get(name, demand.default or BindingValue(local=True))
        )
    return selected if selector.strings else selected.join(BindingValue(unknown=True))


def native_iteration(
    value: BindingValue, demand: MemberDemand, scope: BindingScope
) -> BindingValue:
    """Keep iterator topology distinct from its current ordinal or joined yield."""
    if demand.kind == "iteration_shape":
        base = scope.resolve(replace(value, view="")) if value.view else value
        items = (
            tuple(BindingValue(strings=frozenset({name})) for name, _ in base.entries)
            if base.entries is not None
            else tuple(BindingValue(local=True) for _ in base.items)
            if base.items is not None
            else None
        )
        return BindingValue(
            items=items,
            ordered=base.ordered,
            unknown=base.unknown or value.unknown or value.local or bool(value.targets),
            deferred=base.deferred or value.deferred,
        )
    items = (
        tuple(BindingValue(strings=frozenset({name})) for name, _ in value.entries)
        if value.entries is not None
        else value.items
    )
    if demand.key is None:
        selected = replace(value, items=items).iterated()
    elif items is not None and isinstance(demand.key, int) and 0 <= demand.key < len(items):
        selected = scope.resolve(items[demand.key])
    else:
        selected = BindingValue(unknown=True)
    return replace(
        selected,
        unknown=selected.unknown or value.unknown or value.local or bool(value.targets),
        deferred=selected.deferred or value.deferred,
    )


def selected_key(demand: MemberDemand) -> str | int | None:
    """A concrete selector requires one closed string, not a symbolic or opaque alternative."""
    key = demand.key
    if demand.selector is not None:
        selector = demand.selector
        key = next(iter(selector.strings)) if len(selector.strings) == 1 else None
        if selector.unknown or selector.deferred or selector.parameters:
            key = None
    return key


def native_member(
    value: BindingValue, demand: MemberDemand, scope: BindingScope, observer: PythonConsumption
) -> BindingValue:
    """Read one closed native relation, retaining opaque selectors and missing values."""
    key = selected_key(demand)
    if demand.kind == "native_return" and isinstance(key, str):
        selected = native_scalar(key, (value,), {}) or BindingValue(unknown=True)
    elif demand.kind == "concatenate":
        other = demand.selector or BindingValue(unknown=True)
        selected = concatenate(value, other) if demand.key == "left" else concatenate(other, value)
    elif demand.kind == "truth":
        truth = value.truthiness()
        selected = (
            BindingValue(truths=frozenset({truth}))
            if truth is not None
            else BindingValue(unknown=True)
        )
    elif demand.kind in {"iteration_shape", "iterate"}:
        selected = native_iteration(value, demand, scope)
    elif demand.kind == "structure":
        selected = replace(
            value,
            items=tuple(BindingValue(strings=frozenset({name})) for name, _ in value.entries)
            if value.entries is not None
            else value.items,
            entries=None,
            fields=None,
            aggregates=frozenset(),
            view="",
            native_kind="",
        )
    elif demand.kind == "attribute":
        names = (
            BindingValue(strings=frozenset({key}))
            if isinstance(key, str)
            else BindingValue(unknown=True)
        )
        selected = observer.attribute((value, names), scope)
    elif value.entries is not None and demand.kind == "get":
        selected = mapping_get(value, demand)
    elif value.entries is not None:
        selector = (
            BindingValue(strings=frozenset({key}))
            if isinstance(key, str)
            else demand.selector or BindingValue(unknown=True)
        )
        selected = scope.resolve(value.selected(selector))
    elif (
        value.items is not None
        and isinstance(key, int)
        and -len(value.items) <= key < len(value.items)
    ):
        selected = scope.resolve(value.items[key])
        selected = replace(
            selected,
            unknown=selected.unknown or value.unknown,
            deferred=selected.deferred or value.deferred,
        )
    else:
        selected = BindingValue(
            deferred=value.deferred, unknown=value.unknown or not value.deferred
        )
    return replace(selected, context_limited=selected.context_limited or value.context_limited)


def project(
    value: BindingValue,
    demand: MemberDemand,
    scope: BindingScope,
    sources: PythonSourceReturns | None,
    observer: PythonConsumption,
) -> BindingValue:
    """Bind symbolic demands or record the exact native relation actually consumed."""
    value = scope.resolve(value)
    if value.parameters or value.projections:
        return replace(
            value,
            parameters=frozenset(
                replace(item, members=(*item.members, demand)) for item in value.parameters
            ),
            projections=frozenset(
                replace(item, members=(*item.members, demand)) for item in value.projections
            ),
        )
    selected = native_member(value, demand, scope, observer)
    if sources is not None:
        sources.invocations.note_member(value, demand, selected, scope)
    return selected


def command_tokens(value: BindingValue) -> tuple[tuple[str, ...], ...]:
    """Retain a finite executable prefix despite unresolved trailing arguments."""
    if value.items is None:
        commands = []
        for item in value.strings:
            try:
                commands.append(tuple(shlex.split(item)))
            except ValueError:
                continue
        return tuple(commands)
    alternatives = []
    count = 1
    for item in value.items:
        if not item.strings or count * len(item.strings) > 64:
            break
        alternatives.append(tuple(sorted(item.strings)))
        count *= len(item.strings)
    return tuple(itertools.product(*alternatives)) if alternatives else ()


def effect_dependencies(
    invocations: PythonInvocations,
    summary: EffectSummary,
    key: str,
    arguments: dict[str, BindingValue],
    scope: BindingScope,
    result: PythonConsumption,
) -> tuple[
    list[tuple[FunctionDefinition, tuple[BindingValue, ...], dict[str | None, BindingValue]]],
    bool,
]:
    """Instantiate each call edge independently of known and opaque alternatives."""
    pending = []
    for call in summary.calls:
        callee = substitute(call.callee, arguments, scope, invocations.sources, result, owner=key)
        selected = invocations.sources.call_identity(callee)
        if selected.selection or any(result.kind(target) for target in selected.targets):
            return pending, True
        values = tuple(
            substitute(value, arguments, scope, invocations.sources, result, owner=key)
            for value in call.arguments
        )
        named_values = {
            name: substitute(value, arguments, scope, invocations.sources, result, owner=key)
            for name, value in call.keywords.items()
        }
        for method in selected.methods:
            native = result.bound_method(
                scope.resolve(method.receiver), method.name, values, named_values, scope
            )
            if native.disposition != "read" and any(
                invocations.custody.mutable(value)
                for value in (native.footprint, *values, *named_values.values())
            ):
                return pending, True
        pending.extend(
            (invocations.sources.definitions[target], values, named_values)
            for target in selected.targets
            if target in invocations.sources.definitions
        )
        if result.call_escapes(selected, values, named_values, scope):
            return pending, True
        if selected.unknown and not (selected.targets or selected.methods or selected.parameters):
            roots = [callee, selected, *values, *named_values.values()]
            if not any(invocations.custody.mutable(value, symbolic=True) for value in roots):
                roots.extend(read.value for read in summary.reads.values())
                roots.append(summary.returned)
                if not invocations.custody.retained_transfer(roots, scope):
                    continue
        if callee.parameters or selected.unknown or (selected.deferred and not selected.methods):
            return pending, True
    return pending, False

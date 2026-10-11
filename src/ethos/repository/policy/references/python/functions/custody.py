"""Invocation-local heap and callable capture custody, never proof or authority."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import AggregateIdentity
from ethos.repository.policy.references.python.bindings import BindingScope
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.effects import PythonConsumption
from ethos.repository.policy.references.python.functions.effects import native_member
from ethos.repository.policy.references.python.functions.effects import substitute
from ethos.repository.policy.references.python.functions.effects import supplied

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import LexicalRead
    from ethos.repository.policy.references.python.control import FlowExit
    from ethos.repository.policy.references.python.functions.effects import EffectSummary
    from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
    from ethos.repository.policy.references.python.functions.returns import FunctionDefinition
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@dataclass(slots=True)
class InvocationCustody:
    """Follow only reachable post-call heaps and the actual callable/default environments."""

    sources: PythonSourceReturns

    @staticmethod
    def namespace(expected: BindingScope, scope: BindingScope) -> BindingScope:
        """Select a lexical frame by identity; absent frames retain their recorded owner."""
        current: BindingScope | None = scope
        while current is not None:
            if current.identity == expected.identity:
                return current
            current = current.parent
        return expected

    def lexical_value(self, read: LexicalRead, scope: BindingScope) -> BindingValue:
        """Reobserve a name at its retained program point through selected live custody."""
        namespace = self.namespace(read.namespace, scope)
        return self.witness(namespace.lookup(read.name, later=read.later))

    def unchanged(
        self, summary: EffectSummary, scope: BindingScope, observer: PythonConsumption
    ) -> bool:
        """Recheck bindings and consumed relations, never unrelated reachable contents."""
        if any(self.lexical_value(read, scope) != read.value for read in summary.reads.values()):
            return False
        self.sources.invocations.validating += 1
        try:
            return all(
                self.witness(
                    native_member(selected.resolve(read.subject), read.demand, selected, observer)
                )
                == read.value
                for read in summary.members.values()
                for selected in (
                    scope
                    if read.subject.targets and not read.subject.aggregates
                    else self.view(
                        read.subject,
                        self.namespace(read.namespace, scope),
                        scope,
                        later=read.later,
                    ),
                )
            )
        finally:
            self.sources.invocations.validating -= 1

    def return_inputs(
        self, summary: EffectSummary, arguments: dict[str, BindingValue], scope: BindingScope
    ) -> tuple[BindingValue, ...] | None:
        """Only complete leaves with immutable inputs and exact consumed members share answers."""
        if (
            scope.deferred_outer
            or summary.direct
            or summary.context_limited
            or any(
                read.later
                or read.demand.kind != "attribute"
                or not (
                    (isinstance(read.demand.key, str) and read.demand.selector is None)
                    or (
                        read.demand.selector is not None
                        and len(read.demand.selector.strings) == 1
                        and read.demand.selector
                        == BindingValue(strings=read.demand.selector.strings)
                    )
                )
                or not read.subject.targets
                or self.mutable(read.subject, symbolic=True)
                for read in summary.members.values()
            )
            or any(read.later for read in summary.reads.values())
            or any(
                target in self.sources.definitions or target in self.sources.records
                for call in summary.calls
                for target in call.callee.targets
            )
        ):
            return None
        pending = list(arguments.values())
        while pending:
            value = pending.pop()
            if value.targets or self.mutable(value, symbolic=True):
                return None
            pending.extend(value.items or ())
            pending.extend(item for _, item in value.entries or ())
            pending.extend(method.receiver for method in value.methods)
            if value.element is not None:
                pending.append(value.element)
        if any(self.mutable(read.value, symbolic=True) for read in summary.reads.values()):
            return None
        return tuple(arguments.values())

    @staticmethod
    def witness(value: BindingValue) -> BindingValue:
        """Preserve immutable shape and references; mutable members have separate demands."""
        completed: dict[int, BindingValue] = {}

        def normalized(current: BindingValue) -> BindingValue:
            if id(current) in completed:
                return completed[id(current)]
            if (
                current.items is None
                and current.entries is None
                and current.fields is None
                and current.element is None
                and not current.methods
            ):
                completed[id(current)] = current
                return current
            result = replace(
                current,
                items=tuple(normalized(item) for item in current.items)
                if current.items is not None and not current.aggregates
                else None,
                entries=tuple((name, normalized(item)) for name, item in current.entries)
                if current.entries is not None and not current.aggregates
                else None,
                fields=tuple((name, normalized(item)) for name, item in current.fields)
                if current.fields is not None and not current.aggregates
                else None,
                methods=frozenset(
                    replace(method, receiver=normalized(method.receiver))
                    for method in current.methods
                ),
                element=normalized(current.element)
                if current.element is not None and not current.aggregates
                else None,
            )
            completed[id(current)] = result
            return result

        return normalized(value)

    def view(
        self,
        value: BindingValue,
        source: BindingScope,
        target: BindingScope,
        *,
        later: bool = False,
    ) -> BindingScope:
        """Overlay only reachable missing identities without merging ambient heap state."""
        view = BindingScope(target.name, parent=target, kind=target.kind)
        for key, owners in self.reachable([(value, source)], target=target, later=later).items():
            if not isinstance(key, AggregateIdentity):
                continue
            binding = target.member_binding(key, later=later)
            if binding is None:
                binding = BindingValue()
                for owner in owners.values():
                    binding = binding.join(owner.member(key, later=later))
            view.members[key] = binding
        return view

    def resolve(
        self,
        value: BindingValue,
        source: BindingScope,
        target: BindingScope,
        *,
        later: bool = False,
    ) -> BindingValue:
        """Read immediate live shape without freezing unrelated descendants."""
        if not self.mutable(value):
            return value
        return self.view(value, source, target, later=later).resolve(value)

    def mutable(self, value: BindingValue, *, symbolic: bool = False) -> bool:
        """Follow nested custody; symbolic slots retain conditional call dependencies."""
        pending, seen = [value], set()
        while pending:
            current = pending.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            if (
                current.aggregates
                or current.fields
                or (
                    symbolic
                    and (current.parameters or current.projections or current.context_limited)
                )
                or any(
                    target in self.sources.definitions
                    or target in self.sources.records
                    or target in self.sources.module_paths
                    or PythonConsumption.kind(target)
                    or PythonConsumption.module_kinds(target)
                    for target in current.targets
                )
            ):
                return True
            pending.extend(current.items or ())
            pending.extend(item for _, item in current.entries or ())
            pending.extend(method.receiver for method in current.methods)
            if current.element is not None:
                pending.append(current.element)
        return False

    def retained_transfer(self, roots: list[BindingValue], scope: BindingScope) -> bool:
        """Distinguish live capture custody from not-yet-published local allocations."""
        return any(
            owner.member_binding(identity, later=later) is not None
            for identity, owners in self.reachable([(value, scope) for value in roots]).items()
            for owner in owners.values()
            for later in (False, True)
        )

    def reachable(
        self,
        roots: list[tuple[BindingValue, BindingScope]],
        *,
        target: BindingScope | None = None,
        later: bool | None = None,
    ) -> dict[str | AggregateIdentity, dict[int, BindingScope]]:
        """Retain all scope-qualified witnesses; do not choose the first captured snapshot."""
        retained: dict[str | AggregateIdentity, dict[int, BindingScope]] = defaultdict(dict)
        seen_values, seen_calls, seen_requests = set(), set(), set()
        pending = list(roots)
        captures: list[tuple[FunctionDefinition, BindingScope]] = []
        while pending or captures:
            if captures:
                definition, environment = captures.pop()
                site = definition.key, id(environment)
                if site in seen_calls:
                    continue
                seen_calls.add(site)
                pending.extend(self.capture_roots(definition, environment))
                continue
            value, scope = pending.pop()
            site = self.reachability_key(value), id(scope)
            if site in seen_values or not (
                value.aggregates
                or value.targets
                or value.projections
                or value.items
                or value.entries
                or value.fields
                or value.methods
                or value.element is not None
            ):
                continue
            seen_values.add(site)
            for key in (key for key in value.aggregates if id(scope) not in retained[key]):
                retained[key][id(scope)] = scope
                pending.extend(
                    (item, scope) for item in self.member_values(key, scope, target, later=later)
                )
            value = self.inline_value(value, target)
            pending.extend((item, scope) for item in value.items or ())
            pending.extend((method.receiver, scope) for method in value.methods)
            pending.extend(
                (item, scope) for _, item in (*(value.entries or ()), *(value.fields or ()))
            )
            pending.extend((item, scope) for item in (value.element,) if item is not None)
            for name in value.targets:
                definition = self.sources.definitions.get(name)
                if definition is not None:
                    captures.append((definition, definition.parent))
                pending.extend(self.record_roots(name, scope))
            for projection in (item for item in value.projections if item.key not in seen_requests):
                seen_requests.add(projection.key)
                request = self.sources.invocations.requests[projection.key]
                pending.extend((item, request.caller) for item in request.arguments)
                pending.extend((item, request.caller) for item in request.keywords.values())
                if request.returned is not None:
                    pending.append((request.returned, request.caller))
                captures.append((request.definition, request.parent))
        return dict(retained)

    @staticmethod
    def reachability_key(
        value: BindingValue,
    ) -> int | tuple[frozenset[AggregateIdentity], frozenset[str], frozenset[int]]:
        """Equal resource leaves share custody; inline owners retain object identity."""
        if (
            value.items
            or value.entries
            or value.fields
            or value.methods
            or value.element is not None
        ):
            return id(value)
        return value.aggregates, value.targets, frozenset(item.key for item in value.projections)

    @staticmethod
    def inline_value(value: BindingValue, target: BindingScope | None) -> BindingValue:
        """Live allocations select their heap edges instead of copied inline edges."""
        return (
            replace(value, items=None, entries=None, fields=None, element=None)
            if target is not None and value.aggregates
            else value
        )

    @staticmethod
    def member_values(
        key: AggregateIdentity,
        source: BindingScope,
        target: BindingScope | None,
        *,
        later: bool | None,
    ) -> tuple[BindingValue, ...]:
        """Follow live graph edges; only missing current custody permits owner history."""
        current = target.member_binding(key, later=bool(later)) if target else None
        if later is not None:
            return (current if current is not None else source.member(key, later=later),)
        if current is None:
            return source.member(key), source.member(key, later=True)
        history = target.member_binding(key, later=True) if target else None
        return (current, history) if history is not None else (current,)

    @staticmethod
    def capture_roots(
        definition: FunctionDefinition, environment: BindingScope
    ) -> list[tuple[BindingValue, BindingScope]]:
        """Follow free cells and defaults in the callable's actual captured environment."""
        lexical = definition.flow.lexical.for_node(definition.node)
        roots = [
            (environment.lookup(name, later=later), environment)
            for name in lexical.free | lexical.globals | lexical.nonlocals
            for later in (False, True)
        ]
        roots.extend(
            (parameter.default, environment)
            for parameter in definition.signature.parameters.values()
            if isinstance(parameter.default, BindingValue)
        )
        return roots

    def record_roots(
        self, target: str, scope: BindingScope
    ) -> list[tuple[BindingValue, BindingScope]]:
        """Record defaults and declared methods retain their constructor ownership."""
        record = self.sources.records.get(target)
        if record is None:
            return []
        roots = [
            (parameter.default, record.owner)
            for parameter in record.signature.parameters.values()
            if isinstance(parameter.default, BindingValue)
        ]
        roots.extend(
            (owner.member(key), owner)
            for key in record.owner.members.keys() | record.owner.member_history.keys()
            if isinstance(key, str) and key.startswith(f"{target}.")
            for owner in (scope, record.owner)
        )
        return roots

    def invalidate(self, scope: BindingScope, *values: BindingValue) -> None:
        """An opaque callable or record escape havocs its captures, not unrelated closures."""
        retained = self.reachable([(value, scope) for value in values])
        for key, owners in retained.items():
            scope.assign_member(key, BindingValue(unknown=True))
            for owner in owners.values():
                owner.assign_member(key, BindingValue(unknown=True))

    def publish(self, value: BindingValue, source: BindingScope, target: BindingScope) -> None:
        """Make missing returned allocations visible without rolling back live state."""
        for key, owners in self.reachable([(value, source)], target=target).items():
            if not isinstance(key, AggregateIdentity) or target.member_binding(key) is not None:
                continue
            for later, mapping in ((False, target.members), (True, target.member_history)):
                if target.member_binding(key, later=later) is not None:
                    continue
                observed = BindingValue()
                for owner in owners.values():
                    observed = observed.join(owner.member(key, later=later))
                mapping[key] = observed

    @staticmethod
    def contained(value: BindingValue, base: BindingScope) -> bool:
        """Certify inline edges against present call-time current and history custody."""
        pending, seen = [value], set()
        while pending:
            current = pending.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            if (
                current.targets
                or current.projections
                or current.parameters
                or current.methods
                or current.deferred
                or current.unknown
                or current.spread
                or current.context_limited
                or any(
                    key not in base.members or key not in base.member_history
                    for key in current.aggregates
                )
            ):
                return False
            pending.extend(current.items or ())
            pending.extend(item for _, item in (*(current.entries or ()), *(current.fields or ())))
            if current.element is not None:
                pending.append(current.element)
        return True

    @staticmethod
    def reconcile(
        invocation: SourceInvocation,
        outgoing: list[tuple[BindingScope, dict[str | AggregateIdentity, dict[int, BindingScope]]]],
        keys: set[str | AggregateIdentity],
        original: set[str | AggregateIdentity],
    ) -> None:
        """Join path-local effects without rolling back later live-caller changes."""
        caller = invocation.caller
        for key in keys:
            for later, mapping in ((False, caller.members), (True, caller.member_history)):
                value = BindingValue()
                for scope, retained in outgoing:
                    if key in original and scope.member(
                        key, later=later
                    ) == invocation.state.member(key, later=later):
                        value = value.join(caller.member(key, later=later))
                        continue
                    owners = (
                        (scope,)
                        if key in scope.members or key in scope.member_history
                        else tuple(retained.get(key, {}).values()) or (caller,)
                    )
                    for owner in owners:
                        value = value.join(owner.member(key, later=later))
                mapping[key] = value

    def transfer(
        self, invocation: SourceInvocation, paths: tuple[FlowExit, ...], returned: BindingValue
    ) -> None:
        """Reconcile witnessed local deltas and explicit exports; unknown ancestry stays full."""
        caller, base = invocation.caller, invocation.state
        lexical = invocation.definition.flow.lexical.for_node(invocation.definition.node)
        for name in lexical.outer_writes:
            value = BindingValue()
            destination = None
            for path in paths:
                owner = path.scope.outer(name)
                environment = self.namespace(owner, invocation.definition.parent)
                destination = self.namespace(environment, caller)
                value = value.join(owner.lookup(name))
            if destination is not None:
                destination.assign(name, value)
        original = caller.members.keys() | caller.member_history.keys()
        outgoing = []
        keys = set()
        for path in paths:
            scope = path.scope
            available = {
                key
                for key in scope.members.keys() | scope.member_history.keys()
                if isinstance(key, str) or key in original
            }
            changed = set(original)
            selected = available
            if scope.member_base is base:
                changed = {
                    key
                    for key in original | available
                    if scope.members.get(key) != base.members.get(key)
                    or scope.member_history.get(key) != base.member_history.get(key)
                }
                changed.update(scope.summarized ^ base.summarized)
                selected = {
                    key
                    for key in available
                    if key in changed
                    or any(
                        not self.contained(scope.member(key, later=later), base)
                        for later in (False, True)
                    )
                }
            roots = [
                (returned, scope),
                *((item, scope) for item in invocation.arguments),
                *((item, scope) for item in invocation.keywords.values()),
                *((scope.outer(name).lookup(name), scope) for name in lexical.outer_writes),
                *self.capture_roots(invocation.definition, scope),
            ]
            roots.extend(
                (scope.member(key, later=later), scope)
                for key in selected
                for later in (False, True)
            )
            retained = self.reachable(roots)
            outgoing.append((scope, retained))
            keys.update(changed & original)
            keys.update(key for key in scope.members if isinstance(key, str))
            keys.update(retained)
        self.reconcile(invocation, outgoing, keys, original)
        caller.summarized.update(
            key for scope, _ in outgoing for key in scope.summarized if key in keys
        )


def effect_dependencies(
    invocations: PythonInvocations,
    summary: EffectSummary,
    key: str,
    arguments: dict[str, BindingValue],
    caller: BindingScope,
    result: PythonConsumption,
) -> tuple[
    list[
        tuple[
            FunctionDefinition,
            tuple[BindingValue, ...],
            dict[str | None, BindingValue],
            BindingScope,
        ]
    ],
    bool,
]:
    """Instantiate each call edge independently of known and opaque alternatives."""
    pending = []
    for call in summary.calls:
        scope = supplied(caller, call.custody)
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
            (invocations.sources.definitions[target], values, named_values, scope)
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

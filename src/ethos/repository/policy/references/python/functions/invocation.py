"""Invocation-local return demand and shared native-effect dependency observation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingScope
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ReturnProjection
from ethos.repository.policy.references.python.control import FlowExit
from ethos.repository.policy.references.python.control import PythonControlFlow
from ethos.repository.policy.references.python.functions.custody import InvocationCustody
from ethos.repository.policy.references.python.functions.custody import effect_dependencies
from ethos.repository.policy.references.python.functions.effects import EffectCall
from ethos.repository.policy.references.python.functions.effects import EffectSummary
from ethos.repository.policy.references.python.functions.effects import MemberRead
from ethos.repository.policy.references.python.functions.effects import bound_arguments
from ethos.repository.policy.references.python.functions.effects import held
from ethos.repository.policy.references.python.functions.effects import observe_calls
from ethos.repository.policy.references.python.functions.effects import project
from ethos.repository.policy.references.python.functions.effects import substitute
from ethos.repository.policy.references.python.functions.effects import symbolic_arguments

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import MemberDemand
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.flow import PythonReferenceFlow
    from ethos.repository.policy.references.python.functions.returns import FunctionDefinition
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@dataclass(slots=True)
class SourceInvocation:
    """One call's actual arguments, lexical frame and program-point custody."""

    definition: FunctionDefinition
    arguments: tuple[BindingValue, ...]
    keywords: dict[str | None, BindingValue]
    node: ast.Call
    caller: BindingScope
    parent: BindingScope
    returned: BindingValue | None = None
    invalidated: bool = False
    state: BindingScope = field(init=False)

    def __post_init__(self) -> None:
        """Retain call-time heap reads separately from the live effect destination."""
        self.state = self.caller.fork()


@dataclass(slots=True)
class PythonInvocations:
    """Reuse exact source dependencies, not authorization or mutable concrete answers."""

    sources: PythonSourceReturns
    requests: list[SourceInvocation] = field(default_factory=list)
    summaries: dict[str, EffectSummary] = field(default_factory=dict)
    summarizing: list[str] = field(default_factory=list)
    active: list[str] = field(default_factory=list)
    demands: int = 0
    resolution_depth: int = 0
    validating: int = 0
    custody: InvocationCustody = field(init=False)

    def __post_init__(self) -> None:
        """Share one reachable-resource owner with invalidation and return transfer."""
        self.custody = InvocationCustody(self.sources)

    @staticmethod
    def snapshot(scope: BindingScope) -> BindingScope:
        """Capture lexical program points before later assignments can alter a lazy call."""
        captured = scope.fork()
        if scope.parent is not None:
            captured.parent = PythonInvocations.snapshot(scope.parent)
        return captured

    def read(self, scope: BindingScope, name: str) -> BindingValue:
        """Record actual lexical dependencies while retaining native binding precision."""
        read = scope.read(name)
        value = self.custody.resolve(read.value, read.namespace, scope, later=read.later)
        for key in self.summarizing if not self.validating else ():
            frame: BindingScope | None = self.sources.definitions[key].parent
            while frame is not None and frame.identity != read.namespace.identity:
                frame = frame.parent
            if frame is not None:
                namespace = self.custody.namespace(
                    read.namespace, self.sources.definitions[key].parent
                )
                read = replace(read, namespace=namespace, value=self.custody.witness(read.value))
                self.summaries[key].reads[(namespace.identity, name, read.later)] = read
        return value

    def summary_for(
        self, definition: FunctionDefinition, result: PythonConsumption, scope: BindingScope
    ) -> EffectSummary:
        """Reuse only a summary whose transitive lexical and heap inputs remain equal."""
        summary = self.summaries.get(definition.key)
        if definition.key not in self.summarizing and (
            summary is None
            or (summary.context_limited and summary.context_depth > 0 and not self.summarizing)
            or not self.custody.unchanged(summary, scope, result)
        ):
            self.summarize(definition, result, scope)
        return self.summaries[definition.key]

    def note_member(
        self, subject: BindingValue, demand: MemberDemand, value: BindingValue, scope: BindingScope
    ) -> None:
        """Track consumed external members without expanding unrelated heap siblings."""
        if self.summarizing and not self.validating and (subject.aggregates or subject.targets):
            parent = self.sources.definitions[self.summarizing[-1]].parent
            namespace = self.custody.namespace(parent, scope)
            later = scope.deferred_outer
            if subject.targets or all(
                namespace.member_binding(identity, later=later) is not None
                for identity in subject.aggregates
            ):
                subject = self.custody.witness(subject)
                read = MemberRead(namespace, subject, demand, self.custody.witness(value), later)
                for key in self.summarizing:
                    self.summaries[key].members[(namespace.identity, later, subject, demand)] = read

    def request(
        self,
        definition: FunctionDefinition,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.Call,
        caller: BindingScope,
        result: PythonConsumption,
    ) -> BindingValue:
        """A source call preserves return demand independently of its transitive effects."""
        if self.summarizing:
            summary = self.summaries[self.summarizing[-1]]
            summary.record(
                EffectCall(
                    BindingValue(targets=frozenset({definition.key})),
                    args,
                    keywords,
                    node,
                    result.path,
                    caller.name,
                    held(self.custody, (*args, *keywords.values()), caller),
                )
            )
            selected = self.summary_for(definition, result, caller)
            summary.reads.update(selected.reads)
            summary.members.update(selected.members)
            summary.context_limited = summary.context_limited or selected.context_limited
            arguments = bound_arguments(definition, args, keywords)
            if caller.deferred_outer and selected.observation is not None and arguments is not None:
                observe_calls(
                    selected, arguments, caller, self.sources, result, owner=definition.key
                )
            return (
                substitute(
                    selected.returned,
                    arguments,
                    caller,
                    self.sources,
                    result,
                    owner=definition.key,
                )
                if arguments is not None
                else BindingValue(unknown=True)
            )
        index = len(self.requests)
        self.requests.append(
            SourceInvocation(
                definition,
                args,
                keywords,
                node,
                caller,
                self.snapshot(self.custody.namespace(definition.parent, caller)),
            )
        )
        if self.effectful(definition, args, keywords, caller, result):
            self.materialize(index, result)
        return BindingValue(projections=frozenset({ReturnProjection(index)}))

    def note_call(
        self,
        callee: BindingValue,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.expr,
        path: str,
        scope: BindingScope,
    ) -> None:
        """Preserve callback holes without calling every deferred method effectful."""
        if self.summarizing and (
            callee.selection
            or (callee.unknown and callee.deferred)
            or any(
                self.custody.mutable(value, symbolic=True)
                for value in (callee, *args, *keywords.values())
            )
        ):
            self.summaries[self.summarizing[-1]].record(
                EffectCall(callee, args, keywords, node, path, scope.name)
            )

    def note_mutation(
        self, scope: BindingScope, *values: BindingValue, native_store: bool = False
    ) -> None:
        """Record symbolic roots before an opaque escape havocs nested concrete custody."""
        if not self.summarizing:
            return
        summary = self.summaries[self.summarizing[-1]]
        summary.direct = summary.direct or native_store
        pending, seen = list(values), set()
        while pending:
            value = pending.pop()
            if id(value) in seen:
                continue
            seen.add(id(value))
            if value.parameters:
                summary.footprints.append(value)
            elif (value.targets and self.custody.mutable(value)) or value.aggregates & (
                scope.parent.members.keys() if scope.parent else set()
            ):
                summary.direct = True
            pending.extend(value.items or ())
            pending.extend(method.receiver for method in value.methods)
            pending.extend(item for _, item in (*(value.entries or ()), *(value.fields or ())))
            if value.element is not None:
                pending.append(value.element)

    def effectful(
        self,
        definition: FunctionDefinition,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        scope: BindingScope,
        result: PythonConsumption,
    ) -> bool:
        """Follow actual binding dependencies, never a syntactic scan of owner spelling."""
        pending = [(definition, args, keywords, scope)]
        visited = set()
        while pending:
            current, actual, named, context_scope = pending.pop()
            key = current.key
            summary = self.summary_for(current, result, context_scope)
            context = (
                key,
                actual,
                tuple(named.items()),
                tuple(read.value for read in summary.reads.values()),
            )
            if context in visited:
                continue
            visited.add(context)
            if len(visited) > 128:
                return True
            if summary.direct:
                return True
            arguments = bound_arguments(current, actual, named)
            if arguments is None:
                return True
            for footprint in summary.footprints:
                value = substitute(
                    footprint, arguments, context_scope, self.sources, result, owner=key
                )
                if self.custody.mutable(value):
                    return True
            called, uncertain = effect_dependencies(
                self, summary, key, arguments, context_scope, result
            )
            if uncertain:
                return True
            pending.extend(called)
        return False

    def summarize(
        self,
        definition: FunctionDefinition,
        result: PythonConsumption,
        scope: BindingScope | None = None,
    ) -> None:
        """Observe a definition once with symbolic runtime arguments and shared lexical flow."""
        summary = EffectSummary(context_depth=len(self.active) if self.summarizing else 0)
        self.summaries[definition.key] = summary
        caller = scope if scope is not None else definition.parent
        invocation = SourceInvocation(
            definition,
            (),
            {},
            ast.Call(
                func=ast.Name(id="<source>"),
                args=[],
                keywords=[],
                lineno=definition.node.lineno,
                col_offset=definition.node.col_offset,
            ),
            caller,
            self.snapshot(self.custody.namespace(definition.parent, caller)),
        )
        observer = type(result)(definition.flow.path, result.npm_scripts, sources=self.sources)
        active = self.active
        if not self.summarizing:
            self.active = []
        self.summarizing.append(definition.key)
        try:
            summary.returned = self.evaluate(invocation, observer)
        finally:
            self.summarizing.pop()
            self.active = active
        summary.direct = summary.direct or bool(
            observer.executables or observer.inputs or observer.uncertainties
        )
        summary.direct = summary.direct or bool(
            definition.flow.lexical.for_node(definition.node).outer_writes
        )
        summary.observation = observer

    def materialize(self, index: int, result: PythonConsumption) -> BindingValue:
        """Evaluate one actual call once; reachable values remain subject to later mutation."""
        invocation = self.requests[index]
        if invocation.returned is None:
            invocation.returned = self.evaluate(invocation, result)
        value = invocation.returned
        if invocation.invalidated:
            invocation.caller.invalidate_aggregates(value)
            value = value.join(BindingValue(unknown=True))
        return value

    def invalidate(
        self, scope: BindingScope, *values: BindingValue, conditional: bool = False
    ) -> None:
        """Opaque escapes invalidate lazy object dependencies without eagerly expanding them."""
        if not conditional:
            self.note_mutation(scope, *values)
        self.custody.invalidate(scope, *values)
        pending, seen = list(values), set()
        while pending:
            value = pending.pop()
            if id(value) in seen:
                continue
            seen.add(id(value))
            for projection in value.projections:
                self.requests[projection.key].invalidated = True
            pending.extend(value.items or ())
            pending.extend(method.receiver for method in value.methods)
            pending.extend(item for _, item in value.fields or ())
            pending.extend(item for _, item in value.entries or ())

    def resolve(
        self,
        value: BindingValue,
        scope: BindingScope,
        result: PythonConsumption,
        *,
        deep: bool = True,
    ) -> BindingValue:
        """Keep one finite demand budget across lazy calls and recursive aggregate reads."""
        if self.resolution_depth >= 128:
            return BindingValue(unknown=True, context_limited=True)
        root_demand = not self.active and not self.resolution_depth and not self.summarizing
        if root_demand:
            self.demands = 0
        self.resolution_depth += 1
        try:
            return self.resolve_value(value, scope, result, deep=deep)
        finally:
            self.resolution_depth -= 1
            if root_demand:
                self.demands = 0

    def resolve_value(
        self,
        value: BindingValue,
        scope: BindingScope,
        result: PythonConsumption,
        *,
        deep: bool = True,
    ) -> BindingValue:
        """Resolve selected members before expanding their demanded structure."""
        value = scope.resolve(value)
        current = replace(value, projections=frozenset()) if value.projections else value
        if self.summarizing and value.projections:
            return current.join(BindingValue(deferred=True, context_limited=True))
        for projection in value.projections:
            request = self.requests[projection.key]
            resolved = self.materialize(projection.key, result)
            if request.caller is not scope:
                self.custody.publish(resolved, request.caller, scope)
            if resolved.aggregates and all(
                scope.member(identity) != BindingValue() for identity in resolved.aggregates
            ):
                resolved = scope.resolve(resolved)
            for member in projection.members:
                resolved = project(resolved, member, scope, self.sources, result)
                if resolved.projections:
                    resolved = self.resolve(resolved, request.caller, result, deep=deep)
            if resolved.projections:
                resolved = self.resolve(resolved, request.caller, result, deep=deep)
                self.custody.publish(resolved, request.caller, scope)
            current = current.join(resolved)
        if not deep or not (current.items or current.fields):
            return current
        items = (
            tuple(self.resolve(item, scope, result) for item in current.items)
            if current.items is not None
            else None
        )
        fields = (
            tuple((name, self.resolve(item, scope, result)) for name, item in current.fields)
            if current.fields is not None
            else None
        )
        if (
            items is None
            or all(
                before is after for before, after in zip(current.items or (), items, strict=True)
            )
        ) and (
            fields is None
            or all(
                before is after
                for (_, before), (_, after) in zip(current.fields or (), fields, strict=True)
            )
        ):
            return current
        return replace(current, items=items, fields=fields)

    def bounded_return(
        self, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        """Carry unresolved values to native consumers without inventing another effect kind."""
        definition = invocation.definition
        if self.summarizing:
            self.summaries[self.summarizing[-1]].context_limited = True
        else:
            summary = self.summary_for(definition, result, invocation.caller)
            arguments = bound_arguments(definition, invocation.arguments, invocation.keywords)
            if arguments is None:
                arguments = dict.fromkeys(
                    symbolic_arguments(definition), BindingValue(unknown=True)
                )
            observe_calls(
                summary,
                arguments,
                invocation.caller,
                self.sources,
                result,
                owner=definition.key,
                transitive=True,
            )
        return BindingValue(deferred=bool(self.summarizing), unknown=True, context_limited=True)

    def evaluate(self, invocation: SourceInvocation, result: PythonConsumption) -> BindingValue:
        """Instantiate the same terminal-aware flow under a local dependency bound."""
        definition, args, keywords = (
            invocation.definition,
            invocation.arguments,
            invocation.keywords,
        )
        if (
            definition.key in self.active
            or (not self.summarizing and len(self.active) >= 8)
            or (not self.summarizing and self.demands >= 128)
            or None in keywords
            or any(value.spread for value in args)
        ):
            return self.bounded_return(invocation, result)
        bound = (
            symbolic_arguments(definition)
            if self.summarizing and self.summarizing[-1] == definition.key
            else bound_arguments(definition, args, keywords)
        )
        if bound is None:
            return BindingValue(unknown=True)
        lexical = definition.flow.lexical.for_node(definition.node)
        child = BindingScope(
            f"{invocation.parent.name}.{getattr(definition.node, 'name', '<lambda>')}",
            invocation.parent,
            lexical.locals,
            lexical.globals,
            lexical.nonlocals,
            members=dict(invocation.state.members),
            member_history=dict(invocation.state.member_history),
            member_base=invocation.state,
            deferred_outer=invocation.caller.deferred_outer,
            allocation_context=(
                *invocation.caller.allocation_context,
                (invocation.node.lineno, invocation.node.col_offset, len(self.requests)),
            ),
        )
        for name, value in bound.items():
            child.assign(name, value)
        summary = self.summaries.get(definition.key) if not self.summarizing else None
        cache_key = (
            self.custody.return_inputs(summary, bound, child) if summary is not None else None
        )
        if (
            summary is not None
            and cache_key is not None
            and not self.custody.unchanged(summary, child, result)
        ):
            cache_key = None
        if summary is not None and cache_key in summary.answers:
            return summary.answers[cache_key]
        flow = self.sources.factory(definition.flow.path, result.npm_scripts, sources=self.sources)
        flow.lexical, flow.result = (
            definition.flow.lexical,
            type(result)(definition.flow.path, result.npm_scripts, sources=self.sources),
        )
        root_demand = not self.active and not self.resolution_depth and not self.summarizing
        if root_demand:
            self.demands = 0
        self.active.append(definition.key)
        self.demands += not bool(self.summarizing)
        try:
            returned = self.return_values(invocation, flow, child)
        finally:
            self.active.pop()
            if root_demand:
                self.demands = 0
        result.absorb(flow.result)
        returned = returned if returned != BindingValue() else BindingValue(local=True)
        if (
            summary is not None
            and cache_key is not None
            and self.custody.unchanged(summary, invocation.caller, result)
            and len(summary.answers) < 64
            and not (
                flow.result.imports
                or flow.result.import_sites
                or flow.result.executables
                or flow.result.inputs
                or flow.result.uncertainties
                or returned.targets
                or returned.methods
                or self.custody.mutable(returned, symbolic=True)
            )
        ):
            summary.answers[cache_key] = returned
        return returned

    def return_values(
        self, invocation: SourceInvocation, flow: PythonReferenceFlow, child: BindingScope
    ) -> BindingValue:
        """Join only successful exits after finalization and carry mutable custody back."""
        definition = invocation.definition
        if isinstance(definition.node, ast.Lambda):
            paths = (FlowExit(child, "return", flow.expression(definition.node.body, child)),)
        else:
            paths = PythonControlFlow(flow).block(definition.node.body, child)
        successful = [path for path in paths if path.kind in {"normal", "return"}]
        returned = BindingValue()
        for path in successful:
            value = path.value if path.kind == "return" else BindingValue(local=True)
            returned = returned.join(path.scope.resolve(value))
        if paths and not self.summarizing:
            self.custody.transfer(invocation, paths, returned)
        return returned

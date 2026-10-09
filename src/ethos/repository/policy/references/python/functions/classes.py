"""Closed ordinary class namespaces, descriptor precedence and instance allocation."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ReceiverMethod
from ethos.repository.policy.references.python.functions.escape import immutable_native_value

if TYPE_CHECKING:
    import ast

    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.flow import PythonReferenceFlow
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
    from ethos.repository.policy.references.python.scope import BindingScope

_OBJECT_LOOKUP_HOOKS = frozenset(
    {"__new__", "__getattribute__", "__getattr__", "__setattr__", "__delattr__", "__bases__"}
)


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    """An exact ordinary class namespace with native object lookup and initialization."""

    namespace: BindingScope


@dataclass(slots=True)
class PythonClasses:
    """Class state has one owner; source calls and lexical custody retain theirs."""

    sources: PythonSourceReturns
    definitions: dict[str, ClassDefinition] = field(default_factory=dict)

    def value(
        self,
        flow: PythonReferenceFlow,
        node: ast.ClassDef,
        parent: BindingScope,
        namespace: BindingScope,
    ) -> BindingValue:
        """Use generated record contracts or proven native object lookup, not class spelling."""
        if self.sources.record_kind(flow, node, parent):
            return self.sources.record(flow, node, parent)
        if (
            node.bases
            or node.keywords
            or node.decorator_list
            or _OBJECT_LOOKUP_HOOKS & namespace.values.keys()
        ):
            return BindingValue(local=True)
        key = f"{flow.path}:{node.lineno}:{node.col_offset}:{node.name}:{len(self.definitions)}"
        self.definitions[key] = ClassDefinition(namespace)
        parent.assign_member(key, BindingValue(fields=tuple(namespace.values.items())))
        return BindingValue(targets=frozenset({key}))

    def state(self, target: str, scope: BindingScope, *, later: bool = False) -> BindingValue:
        """Read class namespace custody at the call site, falling back only for missing custody."""
        value = scope.member_binding(target, later=later)
        if value is not None:
            return value
        parent = self.definitions[target].namespace.parent
        return parent.member(target, later=later) if parent else BindingValue(unknown=True)

    def store(
        self,
        target: str,
        name: str,
        value: BindingValue,
        scope: BindingScope,
        *,
        strong: bool,
    ) -> bool:
        """Replace one closed class owner; a may-owner retains the unselected member."""
        if target not in self.definitions:
            return False
        state = self.state(target, scope)
        fields = dict(state.fields or ())
        fields[name] = value if strong else fields.get(name, BindingValue(unknown=True)).join(value)
        scope.assign_member(target, replace(state, fields=tuple(fields.items())))
        return True

    @staticmethod
    def native_lookup(state: BindingValue) -> bool:
        """Only a closed current namespace without custom object hooks proves native lookup."""
        return (
            state.fields is not None
            and not (state.unknown or state.local or state.deferred)
            and not _OBJECT_LOOKUP_HOOKS.intersection(name for name, _ in state.fields)
        )

    def instance_storage(self, owner: BindingValue, name: str, scope: BindingScope) -> bool:
        """Instance fields require native lookup and proven absence of a data descriptor."""
        if name in {"__class__", "__dict__", "__weakref__"} or not owner.instance_types:
            return False
        for target in owner.instance_types:
            if target not in self.definitions:
                return False
            state = self.state(target, scope)
            if not self.native_lookup(state):
                return False
            value = dict(state.fields or ()).get(name)
            if value is not None and not self.non_data_member(value, scope):
                return False
        return True

    def non_data_member(self, value: BindingValue, scope: BindingScope) -> bool:
        """Only closed native values or exact source types prove field-store precedence."""
        value = self.sources.call_identity(scope.resolve(value))
        if (
            value.unknown
            or value.local
            or value.deferred
            or value.projections
            or value.parameters
            or value.selection
            or value.targets - (self.sources.definitions.keys() | self.definitions.keys())
        ):
            return False
        if value.instance_types:
            return all(
                target in self.definitions
                and self.native_lookup(state := self.state(target, scope))
                and not {"__set__", "__delete__"}.intersection(
                    name for name, _ in state.fields or ()
                )
                for target in value.instance_types
            )
        return bool(
            value.targets
            or value.methods
            or value.native_kind
            or value.entries is not None
            or immutable_native_value(value)
        )

    def member(
        self, target: str, name: str, receiver: BindingValue, scope: BindingScope
    ) -> BindingValue:
        """Bind the actual function at lookup; instance-written callables stay unbound."""
        state = self.state(target, scope)
        if not self.native_lookup(state):
            return BindingValue(unknown=True, selection=frozenset({target}))
        value = self.sources.call_identity(
            scope.resolve(dict(state.fields or ()).get(name, BindingValue(unknown=True)))
        )
        if value.instance_types:
            return replace(value, unknown=True, selection=value.selection | {target})
        if value.unknown or value.local or value.deferred:
            value = replace(value, selection=value.selection | {target})
        bound = replace(value, targets=frozenset())
        for identity in value.targets:
            definition = self.sources.definitions.get(identity)
            if definition is not None and definition.binding == "class":
                actual = BindingValue(targets=frozenset({target}))
            elif (
                definition is not None
                and definition.binding not in {"static", "class"}
                and receiver.instance_types
            ):
                actual = receiver
            else:
                bound = bound.join(BindingValue(targets=frozenset({identity})))
                continue
            bound = bound.join(BindingValue(methods=frozenset({ReceiverMethod(actual, identity)})))
        return bound

    def construct(
        self,
        target: str,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        scope: BindingScope,
        node: ast.Call,
        result: PythonConsumption,
    ) -> BindingValue:
        """Initialize one native-object allocation through its actual source callable."""
        instance = scope.aggregate(
            BindingValue(fields=(), instance_types=frozenset({target})), node
        )
        state = self.state(target, scope)
        if not self.native_lookup(state):
            result.call(
                BindingValue(unknown=True, selection=frozenset({target})),
                args,
                keywords,
                node,
                scope,
            )
            return instance.join(BindingValue(unknown=True))
        initializer = dict(state.fields or ()).get("__init__")
        if initializer is None:
            return (
                instance if not args and not keywords else instance.join(BindingValue(unknown=True))
            )
        member = self.member(target, "__init__", instance, scope)
        returned = self.sources.call(member, args, keywords, node, scope, result)
        if returned is None:
            result.call(member, args, keywords, node, scope)
            return instance.join(BindingValue(unknown=True))
        self.sources.invocations.resolve(returned, scope, result, deep=False)
        return scope.resolve(instance)

"""Finite abstract values and ordered lexical environments for Python references."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Literal
from typing import TypedDict


class ReferenceUncertaintyRecord(TypedDict):
    """The JSON observation retains its exact obligation, state and program point."""

    kind: Literal["import", "executable", "value"]
    state: Literal["unknown", "deferred"]
    path: str
    scope: str
    line: int
    column: int
    target: str
    reason: str
    identity: str | None


@dataclass(frozen=True, slots=True)
class ImportReference:
    """A complete module/symbol import site, not a distribution-root spelling."""

    module: str
    name: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class AggregateIdentity:
    """A source allocation and its proven finite iteration context."""

    scope: str
    line: int
    column: int
    context: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class MemberDemand:
    """A typed member/index/iteration relationship with an exact or symbolic selector."""

    kind: Literal["attribute", "index", "iterate", "get", "truth", "structure", "iteration_shape"]
    key: str | int | None = None
    selector: BindingValue | None = None
    default: BindingValue | None = None


@dataclass(frozen=True, slots=True)
class ReturnProjection:
    """An invocation-local return and subsequent member demands, never trusted by name."""

    key: int
    members: tuple[MemberDemand, ...] = ()


@dataclass(frozen=True, slots=True)
class ParameterProjection:
    """A symbolic signature slot and exact members, not an unknown native effect."""

    name: str
    members: tuple[MemberDemand, ...] = ()
    owner: str = ""


@dataclass(frozen=True, slots=True)
class ReceiverMethod:
    """A lookup-time native method and its correlated receiver, preserved through assignment."""

    receiver: BindingValue
    name: str


@dataclass(frozen=True, slots=True)
class BindingValue:
    """Signature projections discharge by owner; independent runtime alternatives survive."""

    targets: frozenset[str] = frozenset()
    strings: frozenset[str] = frozenset()
    truths: frozenset[bool] = frozenset()
    executable_origins: frozenset[str] = frozenset()
    projections: frozenset[ReturnProjection] = frozenset()
    parameters: frozenset[ParameterProjection] = frozenset()
    methods: frozenset[ReceiverMethod] = frozenset()
    instance_types: frozenset[str] = frozenset()
    path: bool = False
    items: tuple[BindingValue, ...] | None = None
    entries: tuple[tuple[str, BindingValue], ...] | None = None
    mapping_shapes: frozenset[tuple[tuple[str, BindingValue], ...]] | None = None
    fields: tuple[tuple[str, BindingValue], ...] | None = None
    optional_fields: frozenset[str] = frozenset()
    element: BindingValue | None = None
    ordered: bool = False
    aggregates: frozenset[AggregateIdentity] = frozenset()
    allocation_complete: bool = False
    view: str = ""
    selection: frozenset[str] = frozenset()
    local: bool = False
    deferred: bool = False
    unknown: bool = False
    spread: bool = False
    native_kind: Literal["", "list"] = ""
    context_limited: bool = False

    def join(self, other: BindingValue) -> BindingValue:
        """Join may-values without choosing a winner or erasing a residual."""
        if self is other or self == other:
            return self
        if self == BindingValue():
            return other
        if other == BindingValue():
            return self
        items = (
            tuple(left.join(right) for left, right in zip(self.items, other.items, strict=True))
            if self.items is not None
            and other.items is not None
            and len(self.items) == len(other.items)
            else None
        )
        element = (
            self.iterated().join(other.iterated())
            if (self.items is not None or self.element is not None)
            and (other.items is not None or other.element is not None)
            else None
        )
        entries = None
        mapping_shapes = None
        if self.entries is not None and other.entries is not None:
            left, right = dict(self.entries), dict(other.entries)
            entries = tuple(
                (
                    key,
                    left.get(key, BindingValue(unknown=True)).join(
                        right.get(key, BindingValue(unknown=True))
                    ),
                )
                for key in dict.fromkeys((*left, *right))
            )
            mapping_shapes = self.join_mapping_shapes(other)
        fields, optional_fields = self.join_fields(other)
        truths = self.truths | other.truths
        for value in (self, other):
            if not value.aggregates:
                if items is None and value.items is not None:
                    truths |= {bool(value.items)}
                if entries is None and value.entries is not None:
                    truths |= {bool(value.entries)}
        return BindingValue(
            targets=self.targets | other.targets,
            strings=self.strings | other.strings,
            truths=truths,
            executable_origins=self.executable_origins | other.executable_origins,
            projections=self.projections | other.projections,
            parameters=self.parameters | other.parameters,
            methods=self.methods | other.methods,
            instance_types=self.instance_types | other.instance_types,
            path=self.path and other.path,
            items=items,
            entries=entries,
            mapping_shapes=mapping_shapes,
            fields=fields,
            optional_fields=optional_fields,
            element=element,
            ordered=self.ordered
            and other.ordered
            and (
                items is not None
                or (
                    self.entries is not None
                    and other.entries is not None
                    and tuple(key for key, _ in self.entries)
                    == tuple(key for key, _ in other.entries)
                )
            ),
            aggregates=self.aggregates | other.aggregates,
            allocation_complete=self.allocation_complete and other.allocation_complete,
            view=self.view if self.view == other.view else "",
            selection=self.selection | other.selection,
            local=self.local or other.local,
            deferred=self.deferred or other.deferred,
            unknown=self.unknown
            or other.unknown
            or (
                self.entries is not None
                and other.entries is not None
                and {key for key, _ in self.entries} != {key for key, _ in other.entries}
                and mapping_shapes is None
            )
            or (self.view != other.view and bool(self.aggregates | other.aggregates)),
            spread=self.spread or other.spread,
            native_kind=self.native_kind if self.native_kind == other.native_kind else "",
            context_limited=self.context_limited or other.context_limited,
        )

    def join_fields(
        self, other: BindingValue
    ) -> tuple[tuple[tuple[str, BindingValue], ...] | None, frozenset[str]]:
        """Closed instance absence retains live class lookup, not an invented unknown field."""
        optional = self.optional_fields | other.optional_fields
        if self.fields is None and other.fields is None:
            return None, optional
        left, right = dict(self.fields or ()), dict(other.fields or ())
        closed = bool(self.instance_types and other.instance_types) and (
            self.fields is not None and other.fields is not None
        )
        missing = BindingValue() if closed else BindingValue(unknown=True)
        if closed:
            optional |= left.keys() ^ right.keys()
        return tuple(
            (name, left.get(name, missing).join(right.get(name, missing)))
            for name in dict.fromkeys((*left, *right))
        ), optional

    def closed_mapping_shapes(self) -> frozenset[tuple[tuple[str, BindingValue], ...]]:
        """Keep finite key presence alternatives distinct from open mapping contents."""
        return self.mapping_shapes or (
            frozenset({self.entries}) if self.entries is not None else frozenset()
        )

    def join_mapping_shapes(
        self, other: BindingValue
    ) -> frozenset[tuple[tuple[str, BindingValue], ...]] | None:
        """Retain bounded native allocations without inventing closed topology for opaque values."""
        if (
            not (self.aggregates or other.aggregates)
            or self.unknown
            or other.unknown
            or self.deferred
            or other.deferred
        ):
            return None
        shapes = self.closed_mapping_shapes() | other.closed_mapping_shapes()
        topologies = {tuple(name for name, _ in shape) for shape in shapes}
        return shapes if len(topologies) > 1 and len(shapes) <= 64 else None

    def concatenate(self, other: BindingValue) -> BindingValue:
        """Bound literal alternatives while retaining loss of value precision."""
        if self.items is not None and other.items is not None:
            return BindingValue(items=self.items + other.items)
        if len(self.strings) * len(other.strings) <= 64:
            return BindingValue(
                strings=frozenset(a + b for a in self.strings for b in other.strings),
                deferred=self.deferred or other.deferred,
                unknown=self.unknown or other.unknown,
                context_limited=self.context_limited or other.context_limited,
            )
        return BindingValue(
            deferred=self.deferred or other.deferred,
            unknown=True,
            context_limited=self.context_limited or other.context_limited,
        )

    def iterated(self) -> BindingValue:
        """Retain a finite element join separately from an exact ordered sequence."""
        result = self.element
        if result is None:
            if self.items is None:
                return BindingValue(
                    deferred=self.deferred,
                    unknown=self.unknown or not self.deferred,
                    context_limited=self.context_limited,
                )
            if not self.items:
                return BindingValue()
            result = self.items[0]
            for item in self.items[1:]:
                result = result.join(item)
        return replace(
            result,
            unknown=result.unknown or self.unknown,
            deferred=result.deferred or self.deferred,
            spread=False,
            context_limited=result.context_limited or self.context_limited,
        )

    def truthiness(self) -> bool | None:
        """Join every closed native truth; independent opaque alternatives stay open."""
        if (
            self.unknown
            or self.deferred
            or self.parameters
            or self.local
            or self.targets
            or self.projections
            or self.methods
            or self.selection
            or (self.aggregates and self.items is None and self.entries is None)
        ):
            return None
        choices = self.truths | {bool(item) for item in self.strings}
        if self.items is not None:
            choices |= {bool(self.items)}
        if self.entries is not None:
            choices |= {bool(shape) for shape in self.closed_mapping_shapes()}
        return next(iter(choices)) if len(choices) == 1 else None

    def guarded(self, *, truth: bool) -> BindingValue:
        """Narrow finite string alternatives without changing opaque provenance."""
        return replace(
            self, strings=frozenset(item for item in self.strings if bool(item) == truth)
        )

    def selected(self, key: BindingValue) -> BindingValue:
        """Successful finite-map reads preserve all values and opaque owner alternatives."""
        if self.entries is None:
            return BindingValue(
                deferred=self.deferred, unknown=True, context_limited=self.context_limited
            )
        value = BindingValue()
        for shape in self.closed_mapping_shapes():
            entries = dict(shape)
            names = entries if key.unknown or key.deferred or not key.strings else key.strings
            for name in names:
                value = value.join(entries.get(name, BindingValue(unknown=True)))
        return replace(
            value,
            unknown=value.unknown or self.unknown,
            deferred=value.deferred or self.deferred,
            context_limited=value.context_limited or self.context_limited,
        )


@dataclass(frozen=True, slots=True)
class ReferenceUncertainty:
    """One consumer site not statically closed; it is never authorization."""

    kind: Literal["import", "executable", "value"]
    state: Literal["unknown", "deferred"]
    path: str
    scope: str
    line: int
    column: int
    target: str
    reason: str
    identity: str | None = None

    def to_dict(self) -> ReferenceUncertaintyRecord:
        """Expose the exact obligation and provenance to existing report consumers."""
        return {
            "kind": self.kind,
            "state": self.state,
            "path": self.path,
            "scope": self.scope,
            "line": self.line,
            "column": self.column,
            "target": self.target,
            "reason": self.reason,
            "identity": self.identity,
        }

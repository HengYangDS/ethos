"""Program-point lexical namespaces and their mutable allocation custody."""

from __future__ import annotations

import ast
import itertools
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import AggregateIdentity
from ethos.repository.policy.references.python.bindings import BindingValue

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class LexicalRead:
    """One resolved name read retains its supplying namespace and program point."""

    namespace: BindingScope
    name: str
    value: BindingValue
    later: bool


@dataclass(slots=True)
class BindingScope:
    """A program-point namespace plus may-bindings for later function invocation."""

    name: str
    parent: BindingScope | None = None
    locals: frozenset[str] = frozenset()
    globals: frozenset[str] = frozenset()
    nonlocals: frozenset[str] = frozenset()
    values: dict[str, BindingValue] = field(default_factory=dict)
    history: dict[str, BindingValue] = field(default_factory=dict)
    members: dict[str | AggregateIdentity, BindingValue] = field(default_factory=dict)
    deferred_outer: bool = False
    kind: str = "function"
    wildcard: bool = False
    member_history: dict[str | AggregateIdentity, BindingValue] = field(default_factory=dict)
    allocation_context: tuple[tuple[int, int, int], ...] = ()
    summarized: set[AggregateIdentity] = field(default_factory=set)
    identity: int = field(default_factory=itertools.count().__next__)
    member_base: BindingScope | None = field(default=None, repr=False, compare=False)

    def lookup(self, name: str, *, later: bool = False) -> BindingValue:
        """Honor lexical locals before considering outer runtime may-bindings."""
        return self.read(name, later=later).value

    def read(self, name: str, *, later: bool = False) -> LexicalRead:
        """Resolve a binding and its origin through the same lexical traversal."""
        values = self.history if later else self.values
        if name in values:
            value = values[name]
        elif name in self.locals and self.kind != "class":
            value = BindingValue(unknown=True)
        elif self.parent is not None:
            parent = self.parent
            if name in self.globals:
                while parent.parent is not None:
                    parent = parent.parent
            read = parent.read(name, later=later or self.deferred_outer)
            return (
                replace(read, value=read.value.join(BindingValue(unknown=True)))
                if self.wildcard
                else read
            )
        elif name in {
            "getattr",
            "__import__",
            "str",
            "exec",
            "eval",
            "tuple",
            "dict",
            "classmethod",
            "staticmethod",
            "isinstance",
        }:
            value = BindingValue(targets=frozenset({f"builtins.{name}"}))
        else:
            value = BindingValue(unknown=True)
        return LexicalRead(
            self, name, value.join(BindingValue(unknown=True)) if self.wildcard else value, later
        )

    def assign(self, name: str, value: BindingValue) -> None:
        """Route lexical writes without executing deferred bodies in the outer frame."""
        owner = self.outer(name) if name in self.globals | self.nonlocals else self
        frame = self
        while frame is not owner and not frame.deferred_outer:
            frame = frame.parent or owner
        frame.values[name] = value
        frame.history[name] = frame.history[name].join(value) if name in frame.history else value
        if frame is not owner:
            previous = owner.history.get(name, BindingValue(unknown=True))
            owner.history[name] = previous.join(value)

    def outer(self, name: str) -> BindingScope:
        """Resolve global or enclosing function ownership, never a class namespace."""
        parent = self.parent or self
        if name in self.globals:
            while parent.parent is not None:
                parent = parent.parent
        else:
            while parent.parent is not None and (
                parent.kind == "class" or name not in parent.locals
            ):
                parent = parent.parent
        return parent

    def invalidate_outer(self, names: frozenset[str]) -> None:
        """A deferred writer invalidates only affected outer may-bindings."""
        for name in names:
            owner = self.outer(name)
            previous = owner.history.get(name, BindingValue(unknown=True))
            owner.history[name] = previous.join(BindingValue(unknown=True))

    def member_binding(
        self, name: str | AggregateIdentity, *, later: bool = False
    ) -> BindingValue | None:
        """Distinguish absent custody from a present empty or unknown binding."""
        values = self.member_history if later else self.members
        if name in values:
            return values[name]
        if self.parent is not None:
            return self.parent.member_binding(name, later=later or self.deferred_outer)
        return None

    def member(self, name: str | AggregateIdentity, *, later: bool = False) -> BindingValue:
        """Resolve imported-object mutation at this point or later invocation."""
        binding = self.member_binding(name, later=later)
        if binding is not None:
            return binding
        if name == "sys.executable":
            return BindingValue(executable_origins=frozenset({"python"}), deferred=True)
        return (
            BindingValue()
            if isinstance(name, AggregateIdentity)
            else BindingValue(targets=frozenset({name}))
        )

    def resolve(self, value: BindingValue) -> BindingValue:
        """Read mutable aggregate aliases from this program point, not copied contents."""
        if not value.aggregates:
            return value
        resolved: BindingValue | None = None
        for identity in value.aggregates:
            current = self.member(identity)
            if current != BindingValue():
                current = replace(current, aggregates=frozenset({identity}))
            resolved = current if resolved is None else resolved.join(current)
        if resolved is None:
            return value
        if value.view and resolved.entries is not None:
            items = tuple(
                item
                if value.view == "values"
                else BindingValue(strings=frozenset({key}))
                if value.view == "keys"
                else BindingValue(
                    items=(BindingValue(strings=frozenset({key})), item), ordered=True
                )
                for key, item in resolved.entries
            )
            shapes = resolved.closed_mapping_shapes()
            resolved = replace(
                resolved,
                items=items,
                entries=None,
                mapping_shapes=None,
                unknown=resolved.unknown or len({len(shape) for shape in shapes}) > 1,
            )
        return replace(
            resolved,
            targets=resolved.targets | value.targets,
            strings=resolved.strings | value.strings,
            truths=resolved.truths | value.truths,
            executable_origins=resolved.executable_origins | value.executable_origins,
            projections=resolved.projections | value.projections,
            parameters=resolved.parameters | value.parameters,
            methods=resolved.methods | value.methods,
            instance_types=resolved.instance_types | value.instance_types,
            selection=resolved.selection | value.selection,
            local=resolved.local or value.local,
            aggregates=value.aggregates,
            allocation_complete=value.allocation_complete,
            view=value.view,
            unknown=resolved.unknown or value.unknown,
            deferred=resolved.deferred or value.deferred,
            context_limited=resolved.context_limited or value.context_limited,
        )

    def aggregate(self, value: BindingValue, node: ast.expr) -> BindingValue:
        """Keep distinct finite allocations and weakly initialize recurrent sites."""
        identity = AggregateIdentity(
            self.name, node.lineno, node.col_offset, self.allocation_context
        )
        previous = self.member(identity)
        if previous != BindingValue():
            self.summarized.add(identity)
            value = previous.join(value)
        self.assign_member(identity, value)
        return replace(value, aggregates=frozenset({identity}), allocation_complete=True)

    @contextmanager
    def iteration(self, node: ast.For, index: int) -> Iterator[None]:
        """Distinguish allocations only where finite iteration order is proven."""
        previous = self.allocation_context
        self.allocation_context = (*previous, (node.lineno, node.col_offset, index))
        try:
            yield
        finally:
            self.allocation_context = previous

    def assume(self, test: ast.expr, *, truth: bool) -> None:
        """Apply a branch-local guard, never a write to binding history."""
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            self.assume(test.operand, truth=not truth)
        elif isinstance(test, ast.Name):
            self.values[test.id] = self.lookup(test.id).guarded(truth=truth)

    def alternatives(
        self, test: ast.expr, value: BindingValue
    ) -> tuple[tuple[bool, BindingScope], ...]:
        """Fork only possible paths and bind each to its own positive condition."""
        known = value.truthiness()
        branches = []
        for truth in (True, False) if known is None else (known,):
            branch = self.fork()
            branch.assume(test, truth=truth)
            branches.append((truth, branch))
        return tuple(branches)

    def invalidate_aggregates(self, *values: BindingValue) -> None:
        """An opaque call invalidates only mutable objects reachable from its inputs."""
        pending = list(values)
        visited: set[AggregateIdentity] = set()
        while pending:
            value = pending.pop()
            pending.extend(value.items or ())
            pending.extend(item for _, item in value.entries or ())
            pending.extend(item for _, item in value.fields or ())
            pending.extend(method.receiver for method in value.methods)
            for identity in value.aggregates - visited:
                visited.add(identity)
                pending.append(self.member(identity))
                self.assign_member(identity, BindingValue(unknown=True))

    def assign_member(self, name: str | AggregateIdentity, value: BindingValue) -> None:
        """Replace one member without invalidating already captured callable values."""
        self.member_history[name] = self.member(name).join(value)
        self.members[name] = value

    def fork(self) -> BindingScope:
        """Copy mutable program-point state for an alternative control path."""
        return replace(
            self,
            values=dict(self.values),
            history=dict(self.history),
            members=dict(self.members),
            member_history=dict(self.member_history),
            summarized=set(self.summarized),
        )

    def merge(self, *branches: BindingScope) -> None:
        """Merge branch environments while preserving missing-binding uncertainty."""
        base = branches[0].member_base
        self.member_base = base if all(branch.member_base is base for branch in branches) else None
        if len(branches) == 1:
            branch = branches[0]
            self.wildcard = branch.wildcard
            self.summarized = set(branch.summarized)
            for name in ("values", "history", "members", "member_history"):
                setattr(self, name, dict(getattr(branch, name)))
            return
        self.wildcard = any(branch.wildcard for branch in branches)
        self.summarized = set().union(*(branch.summarized for branch in branches))
        for field_name in ("values", "history", "members", "member_history"):
            mappings = [getattr(branch, field_name) for branch in branches]
            if all(mapping == mappings[0] for mapping in mappings[1:]):
                setattr(self, field_name, dict(mappings[0]))
                continue
            missing = BindingValue(unknown=True)
            result: dict[str | AggregateIdentity, BindingValue] = {}
            for name in set().union(*(mapping.keys() for mapping in mappings)):
                values = (
                    mapping.get(name, missing)
                    if field_name in ("values", "history")
                    else branch.member(name, later=field_name == "member_history")
                    for mapping, branch in zip(mappings, branches, strict=True)
                )
                value = next(values)
                for selected in values:
                    value = value.join(selected)
                result[name] = value
            setattr(self, field_name, result)

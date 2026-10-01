"""Keep native lexical binding and mutable-alias custody below flow interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import MappingValue
from ethos.repository.policy.references.python.values import Sequence
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value
from ethos.repository.policy.references.python.values import mutable_reachability
from ethos.repository.policy.references.python.values import origins

if TYPE_CHECKING:
    import symtable


@dataclass(slots=True)
class Scope:
    """Own lexical lookup, reaching bindings and mutation invalidation per flow."""

    table: symtable.SymbolTable
    parent: Scope | None = None
    values: dict[str, Value] = field(default_factory=dict)
    history: dict[str, Value] = field(default_factory=dict)
    iteration_names: frozenset[str] | None = None
    invalidated: frozenset[MappingValue | Sequence] = frozenset()

    def lookup(self, name: str) -> Value:
        symbol = self.table.lookup(name) if name in self.table.get_identifiers() else None
        if name in self.values:
            return self.values[name]
        if self.iteration_names is not None and self.parent is not None:
            return UNKNOWN if name in self.iteration_names else self.parent.lookup(name)
        if self.parent is None:
            return (
                frozenset({Imported(f"builtins.{name}")})
                if name in {"dict", "getattr", "str"}
                else UNKNOWN
            )
        if symbol is not None and symbol.is_local():
            return UNKNOWN
        parent = self.parent
        if symbol is not None and symbol.is_global():
            while parent.parent is not None:
                parent = parent.parent
            possible = parent.history.get(name, parent.lookup(name))
            if possible != parent.lookup(name):
                return frozenset({Unknown(origins(possible))})
        return parent.lookup(name)

    def store(self, name: str, value: Value) -> None:
        # Deferred bodies must not mutate the shared enclosing analysis state.
        if self.iteration_names is not None and name not in self.iteration_names and self.parent:
            self.parent.store(name, value)
            return
        self.values[name] = value
        self.history[name] = self.history.get(name, frozenset()) | value

    def invalidate(self, exposed: Value) -> None:
        """A possible mutation widens every reachable alias, not earlier observations."""
        affected = mutable_reachability(exposed)
        scope: Scope | None = self
        while affected and scope is not None:
            scope.invalidated |= affected
            for name, value in tuple(scope.values.items()):
                if affected & mutable_reachability(value):
                    scope.store(name, frozenset({Unknown(origins(value))}))
            scope = scope.parent

    def member(self, identity: str, fallback: Value) -> Value:
        if identity in self.values:
            return self.values[identity]
        return self.parent.member(identity, fallback) if self.parent is not None else fallback

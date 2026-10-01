"""Finite abstract values keep identities, literals and uncertainty distinct."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class Imported:
    """An identity established by an import, not by a variable's spelling."""

    name: str


@dataclass(frozen=True, slots=True)
class Literal:
    """A supported scalar value at the observed program point."""

    value: str | bool | int | None


@dataclass(frozen=True, slots=True)
class Sequence:
    """An ordered argument vector, possibly containing unresolved elements."""

    items: tuple[Value, ...]
    site: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class MappingValue:
    """A native dictionary keeps known entries apart from its unknown remainder."""

    site: tuple[int, int]
    items: tuple[tuple[str, Value], ...]
    remainder: Value = frozenset()
    environment_entries: frozenset[str | None] = frozenset()

    @classmethod
    def construct(
        cls, site: tuple[int, int], entries: tuple[tuple[Value | None, Value], ...]
    ) -> Value:
        """Retain dictionary identity and ordered overrides even when entries are open."""
        bindings = [cls(site, ())]
        for key, value in entries:
            additions = (
                [
                    atom
                    if isinstance(atom, cls)
                    else cls(
                        site,
                        (),
                        frozenset({atom}),
                        frozenset({None}) if atom == Imported("os.environ") else frozenset(),
                    )
                    for atom in value
                ]
                if key is None
                else [
                    cls(site, ((atom.value, value),))
                    if isinstance(atom, Literal) and isinstance(atom.value, str)
                    else cls(site, (), UNKNOWN)
                    for atom in key
                ]
            )
            bindings = [
                cls(
                    site,
                    tuple(
                        {
                            **{
                                name: item | frozenset({Unknown(origins(added.remainder))})
                                if added.remainder
                                else item
                                for name, item in bound.items
                            },
                            **dict(added.items),
                        }.items()
                    ),
                    bound.remainder | added.remainder,
                    (
                        bound.environment_entries
                        | added.environment_entries
                        | frozenset(
                            name for name, _ in bound.items if None in added.environment_entries
                        )
                    )
                    - frozenset(
                        name for name, _ in added.items if name not in added.environment_entries
                    ),
                )
                for bound in bindings
                for added in additions
            ]
            if len(bindings) > 64:
                return frozenset(
                    {cls(site, (), frozenset({Unknown(origins(frozenset(bindings)))}))}
                )
        return frozenset(bindings)

    def read(self, key: Value, default: Value | None = None) -> Value:
        """Read exact entries before consulting an open remainder or a missing-key default."""
        fallback = UNKNOWN if default is None else default
        return join(
            dict(self.items).get(
                atom.value,
                fallback | frozenset({Unknown(origins(self.remainder))})
                if self.remainder
                else fallback,
            )
            if isinstance(atom, Literal) and isinstance(atom.value, str)
            else frozenset({Unknown(origins(frozenset({self})))})
            for atom in key
        )

    def environment_read(self, key: Value) -> bool:
        """A snapshot entry retains input provenance without retaining live-map identity."""
        return any(
            (atom.value if atom.value in dict(self.items) else None) in self.environment_entries
            if isinstance(atom, Literal) and isinstance(atom.value, str)
            else bool(self.environment_entries)
            for atom in key
        )


@dataclass(frozen=True, slots=True)
class MappingMethod:
    """A method belongs to a known native mapping, not an environment lookup."""

    owner: MappingValue
    name: str


@dataclass(frozen=True, slots=True)
class Unknown:
    """An unresolved alternative retaining its known imported dependencies."""

    origins: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Expansion:
    """A starred iterable has variable arity, unlike one unresolved argument."""

    value: Value


@dataclass(frozen=True, slots=True)
class ExecutableLookup:
    """A presence lookup preserves program identity without claiming path bytes."""

    identity: str
    is_path: bool = False


@dataclass(frozen=True, slots=True)
class PathMethod:
    """A native pathlib method bound to the observed executable path."""

    identity: str
    name: str


@dataclass(frozen=True, slots=True)
class LocalFunction:
    """One source-defined function identity; spelling alone cannot identify it."""

    name: str
    line: int


type Value = frozenset[
    Imported
    | Literal
    | Sequence
    | MappingValue
    | MappingMethod
    | Unknown
    | Expansion
    | ExecutableLookup
    | PathMethod
    | LocalFunction
]

UNKNOWN: Value = frozenset({Unknown()})


def origins(value: Value) -> frozenset[str]:
    """Return imported dependencies without inventing a resolved target."""
    return frozenset(
        name
        for atom in reachable_values(value)
        for name in (
            (atom.name,)
            if isinstance(atom, Imported)
            else atom.origins
            if isinstance(atom, Unknown)
            else ()
        )
    )


def join(values: Iterable[Value]) -> Value:
    """Join alternatives, widening excessive combinations rather than guessing."""
    result = frozenset(atom for value in values for atom in value)
    # This analysis bound limits work, never turns an unresolved case into PASS.
    return result if len(result) <= 64 else frozenset({Unknown(origins(result))})


def iteration_values(value: Value) -> Value:
    """Keep finite iteration facts and distinguish empty from unknown iterables."""
    return join(join(atom.items) if isinstance(atom, Sequence) else UNKNOWN for atom in value)


def reachable_values(value: Value) -> Value:
    """Traverse the finite value graph shared by origin and alias observations."""
    pending, found = list(value), set()
    while pending:
        atom = pending.pop()
        if atom in found:
            continue
        found.add(atom)
        if isinstance(atom, MappingValue):
            pending.extend(item for _, values in atom.items for item in values)
            pending.extend(atom.remainder)
        elif isinstance(atom, Sequence):
            pending.extend(item for values in atom.items for item in values)
        elif isinstance(atom, Expansion):
            pending.extend(atom.value)
        elif isinstance(atom, MappingMethod):
            pending.append(atom.owner)
    return frozenset(found)


def mutable_reachability(value: Value) -> frozenset[MappingValue | Sequence]:
    """Find native mutable containers without treating immutable tuples as writers."""
    return frozenset(
        atom
        for atom in reachable_values(value)
        if isinstance(atom, MappingValue) or (isinstance(atom, Sequence) and atom.site is not None)
    )


def widen_mutated(
    value: Value, invalidated: frozenset[MappingValue | Sequence], *, preserve_shape: bool = False
) -> Value:
    """Earlier bound values are snapshots; newly used aliases cannot reuse stale shape."""
    return join(
        frozenset(
            {
                MappingValue(
                    atom.site,
                    tuple((key, widen_mutated(item, invalidated)) for key, item in atom.items),
                    atom.remainder,
                    atom.environment_entries,
                )
            }
        )
        if preserve_shape and isinstance(atom, MappingValue)
        else frozenset({Unknown(origins(frozenset({atom})))})
        if mutable_reachability(frozenset({atom})) & invalidated
        else frozenset({atom})
        for atom in value
    )


def attribute(value: Value, name: str) -> Value:
    """Resolve an imported attribute or preserve the unresolved alternative."""
    return join(
        frozenset({Imported(f"{atom.name}.{name}")})
        if isinstance(atom, Imported)
        else frozenset({MappingMethod(atom, name)})
        if isinstance(atom, MappingValue)
        else frozenset({PathMethod(atom.identity, name)})
        if isinstance(atom, ExecutableLookup)
        and atom.is_path
        and name in {"resolve", "absolute", "as_posix", "__fspath__"}
        else frozenset({atom})
        if isinstance(atom, Unknown)
        else UNKNOWN
        for atom in value
    )


@dataclass(frozen=True, slots=True)
class BoundCall:
    """One call's reaching identities and values before later assignments."""

    line: int
    targets: Value
    args: tuple[Value, ...]
    keywords: tuple[tuple[str | None, Value], ...]

    def at_invocation(self, invalidated: frozenset[MappingValue | Sequence]) -> BoundCall:
        """Unpacked keyword shape is copied; mutable values survive later argument effects."""
        return BoundCall(
            self.line,
            self.targets,
            tuple(widen_mutated(value, invalidated) for value in self.args),
            tuple(
                (key, widen_mutated(value, invalidated, preserve_shape=key is None))
                for key, value in self.keywords
            ),
        )

    def exposed_values(self) -> Value:
        """Argument unpacking copies the outer container, not its reachable values."""
        values = join(
            iteration_values(atom.value) if isinstance(atom, Expansion) else frozenset({atom})
            for value in self.args
            for atom in value
        ) | join(
            join(value for _, value in atom.items)
            if key is None and isinstance(atom, MappingValue)
            else frozenset({atom})
            for key, value in self.keywords
            for atom in value
        )
        return values | frozenset(
            target.owner
            for target in self.targets
            if isinstance(target, MappingMethod) and target.name != "get"
        )

    def keyword_bindings(self) -> tuple[dict[str, Value] | None, ...]:
        """Expand finite alternatives; unknown shape and duplicate keys stay unknown."""
        bindings: list[dict[str, Value] | None] = [{}]
        for key, value in self.keywords:
            additions = (
                [{key: value}]
                if key is not None
                else [
                    dict(atom.items)
                    if isinstance(atom, MappingValue) and not atom.remainder
                    else None
                    for atom in value
                ]
            )
            bindings = [
                {**bound, **added}
                if bound is not None and added is not None and bound.keys().isdisjoint(added)
                else None
                for bound in bindings
                for added in additions
            ]
            if len(bindings) > 64:
                return (None,)
        return tuple(bindings)

    def argument(self, index: int, name: str, default: Value = UNKNOWN) -> Value:
        """Keep only uncertainty that can change this argument or invalidate its call."""
        expanded = any(
            isinstance(atom, Expansion) for value in self.args[: index + 1] for atom in value
        )
        values = []
        for keywords in self.keyword_bindings():
            positional = index < len(self.args)
            value = self.args[index] if positional else (keywords or {}).get(name, default)
            invalid = keywords is None or (positional and name in keywords)
            values.append(value | UNKNOWN if expanded or invalid else value)
        return join(values)

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
        for atom in value
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


def attribute(value: Value, name: str) -> Value:
    """Resolve an imported attribute or preserve the unresolved alternative."""
    return join(
        frozenset({Imported(f"{atom.name}.{name}")})
        if isinstance(atom, Imported)
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

    def argument(self, index: int, name: str, default: Value = UNKNOWN) -> Value:
        """Read a positional or keyword argument without ignoring expansion."""
        expanded = any(key is None for key, _ in self.keywords)
        expanded |= any(
            isinstance(atom, Expansion) for value in self.args[: index + 1] for atom in value
        )
        if index < len(self.args):
            value = self.args[index]
        else:
            value = next((value for key, value in self.keywords if key == name), default)
        return value | UNKNOWN if expanded else value

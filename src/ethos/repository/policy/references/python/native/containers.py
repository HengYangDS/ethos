"""Native mapping copy and view contracts shared by direct calls and deferred substitution."""

from __future__ import annotations

import ast
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.native.scalars import dependent

if TYPE_CHECKING:
    from collections.abc import Iterable

ENVIRONMENT = "os.environ"
MAPPING_COPY = "builtins.dict"
MAPPING_VIEWS = {f"{MAPPING_COPY}.{name}": name for name in ("keys", "values", "items")}
_FLAGS = ("unknown", "deferred", "local", "context_limited", "spread")


def expanded(values: Iterable[BindingValue]) -> tuple[BindingValue, ...]:
    """Flatten proven starred sequences; retain opaque expansions as positional residuals."""
    return tuple(
        item
        for value in values
        for item in (value.items if value.spread and value.items is not None else (value,))
    )


def mapping_view(value: BindingValue, target: str) -> BindingValue | None:
    """Return a closed native mapping view; other receivers are not this contract."""
    view = MAPPING_VIEWS.get(target)
    if view is None or value.entries is None or value.targets:
        return None
    return value.viewed(view)


def mapping_copy(value: BindingValue) -> BindingValue | None:
    """Copy environment provenance and closed overlays; defer symbolic slots; keep others open."""
    residual = replace(
        value,
        targets=value.targets - {ENVIRONMENT},
        truths=frozenset(),
        parameters=frozenset(),
        projections=frozenset(),
        entries=None,
        aggregates=frozenset(),
        view="",
        ordered=False,
        native_kind="",
        **dict.fromkeys(_FLAGS, False),
    )
    if residual != BindingValue():
        return None
    live = ENVIRONMENT in value.targets
    deferred = dependent(value, MemberDemand("native_return", key=MAPPING_COPY))
    return BindingValue(
        parameters=deferred.parameters,
        projections=deferred.projections,
        entries=() if live else value.entries,
        ordered=live or value.ordered,
        native_kind="environment" if live or value.native_kind == "environment" else "",
        unknown=value.unknown or value.local or (live and bool(value.entries)),
        deferred=value.deferred,
        context_limited=value.context_limited,
    )


def mapping_return(value: BindingValue, target: str) -> BindingValue | None:
    """Apply the native copy or view relation demanded by a call or a deferred slot."""
    return mapping_copy(value) if target == MAPPING_COPY else mapping_view(value, target)


def stored(
    current: BindingValue, node: ast.expr, key: BindingValue, value: BindingValue, *, strong: bool
) -> BindingValue:
    """Apply one native subscript store to an exact mapping slot or ordered sequence index."""
    name = next(iter(key.strings)) if len(key.strings) == 1 else None
    if current.entries is not None and name is not None:
        entries = dict(current.entries)
        old = entries.get(name, BindingValue(unknown=True))
        entries[name] = value if strong else old.join(value)
        return replace(current, entries=tuple(entries.items()))
    if isinstance(node, ast.Slice):
        return slice_store(current, node, value, strong=strong)
    if current.items is None or key.strings:
        return BindingValue(unknown=True)
    try:
        index = ast.literal_eval(node)
    except ValueError:
        index = None
    items = list(current.items)
    if type(index) is not int:
        return replace(current, items=tuple(item.join(value) for item in items))
    if -len(items) <= index < len(items):
        items[index] = value if strong else items[index].join(value)
    return replace(current, items=tuple(items))


def native_slice(node: ast.Slice) -> slice | None:
    """Use native literal evaluation for exact slice bounds, never an opaque expression."""
    bounds = []
    for boundary in (node.lower, node.upper, node.step):
        try:
            value = ast.literal_eval(boundary) if boundary is not None else None
        except (ValueError, TypeError):
            return None
        if value is not None and type(value) is not int:
            return None
        bounds.append(value)
    return slice(*bounds) if bounds[2] != 0 else None


def slice_store(
    current: BindingValue, node: ast.Slice, value: BindingValue, *, strong: bool
) -> BindingValue:
    """Apply one exact successful native slice; unsupported stores remain unknown."""
    selector = native_slice(node)
    if (
        selector is None
        or current.items is None
        or value.items is None
        or value.unknown
        or value.deferred
    ):
        return BindingValue(unknown=True)
    items = list(current.items)
    try:
        items[selector] = value.items
    except ValueError:
        return BindingValue(unknown=True)
    updated = replace(current, items=tuple(items))
    return updated if strong else current.join(updated)

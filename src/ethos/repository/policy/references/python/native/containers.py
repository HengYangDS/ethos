"""Native mapping copy and view contracts shared by direct calls and deferred substitution."""

from __future__ import annotations

from dataclasses import replace

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.native.scalars import dependent

ENVIRONMENT = "os.environ"
MAPPING_COPY = "builtins.dict"
MAPPING_VIEWS = {f"{MAPPING_COPY}.{name}": name for name in ("keys", "values", "items")}
_FLAGS = ("unknown", "deferred", "local", "context_limited", "spread")


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

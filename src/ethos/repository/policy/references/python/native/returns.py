"""Closed native return relationships, independent of effect consumption and authority."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.functions.effects import project
from ethos.repository.policy.references.python.native.scalars import native_scalar

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import BindingScope
    from ethos.repository.policy.references.python.effects import PythonConsumption


def native_return(
    observer: PythonConsumption,
    target: str,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
    scope: BindingScope,
) -> BindingValue | None:
    """Recognize native input-to-return contracts without treating construction as escape."""
    if observer.sources is not None and target in {
        "pathlib.Path",
        "builtins.str",
        "builtins.tuple",
        "builtins.list",
        "builtins.len",
        "builtins.dict",
        "shutil.which",
    }:
        args = tuple(observer.sources.invocations.resolve(value, scope, observer) for value in args)
    if target == "functools.partial" and observer.sources is not None:
        return observer.sources.partial(args, keywords)
    if target == "builtins.getattr" and args:
        return observer.attribute(args, scope)
    if target == "builtins.hasattr" and len(args) == 2 and not keywords:
        owner, name = args
        if owner.targets and not (
            owner.unknown or owner.local or owner.parameters or owner.projections
        ):
            observer.attribute((owner, name), scope)
            return BindingValue(deferred=True)
    if target == "builtins.isinstance" and len(args) == 2 and not keywords:
        types = args[1]
        if (
            types.targets
            and types.targets <= {"builtins.str", "builtins.tuple", "builtins.dict"}
            and not (types.unknown or types.local or types.deferred)
        ):
            return BindingValue(deferred=True)
    if target in {"builtins.dict", "builtins.list", "builtins.tuple", "builtins.dict.fromkeys"}:
        return native_container(observer, target, args, keywords, scope)
    return native_scalar(target, args, keywords)


def native_container(
    observer: PythonConsumption,
    target: str,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
    scope: BindingScope,
) -> BindingValue | None:
    """Fresh mapping copies retain source provenance independently of mutable aliases."""
    if target == "builtins.list" and len(args) <= 1 and not keywords:
        value = scope.resolve(args[0]) if args else BindingValue(items=(), ordered=True)
        if not (value.targets or value.local) and (
            value.items is not None
            or value.entries is not None
            or value.element is not None
            or value.parameters
            or value.projections
        ):
            copied = project(value, MemberDemand("structure"), scope, observer.sources, observer)
            return replace(copied, native_kind="list", ordered=True)
    if target == "builtins.dict" and len(args) <= 1 and not keywords:
        value = scope.resolve(args[0]) if args else BindingValue(entries=(), ordered=True)
        if value.targets == frozenset({"os.environ"}) and not value.unknown:
            return BindingValue(entries=(), ordered=True, native_kind="environment")
        if value.entries is not None and not value.targets:
            return replace(value, aggregates=frozenset(), view="")
    if target in {"builtins.tuple", "builtins.dict.fromkeys"} and args:
        if target == "builtins.tuple":
            return project(args[0], MemberDemand("structure"), scope, observer.sources, observer)
        value = project(args[0], MemberDemand("iterate"), scope, observer.sources, observer)
        default = args[1] if len(args) > 1 else BindingValue(local=True)
        return BindingValue(
            entries=tuple((name, default) for name in sorted(value.strings)),
            ordered=False,
            unknown=value.unknown or value.deferred or not value.strings,
            context_limited=value.context_limited or default.context_limited,
        )
    return None

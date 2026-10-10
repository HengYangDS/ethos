"""Closed native return relationships, independent of effect consumption and authority."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.functions.effects import project
from ethos.repository.policy.references.python.native.containers import MAPPING_VIEWS
from ethos.repository.policy.references.python.native.containers import mapping_copy
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
    return (
        observer.sources.completed_process(args, keywords, scope)
        if target == "subprocess.CompletedProcess" and observer.sources is not None
        else native_scalar(target, args, keywords)
    )


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
        return mapping_copy(value)
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


def symbolic_view(
    callee: BindingValue, args: tuple[BindingValue, ...], keywords: dict[str | None, BindingValue]
) -> BindingValue | None:
    """Defer a no-argument native mapping view on symbolic receivers to each actual pack."""
    if args or keywords or callee != BindingValue(parameters=callee.parameters):
        return None
    deferred = set()
    for projection in callee.parameters:
        member = projection.members[-1] if projection.members else None
        names = member.selector.strings if member and member.selector else frozenset()
        target = f"builtins.dict.{next(iter(names))}" if len(names) == 1 else ""
        if member is None or member.kind != "attribute" or target not in MAPPING_VIEWS:
            return None
        view = MemberDemand("native_return", key=target)
        deferred.add(replace(projection, members=(*projection.members[:-1], view)))
    return BindingValue(parameters=frozenset(deferred))


def store_field(name: str, owner: BindingValue, value: BindingValue, scope: BindingScope) -> None:
    """Only native mutable records store fields; one exact owner replaces, aliases join."""
    if owner.unknown:
        scope.invalidate_aggregates(*(method.receiver for method in owner.methods))
    strong = len(owner.aggregates) == 1 and not (owner.unknown or owner.deferred)
    for identity in owner.aggregates:
        current = scope.member(identity)
        if current.fields is not None and current.native_kind != "completed_process":
            # A store on any other record never establishes a value; it only removes one.
            fields = dict(current.fields) | {name: BindingValue(unknown=True)}
            scope.assign_member(identity, replace(current, fields=tuple(fields.items())))
        if current.native_kind != "completed_process" or current.fields is None:
            continue
        fields = dict(current.fields)
        fields[name] = (
            value
            if strong and identity not in scope.summarized
            else fields.get(name, BindingValue(unknown=True)).join(value)
        )
        scope.assign_member(identity, replace(current, fields=tuple(fields.items())))

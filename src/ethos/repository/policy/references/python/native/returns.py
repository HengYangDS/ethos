"""Closed native return relationships, independent of effect consumption and authority."""

from __future__ import annotations

import inspect
import pathlib
import subprocess
import tempfile
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Literal

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.functions.effects import project
from ethos.repository.policy.references.python.native.containers import MAPPING_VIEWS
from ethos.repository.policy.references.python.native.containers import mapping_copy
from ethos.repository.policy.references.python.native.scalars import native_scalar

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import BindingScope
    from ethos.repository.policy.references.python.effects import PythonConsumption


@dataclass(frozen=True, slots=True)
class ReceiverCall:
    """A native result and its effect disposition are separate observations."""

    returned: BindingValue | None = None
    disposition: Literal["read", "mutation", "unresolved"] = "unresolved"
    footprint: BindingValue = field(default_factory=BindingValue)
    argument_demand: int | None = None
    post_state: BindingValue | None = None


_TEMPORARY_DIRECTORY_SIGNATURE = inspect.signature(tempfile.TemporaryDirectory)
_TEMPORARY_DIRECTORY = BindingValue(
    native_kind="temporary_directory", fields=(("name", BindingValue(native_kind="text")),)
)
_TEMPORARY_DIRECTORY_DISPATCH = (
    "tempfile.TemporaryDirectory.__new__",
    "tempfile.TemporaryDirectory.__setattr__",
    "tempfile.TemporaryDirectory.__init__",
    "tempfile.TemporaryDirectory.__enter__",
    "tempfile.TemporaryDirectory.__exit__",
    "tempfile.TemporaryDirectory.cleanup",
    "tempfile.TemporaryDirectory._cleanup",
    "tempfile.TemporaryDirectory._rmtree",
    "tempfile.mkdtemp",
)
_NATIVE_RECORD_SIGNATURES = {
    f"subprocess.{constructor.__name__}": signature.replace(
        parameters=[
            parameter
            if parameter.default is parameter.empty
            else parameter.replace(default=BindingValue(truths=frozenset({False})))
            for parameter in signature.parameters.values()
        ]
    )
    for constructor in (
        subprocess.CompletedProcess,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    )
    for signature in (inspect.signature(constructor),)
}
_EXCEPTION_OUTPUT_ALIASES = frozenset(
    f"subprocess.{constructor.__name__}"
    for constructor in (subprocess.TimeoutExpired, subprocess.CalledProcessError)
)
_PATH_RESOLVE_DISPATCH = tuple(
    dict.fromkeys(
        [
            f"pathlib.{owner.__name__}.{name}"
            for concrete in (pathlib.Path, pathlib.PosixPath, pathlib.WindowsPath)
            for owner in concrete.__mro__[:-1]
            for name in ("resolve", "with_segments", "__new__", "__init__", "__setattr__")
            if hasattr(owner, name)
        ]
        + ["os.path.realpath"]
    )
)


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
    if target in {
        "builtins.dict",
        "builtins.list",
        "builtins.tuple",
        "builtins.dict.fromkeys",
        "tempfile.TemporaryDirectory",
        *_NATIVE_RECORD_SIGNATURES,
    }:
        return native_container(observer, target, args, keywords, scope)
    return native_scalar(target, args, keywords)


def temporary_directory(
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
    scope: BindingScope,
    observer: PythonConsumption,
) -> BindingValue | None:
    """Native allocation owns only its directory; opaque inputs never establish its protocol."""
    if None in keywords or any(value.spread for value in args):
        return None
    named = {name: value for name, value in keywords.items() if name is not None}
    try:
        bound = _TEMPORARY_DIRECTORY_SIGNATURE.bind(*args, **named)
    except TypeError:
        return None
    for name, value in bound.arguments.items():
        closed = (
            value.truths and value == BindingValue(truths=value.truths)
            if name in {"ignore_cleanup_errors", "delete"}
            else value.strings and value == BindingValue(strings=value.strings)
        )
        if not closed:
            return None
    return (
        _TEMPORARY_DIRECTORY
        if native_context(_TEMPORARY_DIRECTORY, scope, observer) is not None
        else None
    )


def native_dependencies(
    observer: PythonConsumption, target: str, scope: BindingScope
) -> tuple[BindingValue, ...]:
    """Read one supported protocol's dispatch inputs and retain every changed effect owner."""
    changed = []
    dependencies = (
        _TEMPORARY_DIRECTORY_DISPATCH
        if target == "tempfile.TemporaryDirectory"
        else _PATH_RESOLVE_DISPATCH
        if target == "pathlib.Path.resolve"
        else (f"{target}.__init__", f"{target}.__new__", f"{target}.__setattr__")
        if target in _NATIVE_RECORD_SIGNATURES
        else ()
    )
    for dependency in dependencies:
        owner, _, name = dependency.rpartition(".")
        value = observer.attribute(
            (BindingValue(targets=frozenset({owner})), BindingValue(strings=frozenset({name}))),
            scope,
        )
        if value != BindingValue(targets=frozenset({dependency})):
            changed.append(value)
    return tuple(changed)


def native_context(
    value: BindingValue, scope: BindingScope, observer: PythonConsumption
) -> BindingValue | None:
    """A current, unmodified native context returns text and cannot havoc caller-local objects."""
    value = replace(scope.resolve(value), aggregates=frozenset())
    if value != _TEMPORARY_DIRECTORY:
        return None
    return (
        None
        if native_dependencies(observer, "tempfile.TemporaryDirectory", scope)
        else BindingValue(native_kind="text")
    )


def native_record(
    observer: PythonConsumption,
    target: str,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
    scope: BindingScope,
) -> BindingValue | None:
    """Exact field-only constructors retain references without invoking or mutating them."""
    if (
        None in keywords
        or any(value.spread for value in args)
        or native_dependencies(observer, target, scope)
    ):
        return None
    try:
        bound = _NATIVE_RECORD_SIGNATURES[target].bind(
            *args, **{name: value for name, value in keywords.items() if name is not None}
        )
    except TypeError:
        return None
    bound.apply_defaults()
    return BindingValue(
        fields=(("__class__", BindingValue(targets=frozenset({target}))), *bound.arguments.items()),
        native_kind="native_record",
    )


def native_field_name(
    observer: PythonConsumption,
    owner: BindingValue,
    name: str,
    scope: BindingScope,
    *,
    write: bool = False,
) -> str | None:
    """Descriptor aliases share one field only while their actual native dispatch remains closed."""
    target = dict(owner.fields or ()).get("__class__", BindingValue()).targets
    if name != "stdout" or len(target) != 1 or not target <= _EXCEPTION_OUTPUT_ALIASES:
        return name
    descriptor = f"{next(iter(target))}.stdout"
    for dependency in (descriptor, f"{descriptor}.{'fset' if write else 'fget'}"):
        parent, _, member = dependency.rpartition(".")
        current = observer.attribute(
            (BindingValue(targets=frozenset({parent})), BindingValue(strings=frozenset({member}))),
            scope,
        )
        if current != BindingValue(targets=frozenset({dependency})):
            observer.invalidate(scope, owner, current, conditional=True)
            return None
    return "output"


def native_field(
    observer: PythonConsumption, owner: BindingValue, name: str, scope: BindingScope
) -> BindingValue | None:
    """Read the same native record slot that a qualified descriptor store updates."""
    if owner.native_kind != "native_record" or owner.fields is None:
        return None
    canonical = native_field_name(observer, owner, name, scope)
    value = dict(owner.fields).get(canonical or "", BindingValue(unknown=True))
    return replace(
        value, unknown=value.unknown or owner.unknown, deferred=value.deferred or owner.deferred
    )


def native_container(
    observer: PythonConsumption,
    target: str,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
    scope: BindingScope,
) -> BindingValue | None:
    """Native containers retain owned state without aliasing arbitrary caller-local objects."""
    if target == "tempfile.TemporaryDirectory" or target in _NATIVE_RECORD_SIGNATURES:
        return (
            temporary_directory(args, keywords, scope, observer)
            if target == "tempfile.TemporaryDirectory"
            else native_record(observer, target, args, keywords, scope)
        )
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


def symbolic_return(
    callee: BindingValue, args: tuple[BindingValue, ...], keywords: dict[str | None, BindingValue]
) -> BindingValue | None:
    """Retain a closed no-argument receiver operation until its actual owner is substituted."""
    if (
        not callee.parameters
        or args
        or keywords
        or callee != BindingValue(parameters=callee.parameters)
    ):
        return None
    deferred = set()
    for projection in callee.parameters:
        member = projection.members[-1] if projection.members else None
        names = member.selector.strings if member and member.selector else frozenset()
        if (
            member is None
            or member.kind != "attribute"
            or len(names) != 1
            or member.selector != BindingValue(strings=names)
        ):
            return None
        name = next(iter(names))
        target = "pathlib.Path.resolve" if name == "resolve" else f"builtins.dict.{name}"
        if target != "pathlib.Path.resolve" and target not in MAPPING_VIEWS:
            return None
        view = MemberDemand("native_return", key=target)
        deferred.add(replace(projection, members=(*projection.members[:-1], view)))
    return BindingValue(parameters=frozenset(deferred))


def store_field(
    name: str,
    owner: BindingValue,
    value: BindingValue,
    scope: BindingScope,
    observer: PythonConsumption,
) -> None:
    """Only native mutable records store fields; one exact owner replaces, aliases join."""
    if owner.unknown:
        scope.invalidate_aggregates(*(method.receiver for method in owner.methods))
    strong = len(owner.aggregates) == 1 and not (owner.unknown or owner.deferred)
    for identity in owner.aggregates:
        current = scope.member(identity)
        if current.fields is not None and current.native_kind != "native_record":
            # A store on any other record never establishes a value; it only removes one.
            fields = dict(current.fields) | {name: BindingValue(unknown=True)}
            scope.assign_member(identity, replace(current, fields=tuple(fields.items())))
        if current.native_kind != "native_record" or current.fields is None:
            continue
        canonical = native_field_name(observer, current, name, scope, write=True)
        if canonical is None:
            scope.invalidate_aggregates(owner)
            continue
        fields = dict(current.fields)
        fields[canonical] = (
            value
            if strong and identity not in scope.summarized
            else fields.get(canonical, BindingValue(unknown=True)).join(value)
        )
        scope.assign_member(identity, replace(current, fields=tuple(fields.items())))

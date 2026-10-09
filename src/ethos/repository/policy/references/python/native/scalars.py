"""Native scalar relations retain substitutions rather than generic runtime flags."""

from __future__ import annotations

from dataclasses import replace

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand


def dependent(value: BindingValue, demand: MemberDemand) -> BindingValue:
    """Retain the transformation to apply when an owner supplies its actual argument."""
    return BindingValue(
        parameters=frozenset(
            replace(item, members=(*item.members, demand)) for item in value.parameters
        ),
        projections=frozenset(
            replace(item, members=(*item.members, demand)) for item in value.projections
        ),
        unknown=value.unknown,
        deferred=value.deferred,
        context_limited=value.context_limited,
    )


def concatenate(left: BindingValue, right: BindingValue) -> BindingValue:
    """Compose literal or symbolic operands without dropping opaque alternatives."""
    if left.items is not None and right.items is not None:
        return BindingValue(items=left.items + right.items)
    bounded = len(left.strings) * len(right.strings) <= 64
    value = BindingValue(
        strings=frozenset(a + b for a in left.strings for b in right.strings)
        if bounded
        else frozenset(),
        deferred=left.deferred or right.deferred,
        unknown=left.unknown or right.unknown or not bounded,
        context_limited=left.context_limited or right.context_limited,
    )
    for subject, other, order in ((left, right, "left"), (right, left, "right")):
        if subject.parameters or subject.projections:
            value = value.join(
                dependent(subject, MemberDemand("concatenate", key=order, selector=other))
            )
    return value


def native_scalar(
    target: str, args: tuple[BindingValue, ...], keywords: dict[str | None, BindingValue]
) -> BindingValue | None:
    """Native transformations discharge actual slots, never opaque inputs."""
    value = args[0] if args else keywords.get("cmd", BindingValue(unknown=True))
    if target == "builtins.len" and len(args) == 1 and not keywords:
        symbolic = bool(value.parameters or value.projections)
        native = not (value.unknown or value.local or value.selection) and (
            value.targets == frozenset({"os.environ"})
            or (
                not value.targets
                and (
                    value.items is not None
                    or value.entries is not None
                    or value.strings
                    or value.native_kind in {"list", "environment"}
                )
            )
        )
        return (
            dependent(value, MemberDemand("native_return", key=target))
            if symbolic
            else BindingValue(deferred=True, context_limited=value.context_limited)
            if native
            else None
        )
    if target == "shutil.which":
        current = dependent(value, MemberDemand("native_return", key=target))
        return replace(
            current,
            executable_origins=value.strings,
            unknown=value.unknown
            or not (value.strings or value.deferred or value.parameters or value.projections),
        )
    if (
        target in {"pathlib.Path", "builtins.str", "builtins.int"}
        and len(args) == 1
        and not keywords
    ):
        current = dependent(value, MemberDemand("native_return", key=target))
        symbolic = bool(value.parameters or value.projections)
        return replace(
            current,
            strings=value.strings if target != "builtins.int" else frozenset(),
            executable_origins=value.executable_origins,
            path=target == "pathlib.Path",
            deferred=value.deferred or (target == "builtins.int" and not symbolic),
            unknown=value.unknown
            or not (
                value.strings
                or value.executable_origins
                or value.deferred
                or symbolic
                or (target == "builtins.int" and value.truths)
            ),
        )
    if target == "builtins.range" and args and not keywords:
        current = dependent(value, MemberDemand("native_return", key="builtins.int"))
        current = replace(current, deferred=current.deferred or not current.parameters)
        return BindingValue(element=current, unknown=any(item.unknown for item in args))
    return None

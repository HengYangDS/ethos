"""Native scalar relations retain substitutions rather than generic runtime flags."""

from __future__ import annotations

from dataclasses import replace
from pathlib import PurePath

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
            strings=frozenset(str(PurePath(text)) for text in value.strings)
            if target == "pathlib.Path"
            else value.strings
            if target != "builtins.int"
            else frozenset(),
            executable_origins=value.executable_origins,
            native_kind="text" if target == "builtins.str" and native_content(value) else "",
            path=target == "pathlib.Path",
            deferred=value.deferred or (target == "builtins.int" and not symbolic),
            unknown=value.unknown
            or not (
                value.strings
                or value.executable_origins
                or value.deferred
                or symbolic
                or (target != "builtins.int" and native_content(value))
                or (target == "builtins.int" and value.truths)
            ),
        )
    if target == "hashlib.sha256":
        # A successful native digest needs one bytes-like buffer; others keep their escape.
        flags = keywords.get("usedforsecurity", BindingValue(truths=frozenset({True})))
        valid = len(args) <= 1 and set(keywords) <= {"usedforsecurity"}
        return (
            BindingValue(native_kind="hash")
            if valid
            and all(native_text(item, "bytes") for item in args)
            and flags.truths
            and not (flags.unknown or flags.strings or flags.native_kind or flags.targets)
            else None
        )
    if target == "builtins.range" and args and not keywords:
        current = dependent(value, MemberDemand("native_return", key="builtins.int"))
        current = replace(current, deferred=current.deferred or not current.parameters)
        return BindingValue(element=current, unknown=any(item.unknown for item in args))
    return None


_ENCODINGS = frozenset({"utf-8", "utf8", "ascii"})


def native_content(value: BindingValue) -> bool:
    """Native text, or a qualified native Path whose text conversion cannot fail."""
    return native_text(value) or (
        value.path and not (value.unknown or value.local or value.targets or value.methods)
    )


def native_text(value: BindingValue, *kinds: str) -> bool:
    """Every alternative is one native content value of a selected kind, with no other shape."""
    pure = replace(value, deferred=False, truths=frozenset())
    return pure.native_kind in (kinds or ("text",)) and pure == BindingValue(
        native_kind=pure.native_kind
    )


def native_method(
    owner: BindingValue,
    name: str,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
) -> BindingValue | None:
    """Return a native digest or text method kind for exact supported signatures only."""
    if (
        owner.path
        and native_content(owner)
        and not args
        and (
            (name == "read_bytes" and not keywords)
            or (
                name == "read_text"
                and set(keywords) <= {"encoding"}
                and all(
                    item.strings
                    and item == BindingValue(strings=item.strings)
                    and item.strings <= _ENCODINGS
                    for item in keywords.values()
                )
            )
        )
    ):
        return BindingValue(native_kind="bytes" if name == "read_bytes" else "text")
    if keywords or any(value.spread for value in args):
        return None
    closed = all(item.strings and item == BindingValue(strings=item.strings) for item in args)
    if native_text(owner, "hash") and name == "hexdigest" and not args:
        return BindingValue(native_kind="text")
    if native_text(owner) and name in {"strip", "rstrip", "lstrip"} and len(args) <= 1 and closed:
        return BindingValue(native_kind="text")
    if (
        (
            (native_text(owner) and name == "encode")
            or (native_text(owner, "bytes") and name == "decode")
        )
        and len(args) <= 1
        and closed
        and all(item.strings <= _ENCODINGS for item in args)
    ):
        return BindingValue(native_kind="bytes" if name == "encode" else "text")
    return native_path_method(owner, name, args)


def native_path_method(
    owner: BindingValue, name: str, args: tuple[BindingValue, ...]
) -> BindingValue | None:
    """Exact Path conversion signatures; unsupported or opaque calls stay unresolved."""
    if owner.path and (
        (name in {"absolute", "as_posix"} and not args)
        or (name == "resolve" and len(args) <= 1 and all(native_flag(item) for item in args))
    ):
        # as_posix is lexical; resolve() may follow a symlink to another final name.
        names = frozenset() if name == "resolve" else owner.executable_origins
        text = (
            frozenset(PurePath(item).as_posix() for item in owner.strings)
            if name == "as_posix"
            else frozenset()
        )
        converted = replace(owner, strings=text, executable_origins=names)
        if name != "as_posix":
            return converted
        # A successful lexical conversion is native text, never a Path.
        return replace(converted, path=False, native_kind="" if owner.unknown else "text")
    return None


def native_flag(value: BindingValue) -> bool:
    """One closed native truth value with no other alternative."""
    return bool(value.truths) and value == BindingValue(truths=value.truths)


PATH_DIVIDE = ("pathlib.PurePath.__truediv__", "pathlib.PurePath.__rtruediv__")


def native_divide(left: BindingValue, right: BindingValue) -> BindingValue | None:
    """Apply one native Path division now, or retain it for each symbolic operand."""
    if not (left.path and (native_text(right) or right.strings)) and (
        left.parameters or left.projections or right.parameters or right.projections
    ):
        value = BindingValue(
            deferred=left.deferred or right.deferred,
            unknown=left.unknown or right.unknown,
            context_limited=left.context_limited or right.context_limited,
        )
        for subject, other, key in ((left, right, PATH_DIVIDE[0]), (right, left, PATH_DIVIDE[1])):
            if subject.parameters or subject.projections:
                demand = MemberDemand("native_return", key=key, selector=other)
                value = value.join(dependent(subject, demand))
        return value
    if not left.path:
        return None
    if native_text(right):
        # A native text component keeps the Path type; it never names the final leaf.
        return BindingValue(
            path=True, unknown=left.unknown, deferred=left.deferred or right.deferred
        )
    if not right.strings:
        return None
    value = BindingValue()
    for suffix in right.strings:
        if suffix in {"", "."}:
            current = left
        elif suffix == ".." or "/" in suffix or "\\" in suffix:
            current = BindingValue(unknown=True)
        else:
            exact = () if left.unknown or left.deferred else left.strings
            current = BindingValue(
                path=True,
                strings=frozenset(str(PurePath(root, suffix)) for root in exact),
                executable_origins=frozenset({suffix}),
                deferred=left.deferred or right.deferred or bool(left.parameters),
                unknown=left.unknown or right.unknown,
            )
        value = value.join(current)
    return value


def native_operation(value: BindingValue, demand: MemberDemand) -> BindingValue | None:
    """Apply a retained native operator to its substituted operand, or stay unknown."""
    if demand.key not in PATH_DIVIDE:
        return None
    other = demand.selector or BindingValue(unknown=True)
    operands = (value, other) if demand.key == PATH_DIVIDE[0] else (other, value)
    return native_divide(*operands) or BindingValue(unknown=True)


def open_operation(value: BindingValue) -> bool:
    """A native operator still waiting on an unbound operand has no closed receiver."""
    return any(
        member.kind == "native_return" and member.key in PATH_DIVIDE
        for slot in (*value.parameters, *value.projections)
        for member in slot.members
    )

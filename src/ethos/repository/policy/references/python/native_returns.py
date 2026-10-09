"""Native executable and path return provenance, independent of source invocation."""

from __future__ import annotations

from ethos.repository.policy.references.python.bindings import BindingValue


def native_leaf_return(
    target: str,
    args: tuple[BindingValue, ...],
    keywords: dict[str | None, BindingValue],
) -> BindingValue | None:
    """Native path and executable leaves retain only their actual argument provenance."""
    if target == "shutil.which":
        name = args[0] if args else keywords.get("cmd", BindingValue(unknown=True))
        return BindingValue(
            executable_origins=name.strings,
            deferred=name.deferred,
            unknown=name.unknown or (not name.strings and not name.deferred),
            context_limited=name.context_limited,
        )
    if target in {"pathlib.Path", "builtins.str"} and len(args) == 1 and not keywords:
        return BindingValue(
            strings=args[0].strings,
            executable_origins=args[0].executable_origins,
            path=target == "pathlib.Path",
            deferred=args[0].deferred,
            context_limited=args[0].context_limited,
            unknown=args[0].unknown
            or not (args[0].strings or args[0].executable_origins or args[0].deferred),
        )
    return None

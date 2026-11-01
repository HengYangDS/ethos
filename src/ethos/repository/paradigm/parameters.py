"""Declared parameters: the contract's defaults and bounds, a repository's own values, the accessor.

A repository binding may declare a value in `.ethos/rules.toml` `[paradigm.<group>]`: a lower
value applies, and a higher one applies within the parameter's bound when
`[paradigm.<group>.reasons]` states why. Any other declaration is a gap and leaves the default in
force, so a malformed value never loosens a parameter. Each composition root binds its target
repository's resolution to the invocation; adapters read a value with `parameter` and fall back
to the declared default where no repository is bound.
"""

from __future__ import annotations

import tomllib
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cached_property
from importlib import import_module
from typing import TYPE_CHECKING
from typing import Literal
from typing import NamedTuple

from ethos.repository.paradigm.gap import ParadigmGap

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import Parameter
    from ethos.contracts.paradigm.declaration import RepositoryParadigm


class ParameterResolution(NamedTuple):
    """The effective values by group, the declaration's gaps and each reasoned higher value."""

    values: dict[str, dict[str, int]]
    gaps: tuple[ParadigmGap, ...]
    deviations: tuple[dict[str, object], ...]


def parameter_resolution(rules: str | None, paradigm: RepositoryParadigm) -> ParameterResolution:
    """Resolve every declared group from the contract and the binding's `rules.toml` text."""
    carrier = f"{paradigm.binding.root}/rules.toml"
    try:
        table = tomllib.loads(rules or "")
    except tomllib.TOMLDecodeError:
        table = {}
    gaps: list[ParadigmGap] = []
    if "code_size" in _table(table, "quality"):
        repair = "replace [quality.code_size] with a repository value in [paradigm.size]"
        gaps.append(ParadigmGap("binding-restatement", f"{carrier}:quality.code_size", repair))
    rows = {(row.group, row.key): row for row in paradigm.parameter}
    values = {group: paradigm.parameter_defaults(group) for group, _key in rows}
    deviations: list[dict[str, object]] = []
    for group in _table(table, "paradigm"):
        if group not in values:
            repair = f"remove [paradigm.{group}]; the paradigm declares {', '.join(values)}"
            gaps.append(ParadigmGap("parameter-declaration", f"{carrier}:paradigm.{group}", repair))
            continue
        declared = _table(_table(table, "paradigm"), group)
        reasons = _table(declared, "reasons")
        for key, value in declared.items():
            if key == "reasons":
                continue
            row = rows.get((group, key))
            place = f"{carrier}:paradigm.{group}.{key}"
            if gap := _declaration_gap(paradigm, group, key, row, value, reasons.get(key), place):
                gaps.append(gap)
            elif row is not None and isinstance(value, int):
                values[group][key] = value
                if value > row.default:
                    deviation = {"value": value, "default": row.default, "reason": reasons[key]}
                    deviations.append({"parameter": f"{group}.{key}", **deviation})
    return ParameterResolution(values, tuple(gaps), tuple(deviations))


def _declaration_gap(
    paradigm: RepositoryParadigm,
    group: str,
    key: str,
    row: Parameter | None,
    value: object,
    reason: object,
    place: str,
) -> ParadigmGap | None:
    """Return the gap that keeps one declared value from applying, if there is one."""
    kind = f"{group}-declaration"
    if row is None:
        renamed = next(
            (
                item.key
                for item in paradigm.parameter
                if item.group == group and key in item.retired
            ),
            None,
        )
        return ParadigmGap(
            kind, place, f"rename {key} to {renamed}" if renamed else f"remove {key}"
        )
    if type(value) is not int or value <= 0:
        return ParadigmGap(kind, place, f"declare {key} as a positive integer")
    if value == row.default:
        repair = f"remove {key}; {row.default} is the paradigm's default"
        return ParadigmGap("binding-restatement", place, repair)
    if value > row.bound or (value > row.default and not _stated(reason)):
        repair = f"declare {key} at most {row.bound} with its reason, or remove it"
        return ParadigmGap(kind, place, repair)
    return None


def repository_resolution(root: Path) -> ParameterResolution:
    """Resolve the parameters that the repository's binding selects."""
    paradigm = _paradigm()
    try:
        rules = (root / paradigm.binding.root / "rules.toml").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        rules = None
    return parameter_resolution(rules, paradigm)


class _Binding:
    """One invocation's repository, resolved when a value is first read."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @cached_property
    def resolution(self) -> ParameterResolution:
        return repository_resolution(self.root)


_BOUND: ContextVar[_Binding | None] = ContextVar("repository_parameters", default=None)


@contextmanager
def repository_parameters(root: Path) -> Generator[None]:
    """Bind the target repository's parameters to the invocation for every adapter it calls."""
    token = _BOUND.set(_Binding(root))
    try:
        yield
    finally:
        _BOUND.reset(token)


def active_resolution() -> ParameterResolution:
    """Return the invocation's resolution, or the declared defaults where none is bound."""
    binding = _BOUND.get()
    return binding.resolution if binding else parameter_resolution(None, _paradigm())


def parameter(group: str, key: str) -> int:
    """Return one declared parameter's value for the invocation's repository."""
    return active_resolution().values[group][key]


type TimeoutKind = Literal[
    "gate", "tool", "git", "git_history", "probe", "lock", "download", "request", "admission"
]


def seconds(kind: TimeoutKind, given: float | None = None) -> float:
    """Return a caller's explicit value, else the invocation's `timeout.<kind>_seconds`."""
    return parameter("timeout", f"{kind}_seconds") if given is None else given


def parameter_source(group: str, key: str) -> str:
    """Return `repository` when the invocation's binding set the value, otherwise `default`."""
    declared = parameter(group, key) != _paradigm().parameter_row(group, key).default
    return "repository" if declared else "default"


def _paradigm() -> RepositoryParadigm:
    """Load the contract when a value is read; binding an invocation imports no models."""
    return import_module("ethos.contracts.paradigm.declaration").load_repository_paradigm()


def _table(value: object, key: str) -> dict[str, object]:
    """Return one TOML table, or an empty one when it is absent or not a table."""
    table = value.get(key) if isinstance(value, dict) else None
    return table if isinstance(table, dict) else {}


def _stated(reason: object) -> bool:
    """Return whether a declared reason is a non-empty string."""
    return isinstance(reason, str) and bool(reason.strip())

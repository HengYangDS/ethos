"""Declarative helpers for simple quality report commands."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

from ethos_core.result import EthosResult

ReportPayload = Mapping[str, object]
ReportLoader = Callable[[Path], ReportPayload]
ValueProjection = Callable[[ReportPayload], object]
SummaryProjection = Callable[[ReportPayload], Mapping[str, object]]
DataProjection = Callable[[ReportPayload], Mapping[str, object]]
ActionsProjection = Callable[[ReportPayload], Sequence[str]]
EmitFunction = Callable[[EthosResult], None]
StateProjection = Callable[[ReportPayload, object], str]
HeadProvider = Callable[[Path], str]
PayloadLoader = Callable[[Path], object]


def module_report(
    namespace: Mapping[str, object],
    name: str,
    *,
    current_head: HeadProvider | None = None,
) -> ReportLoader:
    """Return a late-bound report loader, optionally passing current-head fact."""

    def load(root: Path) -> ReportPayload:
        report = namespace[name]
        if not callable(report):
            msg = f"report binding is not callable: {name}"
            raise TypeError(msg)
        if current_head:
            return cast("Callable[..., ReportPayload]", report)(
                root,
                current_head=current_head(root),
            )
        return cast("ReportLoader", report)(root)

    return load


def head_bound_report(
    report: Callable[..., ReportPayload], *, current_head: HeadProvider
) -> ReportLoader:
    """Return a report loader that passes an explicit current-head fact."""
    return lambda root: report(root, current_head=current_head(root))


def payload_report(loader: PayloadLoader, *, state: str = "clean") -> ReportLoader:
    """Wrap a payload loader as an always-clean report declaration."""
    return lambda root: {"ok": True, "state": state, "payload": loader(root)}


def project_summary(**fields: ValueProjection) -> SummaryProjection:
    """Compose a summary projection from declared field projections."""
    return lambda report: {name: projection(report) for name, projection in fields.items()}


def path_value(*path: str, default: object = None) -> ValueProjection:
    """Return a nested mapping value, with an optional default for missing leaves."""

    def project(report: ReportPayload) -> object:
        current: object = report
        for part in path:
            if not isinstance(current, Mapping):
                return default
            mapping = cast("Mapping[str, object]", current)
            if part not in mapping:
                return default
            current = mapping[part]
        return current

    return project


def count_at(*path: str) -> ValueProjection:
    """Return the length of a nested sequence or mapping field."""
    return lambda report: len(
        cast("Sequence[object] | Mapping[str, object]", path_value(*path)(report))
    )


def count_of(field: str) -> ValueProjection:
    """Return the length of a sequence or mapping field."""
    return count_at(field)


def field_data(field: str) -> DataProjection:
    """Project one mapping field as command result data."""
    return lambda report: cast("Mapping[str, object]", report[field])


def advisory_state(field: str) -> StateProjection:
    """Return advisory when an otherwise-clean report carries advisory gaps."""
    return lambda report, ok: (
        "advisory" if ok and _sequence(report.get(field)) else "clean" if ok else "blocked"
    )


def constant_actions(*actions: str) -> ActionsProjection:
    """Return a next-action projection that ignores report payload details."""
    return lambda _report: actions


def conditional_actions(*, when_blocked: str, when_clean: str) -> ActionsProjection:
    """Return next actions keyed by whether a report has required gaps."""
    return lambda report: (when_blocked if _sequence(report.get("required_gaps")) else when_clean,)


def field_summary(*fields: str) -> SummaryProjection:
    """Project selected report fields into an ``EthosResult`` summary."""
    return project_summary(**{field: path_value(field) for field in fields})


class ReportCommandSpec(BaseModel):
    """Declaration for a quality command that wraps a repository report."""

    model_config = ConfigDict(frozen=True)

    command: str
    report: ReportLoader
    summary: SummaryProjection | None = None
    data: DataProjection | None = None
    next_actions: ActionsProjection | None = None
    state: StateProjection | None = None
    clean_state: str = "clean"
    blocked_state: str = "blocked"


def build_report_result(spec: ReportCommandSpec, root: Path) -> EthosResult:
    """Compile a report command declaration into an ``EthosResult``."""
    report = spec.report(root)
    ok = bool(report.get("ok"))
    state = (
        spec.state(report, ok)
        if spec.state
        else str(report.get("state") or (spec.clean_state if ok else spec.blocked_state))
    )
    required_gaps = tuple(str(gap) for gap in _sequence(report.get("required_gaps")))
    summary = dict(spec.summary(report) if spec.summary else _mapping(report.get("summary")))
    next_actions = tuple(
        str(action) for action in (spec.next_actions(report) if spec.next_actions else ())
    )
    data = dict(spec.data(report) if spec.data else report)
    return EthosResult(
        command=spec.command,
        ok=ok,
        state=state,
        summary=summary,
        required_gaps=required_gaps,
        next_actions=next_actions,
        data=data,
    )


def emit_report_command(
    spec: ReportCommandSpec,
    root: Path,
    *,
    emit_func: EmitFunction,
) -> None:
    """Emit a simple report command from its declaration."""
    emit_func(build_report_result(spec, root))


def _mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()

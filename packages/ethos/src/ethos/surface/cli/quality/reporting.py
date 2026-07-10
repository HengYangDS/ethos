"""Declarative helpers for simple quality report commands."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict

from ethos_core.result import EthosResult

ReportPayload = Mapping[str, object]
ReportLoader = Callable[[Path], ReportPayload]
SummaryProjection = Callable[[ReportPayload], Mapping[str, object]]
ActionsProjection = Callable[[ReportPayload], Sequence[str]]
EmitFunction = Callable[[EthosResult], None]
StateProjection = Callable[[ReportPayload, bool], str]


def module_report(namespace: Mapping[str, object], name: str) -> ReportLoader:
    """Return a report loader that resolves a module binding at call time."""

    def load(root: Path) -> ReportPayload:
        report = namespace[name]
        if not callable(report):
            msg = f"report binding is not callable: {name}"
            raise TypeError(msg)
        return report(root)

    return load


def constant_actions(*actions: str) -> ActionsProjection:
    """Return a next-action projection that ignores report payload details."""
    return lambda _report: actions


def conditional_actions(*, when_blocked: str, when_clean: str) -> ActionsProjection:
    """Return next actions keyed by whether a report has required gaps."""
    return lambda report: (when_blocked if _sequence(report.get("required_gaps")) else when_clean,)


def field_summary(*fields: str) -> SummaryProjection:
    """Project selected report fields into an ``EthosResult`` summary."""
    return lambda report: {field: report[field] for field in fields}


class ReportCommandSpec(BaseModel):
    """Declaration for a quality command that wraps a repository report."""

    model_config = ConfigDict(frozen=True)

    command: str
    report: ReportLoader
    summary: SummaryProjection | None = None
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
    return EthosResult(
        command=spec.command,
        ok=ok,
        state=state,
        summary=summary,
        required_gaps=required_gaps,
        next_actions=next_actions,
        data=dict(report),
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
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()

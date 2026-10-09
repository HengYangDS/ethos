"""Interpret official pytest report events before checking their JUnit projection."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class SubtestContext(BaseModel):
    """The official serializer retains a subtest's context under its parent."""

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")
    msg: str | None = None
    kwargs: dict[str, str] = Field(default_factory=dict)


class PytestEvent(BaseModel):
    """Relevant native fields; future informational fields do not change meaning."""

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")
    kind: str = Field(alias="$report_type", min_length=1)
    nodeid: str = ""
    outcome: Literal["passed", "failed", "skipped"] | None = None
    when: Literal["setup", "call", "teardown", "config", "collect", "runtest"] | None = None
    worker_id: str = ""
    item_index: int | None = Field(default=None, ge=0)
    pytest_version: str = ""
    exitstatus: int | None = Field(default=None, ge=0, le=5)
    subtest: SubtestContext | None = Field(default=None, alias="_subtest.context")
    wasxfail: str | None = None
    category: str | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class PytestReport:
    """Report-event totals differ from parent test-case identities."""

    total: int
    failures: int
    errors: int
    skipped: int
    cases: tuple[tuple[str, str], ...]
    outcomes: tuple[tuple[str, str, str], ...]
    warnings: tuple[PytestEvent, ...]
    failed: bool


@dataclass(slots=True)
class _Parent:
    setup: PytestEvent | None = None
    call: PytestEvent | None = None
    teardown: PytestEvent | None = None
    subtests: list[PytestEvent] = field(default_factory=list)

    def observe(self, event: PytestEvent) -> None:
        """Each execution preserves setup, child calls, parent call and teardown order."""
        if event.kind == "SubTestReport":
            if (
                self.setup is None
                or self.setup.outcome != "passed"
                or self.call is not None
                or self.teardown is not None
                or event.when != "call"
                or event.subtest is None
            ):
                msg = "pytest_subtest_unbound"
                raise ValueError(msg)
            self.subtests.append(event)
        elif event.when == "setup" and self.setup is None:
            self.setup = event
        elif (
            event.when == "call"
            and self.setup is not None
            and self.setup.outcome == "passed"
            and self.call is None
            and self.teardown is None
        ):
            self.call = event
        elif (
            event.when == "teardown"
            and self.setup is not None
            and self.teardown is None
            and (self.setup.outcome != "passed" or self.call is not None)
        ):
            self.teardown = event
        else:
            msg = "pytest_report_order_invalid"
            raise ValueError(msg)

    def reports(self) -> tuple[PytestEvent, ...]:
        """Only terminal test reports contribute to the producer's JUnit totals."""
        if self.setup is None or self.teardown is None:
            msg = "pytest_execution_incomplete"
            raise ValueError(msg)
        return tuple(
            event
            for event in (self.setup, *self.subtests, self.call, self.teardown)
            if event is not None and (event.when == "call" or event.outcome != "passed")
        )


def _case_identity(nodeid: str) -> tuple[str, str]:
    address, bracket, parameters = nodeid.partition("[")
    names = address.split("::")
    path = PurePosixPath(names[0])
    if (
        len(names) < 2
        or not names[-1]
        or path.is_absolute()
        or any(part in {".", ".."} for part in path.parts)
        or "\\" in names[0]
    ):
        msg = "pytest_nodeid_invalid"
        raise ValueError(msg)
    names[0] = names[0].replace("/", ".").removesuffix(".py")
    return ".".join(names[:-1]), names[-1] + bracket + parameters


def _terminal_events(text: str) -> tuple[PytestEvent, ...]:
    """A complete original stream binds the native producer and terminal outcome."""
    try:
        events = tuple(PytestEvent.model_validate_json(line) for line in text.splitlines())
    except ValueError as error:
        msg = "pytest_event_invalid"
        raise ValueError(msg) from error
    if (
        not events
        or events[0].kind != "SessionStart"
        or not events[0].pytest_version
        or events[-1].kind != "SessionFinish"
        or events[-1].exitstatus is None
        or any(event.kind in {"SessionStart", "SessionFinish"} for event in events[1:-1])
    ):
        msg = "pytest_terminal_missing"
        raise ValueError(msg)
    return events


def _junit_outcome(report: PytestEvent) -> str | None:
    """Conserve each native outcome under its parent identity in the XML projection."""
    if report.outcome == "failed" and report.when != "call":
        return "error"
    if report.outcome == "skipped" or (report.outcome == "failed" and report.wasxfail is not None):
        return "skipped"
    return "failure" if report.outcome == "failed" else None


def pytest_report(text: str) -> PytestReport:
    """Read one original official event stream, never infer children from XML counts."""
    events = _terminal_events(text)
    parents: dict[tuple[str, str, int | None], _Parent] = {}
    warnings: list[PytestEvent] = []
    collection_failed = False
    for event in events[1:-1]:
        if event.kind in {"TestReport", "SubTestReport"}:
            if event.outcome is None or event.when not in {"setup", "call", "teardown"}:
                msg = "pytest_event_invalid"
                raise ValueError(msg)
            _case_identity(event.nodeid)
            key = event.nodeid, event.worker_id, event.item_index
            parents.setdefault(key, _Parent()).observe(event)
        elif event.kind == "WarningMessage":
            if not event.message:
                msg = "pytest_event_invalid"
                raise ValueError(msg)
            warnings.append(event)
        elif event.kind == "CollectReport":
            if event.outcome is None:
                msg = "pytest_event_invalid"
                raise ValueError(msg)
            collection_failed |= event.outcome == "failed"
    reports = tuple(report for parent in parents.values() for report in parent.reports())
    if not reports:
        msg = "pytest_empty"
        raise ValueError(msg)
    failures = sum(
        report.outcome == "failed" and report.when == "call" and report.wasxfail is None
        for report in reports
    )
    errors = sum(report.outcome == "failed" and report.when != "call" for report in reports)
    skipped = sum(
        report.outcome == "skipped" or (report.outcome == "failed" and report.wasxfail is not None)
        for report in reports
    )
    correction = sum(
        parent.teardown is not None
        and parent.teardown.outcome == "failed"
        and parent.call is not None
        and parent.call.outcome == "passed"
        for parent in parents.values()
    )
    cases = tuple(
        _case_identity(nodeid)
        for (nodeid, _, _), parent in parents.items()
        for _ in range(
            2
            if parent.call is not None
            and parent.call.outcome == "failed"
            and parent.teardown is not None
            and parent.teardown.outcome == "failed"
            else 1
        )
    )
    return PytestReport(
        total=len(reports) - correction,
        failures=failures,
        errors=errors,
        skipped=skipped,
        cases=cases,
        outcomes=tuple(
            (*_case_identity(report.nodeid), tag)
            for report in reports
            if (tag := _junit_outcome(report)) is not None
        ),
        warnings=tuple(warnings),
        failed=bool(
            events[-1].exitstatus
            or failures
            or errors
            or warnings
            or collection_failed
            or all(report.outcome != "passed" for report in reports)
        ),
    )

"""Aggregators reduce their parts through one outcome: a part's cause and class reach the top."""

from __future__ import annotations

from types import SimpleNamespace

from filelock import Timeout

import ethos.adapters.gates.runner as runner
import ethos.application.inspection as inspection
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh_report import failure_report
from ethos.adapters.mutation.lane_retirement.operation import retirement_failure
from ethos.contracts.outcome import refusal
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane

LATE = refusal("subject_gap:path", "second_gap", verdict="unknown")


def test_host_observation_keeps_a_timed_out_gate_cause_and_class(tmp_path, monkeypatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    timed = runner.ActionRunResult(
        "tests",
        ("tests",),
        "unknown",
        124,
        diagnostics=({"kind": "gate_timeout", "required_gaps": ["gate_timeout:tests"]},),
    )
    policy = SimpleNamespace(
        gaps=(),
        nodes=(),
        registry={},
        digest="d",
        result_gaps=lambda checks, **_: tuple(
            f"gate_execution_not_proven:{c['action_id']}" for c in checks
        ),
    )
    monkeypatch.setattr(runner, "resolve_gate_policy", lambda *_a, **_k: policy)
    monkeypatch.setattr(runner, "run_gate_graph", lambda *_a, **_k: (timed,))
    observed = runner.observe_gate_execution(repo)
    assert observed["verdict"] == "unknown"
    assert observed["required_gaps"] == [
        "gate_unknown:tests",
        "gate_timeout:tests",
        "gate_execution_not_proven:tests",
    ]
    assert observed["diagnostics"][0]["kind"] == "gate_timeout"


def test_status_keeps_an_unknown_resolution_unknown(tmp_path, monkeypatch) -> None:
    root = prepared_work_lane(tmp_path).worktree
    unknown = CurrentResolution(
        verdict="unknown",
        authority=None,
        commitment=None,
        scope=CurrentScope(()),
        required_gaps=("openspec_scope_unavailable",),
    )
    monkeypatch.setattr(inspection, "resolve_current_resolution", lambda *_a, **_k: unknown)
    result = inspection.inspect_repository(root)
    assert (result.verdict, result.state) == ("unknown", "unknown"), result.required_gaps
    assert "openspec_scope_unavailable" in result.required_gaps


def test_refresh_and_retirement_failures_keep_every_gap_and_the_class() -> None:
    refused = failure_report(("lane", "candidate", "c" * 40, "/candidate"), "a" * 40, LATE)
    assert (refused["verdict"], refused["required_gaps"]) == ("unknown", list(LATE.outcome.gaps))
    retired = retirement_failure(LATE)
    assert (retired["verdict"], retired["required_gaps"]) == ("unknown", list(LATE.outcome.gaps))
    held = retirement_failure(Timeout("lock"))
    assert (held["verdict"], held["required_gaps"]) == ("block", ["lane_retirement_in_progress"])

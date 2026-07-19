from __future__ import annotations

# ruff: noqa: TC003
from pathlib import Path

import pytest

import ethos.surface.cli.root.lifecycle as root_lifecycle
from ethos.adapters.mutation.closeout import core as closeout_core
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.lifecycle.core import MutationEvaluation
from tests.support.subprocesses import completed as cp


def _run_closeout(tmp_path: Path, monkeypatch, *, statuses, reports):
    status_iter = iter(statuses)
    report_iter = iter(reports)
    audit_heads: list[str] = []
    control_heads: list[str] = []
    emitted: list[object] = []
    events: list[str] = []
    monkeypatch.setattr(root_lifecycle, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(root_lifecycle.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        root_lifecycle,
        "evaluate_closeout_mutation",
        lambda *_args, **_kwargs: MutationEvaluation(ok=True, state="ready"),
    )
    monkeypatch.setattr(root_lifecycle.land_core, "closeout_audit_root", lambda *_args: tmp_path)

    def audit(*_args, current_head=""):
        events.append("audit")
        audit_heads.append(current_head)
        return {"ok": True, "required_gaps": [], "governance_context": {}}

    monkeypatch.setattr(root_lifecycle.land_core, "repository_audit_after_admission", audit)
    monkeypatch.setattr(
        root_lifecycle,
        "completed_active_changes_report",
        lambda _root: {"ok": True, "required_gaps": []},
    )

    def status(*_args, **_kwargs):
        events.append("status")
        return {"candidate": {"head": next(status_iter)}}

    monkeypatch.setattr(root_lifecycle, "workspace_status", status)

    def control_report(**kwargs):
        events.append("control")
        control_heads.append(kwargs["candidate_head"])
        return next(report_iter)

    monkeypatch.setattr(root_lifecycle, "control_replacement_report", control_report)
    monkeypatch.setattr(
        root_lifecycle,
        "apply_candidate_to_accepted",
        lambda **_kwargs: pytest.fail("effect must not run after failed recheck"),
    )
    monkeypatch.setattr(root_lifecycle, "emit", lambda result, **_kwargs: emitted.append(result))
    monkeypatch.setattr(root_lifecycle, "_closeout_result", lambda payload: payload)
    root_lifecycle.land(
        apply=True,
        authorize=True,
        expect_head="a" * 40,
        closeout=True,
        root=tmp_path,
        json_output=True,
    )
    return emitted[0], control_heads, audit_heads, events


def test_closeout_rechecks_control_receipt_before_effect(tmp_path: Path, monkeypatch) -> None:
    result, _heads, audit_heads, events = _run_closeout(
        tmp_path,
        monkeypatch,
        statuses=("b" * 40, "b" * 40, "b" * 40),
        reports=(
            {"verdict": "allow", "required_gaps": []},
            {"verdict": "defer", "required_gaps": ["fresh_control_gap"]},
        ),
    )
    assert result.ok is False
    assert result.gaps == ("fresh_control_gap",)
    assert audit_heads == ["b" * 40]
    assert events[:2] == ["status", "audit"]


def test_closeout_blocks_candidate_head_changed_after_full_audit(
    tmp_path: Path, monkeypatch
) -> None:
    result, control_heads, audit_heads, events = _run_closeout(
        tmp_path,
        monkeypatch,
        statuses=("b" * 40, "c" * 40),
        reports=({"verdict": "allow", "required_gaps": []},),
    )
    assert control_heads == []
    assert audit_heads == ["b" * 40]
    assert events[:2] == ["status", "audit"]
    assert result.ok is False
    assert result.gaps == ("candidate_head_changed_after_closeout_audit",)


@pytest.mark.parametrize(
    ("accepted_now", "candidate_now", "expected_gap"),
    [
        ("h2", "c2", "accepted_advanced_concurrently"),
        ("h1", "c3", "candidate_head_changed_after_control_replacement_check"),
        ("h1", "c2", "accepted_atomic_update_rejected"),
    ],
)
def test_ref_transaction_failure_distinguishes_observed_ref_state(
    tmp_path: Path, accepted_now: str, candidate_now: str, expected_gap: str
) -> None:
    request = closeout_core.CloseoutRequest(
        root=tmp_path,
        policy=BranchRolePolicy(),
        current_head="h1",
        candidate_head="c2",
        candidate_path=tmp_path,
        worktrees=[],
    )
    accepted = closeout_core.CloseoutTransition("refs/heads/dev", "h1", "c2", "c2")

    def observe(_root, *args, **_kwargs):
        return cp(accepted_now if args[-1] == accepted.ref_name else candidate_now)

    result = closeout_core._ref_transaction_failure(  # noqa: RUF100, SLF001 - exact failure classification contract
        request, accepted, cp(stderr="transaction rejected", returncode=1), observe
    )

    assert result["required_gaps"] == [expected_gap]
    assert result["stderr"] == "transaction rejected"

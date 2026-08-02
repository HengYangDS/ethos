from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.domain.land.closeout as closeout
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.verdict import observation_verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from pathlib import Path


def _decision(verdict, *gaps) -> AdmissionDecision:
    return AdmissionDecision(
        verdict=verdict,
        subject=MutationSubject(action="test", resource="repository:test"),
        basis=DecisionBasis(
            enforcement_boundary="test",
            identity_basis="test",
            evidence_boundary="test",
            verifier_provenance="test",
            time_basis="test",
        ),
        required_gaps=gaps,
    )


def test_admission_decision_authorizes_only_pass() -> None:
    passed = _decision("pass")
    blocked = _decision("block", "gap")
    unknown = _decision("unknown")

    assert passed.verdict == "pass"
    assert blocked.verdict == "block"
    assert unknown.verdict == "unknown"
    assert all(not hasattr(decision, "ok") for decision in (passed, blocked, unknown))


def test_closeout_helpers_authorize_only_pass(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    candidate = tmp_path / "candidate"
    passed = _decision("pass")
    blocked = _decision("block", "gap")
    unknown = _decision("unknown")
    monkeypatch.setattr(
        closeout,
        "workspace_status",
        lambda *_args, **_kwargs: {"candidate": {"worktree_path": candidate.as_posix()}},
    )
    monkeypatch.setattr(
        closeout.ethos.domain.status,
        "audit_for_root",
        lambda root, **_kwargs: {"verdict": "pass", "root": root.as_posix()},
    )

    assert closeout.closeout_audit_root(repo, passed) == candidate
    assert closeout.closeout_audit_root(repo, blocked) == repo
    assert closeout.closeout_audit_root(repo, unknown) == repo
    assert closeout.repository_audit_after_admission(repo, passed)["root"] == repo.as_posix()
    for decision in (blocked, unknown):
        report = closeout.repository_audit_after_admission(repo, decision)
        assert report["verdict"] == "block"
        assert report["state"] == "skipped"
        assert report["reason"] == "mutation_admission_blocked"


def test_observation_verdict_preserves_unknown_and_blocks_warnings() -> None:
    assert observation_verdict(ok=True) == "pass"
    assert observation_verdict(ok=False) == "block"
    assert observation_verdict(ok=None, required_gaps=("missing_fact",)) == "unknown"
    assert observation_verdict(ok=True, warnings=("warning",)) == "block"


def test_verdict_reducer_orders_block_before_unknown_before_pass() -> None:
    assert reduce_verdicts("pass", "pass") == "pass"
    assert reduce_verdicts("pass", "unknown") == "unknown"
    assert reduce_verdicts("unknown", "block") == "block"
    assert reduce_verdicts("pass", required_gaps=("hard_gap",)) == "block"
    assert reduce_verdicts() == "unknown"


def test_report_verdict_requires_explicit_semantics_and_blocks_adverse_diagnostics() -> None:
    assert report_verdict({"verdict": "unknown", "ok": True}) == "unknown"
    assert report_verdict({"ok": False, "required_gaps": ["failed"]}) == "unknown"
    assert report_verdict({"ok": True, "warnings": ["warning"]}) == "block"
    assert (
        report_verdict(
            {"verdict": "pass", "diagnostics": [{"severity": "warning", "message": "warn"}]}
        )
        == "block"
    )
    assert (
        report_verdict(
            {"verdict": "pass", "diagnostics": [{"severity": "error", "code": "failed"}]}
        )
        == "block"
    )
    assert (
        report_verdict(
            {"verdict": "pass", "diagnostics": [{"severity": "info", "message": "note"}]}
        )
        == "pass"
    )
    assert report_verdict({}) == "unknown"

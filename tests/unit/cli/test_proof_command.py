"""Preserve proof resolution failures and reuse one resolved repository context."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from tests.support.proof import conformant_proof_checks
from tests.support.semantic import attestation_fixture
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _plan(*, gap: str = ""):
    commitment = commitment_fixture(
        id="repository:proof-command", acceptance=("acceptance:fixture",)
    )
    return compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head="a" * 40,
            tree="b" * 40,
            observed_at=datetime.now(UTC),
            values={},
        ),
        (PlanNode(id="gate", kind="check", command=("gate",)),),
        policy={
            "gates": [
                {
                    "id": "gate",
                    "kind": "test",
                    "command": ["gate"],
                    "trust_bearing": True,
                    "evidence_class": "test",
                }
            ]
        },
        required_gaps=(gap,) if gap else (),
    )


def _check(*, verdict: str = "pass", trust_bearing: bool = True) -> dict[str, object]:
    return conformant_proof_checks(_plan())[0] | {
        "exit_code": 0 if verdict != "unknown" else None,
        "verdict": verdict,
        "trust_bearing": trust_bearing,
    }


def _attestation(verdict: str = "pass"):
    return attestation_fixture(
        predicate="proof:repository",
        verifier="agent:test:proof-command",
        subject="repository:proof-command",
        issued_at=datetime(2026, 1, 1, tzinfo=UTC),
        verdict=verdict,
        payload_kind="proof:repository",
        payload_body={"artifact": {"path": "artifact.json", "sha256": "sha256:" + "d" * 64}},
        commitment_digest="a" * 64,
    )


def _options(**updates: object) -> SimpleNamespace:
    values = {
        "objective": "ethos proof",
        "scope": "repository",
        "execute": False,
        "gate": (),
        "full": False,
        "change": None,
        "expect_head": None,
        "host": False,
        "probe": False,
    }
    values.update(updates)
    return SimpleNamespace(**values)


def _arrange(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    plan=None,
    checks: tuple[dict[str, object], ...] = (),
    runs_ok: bool = True,
    audit=None,
):
    emitted = []
    repo = tmp_path / "repo"
    repo.mkdir()
    selected_plan = plan or _plan()
    audit = audit or {
        "verdict": "pass",
        "mode": "repository",
        "governance_context": {"contract": "governed_repository"},
        "required_gaps": [],
        "openspec": {"mode": "shape"},
    }
    lifecycle = {
        "verdict": "pass",
        "change": "",
        "schema_name": "",
        "required_gaps": [],
        "summary": {"change_count": 0},
    }
    commitment = commitment_fixture(id="change:proof-command", acceptance=("acceptance:fixture",))
    binding = CurrentResolution(
        verdict="pass",
        authority=None,
        commitment=commitment,
        scope=CurrentScope(("changed.py",)),
    )
    monkeypatch.setattr(proof_cli, "resolve_root", lambda _root: repo)
    monkeypatch.setattr(proof_cli, "_emit_host_gate_observation", lambda **_kwargs: False)
    monkeypatch.setattr(
        proof_cli,
        "_proof_context",
        lambda *_args, **_kwargs: (
            "a" * 40,
            audit,
            binding,
            lifecycle,
        ),
    )
    monkeypatch.setattr(proof_cli, "proof_plan", lambda *_args, **_kwargs: selected_plan)
    monkeypatch.setattr(
        proof_cli,
        "run_plan_checks",
        lambda **_kwargs: (list(checks or (_check(),)), runs_ok),
    )
    monkeypatch.setattr(proof_cli, "emit", lambda result, **_kwargs: emitted.append(result))
    return repo, emitted


@pytest.mark.parametrize("verdict", ["block", "unknown"])
def test_invalid_common_audit_stops_before_check_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, verdict: str
) -> None:
    """Known governance failure prevents spending work or minting proof first."""
    audit = {
        "verdict": verdict,
        "required_gaps": ["protected_branches_policy_missing"],
        "next_action": "repair declared protected roles",
    }
    repo, emitted = _arrange(monkeypatch, tmp_path, audit=audit)

    def unexpected(**_kwargs):
        pytest.fail("checks must not execute after failed common admission")

    monkeypatch.setattr(proof_cli, "run_plan_checks", unexpected)
    proof_cli.prove(_options(execute=True), root=repo, json_output=True)
    assert emitted[-1].verdict == verdict
    assert emitted[-1].required_gaps == ("protected_branches_policy_missing",)
    assert emitted[-1].next_action == "repair declared protected roles"


@pytest.mark.parametrize(
    ("case", "expected_gap", "next_action"),
    [
        ("plan-error", "proof_plan_invalid", "ethos plan --changed --json"),
        ("plan-blocked", "plan_gap", "repair the Commitment or repository facts"),
        ("runner-error", "proof_plan_head_missing", "ethos plan --changed --json"),
    ],
)
def test_prove_fail_closed_before_result_compilation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_gap: str,
    next_action: str,
) -> None:
    plan = _plan(gap="plan_gap") if case == "plan-blocked" else _plan()
    _repo, emitted = _arrange(monkeypatch, tmp_path, plan=plan)
    if case != "plan-blocked":
        target = "proof_plan" if case == "plan-error" else "run_plan_checks"
        monkeypatch.setattr(proof_cli, target, Mock(side_effect=ValueError(expected_gap)))

    proof_cli.prove(root=tmp_path, json_output=True)

    assert emitted[-1].required_gaps == (expected_gap,)
    assert emitted[-1].next_action == next_action


def test_prove_preserves_nonpassing_current_resolution_without_planning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, emitted = _arrange(monkeypatch, tmp_path)
    resolution = CurrentResolution(
        verdict="block",
        authority=None,
        commitment=None,
        scope=CurrentScope(()),
        required_gaps=("invocation_actor_missing:work/feature",),
        next_action="export ETHOS_ACTOR=agent:test:case:agent-a",
        user_decision_required=True,
    )
    monkeypatch.setattr(
        proof_cli,
        "_proof_context",
        lambda *_args, **_kwargs: (
            "a" * 40,
            {"verdict": "pass", "required_gaps": []},
            resolution,
            {},
        ),
    )
    monkeypatch.setattr(
        proof_cli,
        "proof_plan",
        Mock(
            side_effect=AssertionError(
                "proof planning must not run after current resolution blocks"
            )
        ),
    )

    proof_cli.prove(root=tmp_path, json_output=True)

    result = emitted[-1]
    assert result.verdict == resolution.verdict
    assert result.required_gaps == resolution.required_gaps
    assert result.next_action == resolution.next_action
    assert result.user_decision_required is resolution.user_decision_required


def test_prove_does_not_replace_unexpected_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(proof_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(proof_cli, "_emit_host_gate_observation", lambda **_kwargs: False)
    monkeypatch.setattr(
        proof_cli.status_domain,
        "audit_for_root",
        lambda *_args, **_kwargs: {"verdict": "pass", "required_gaps": []},
    )
    monkeypatch.setattr(
        proof_cli,
        "workspace_status_observation",
        lambda *_args, **_kwargs: (
            {"head": "a" * 40, "branch": "dev", "role": "accepted"},
            None,
        ),
    )
    monkeypatch.setattr(
        proof_cli,
        "resolve_current_resolution",
        Mock(side_effect=ValueError("resolution_failed")),
    )

    with pytest.raises(ValueError, match=r"^resolution_failed$"):
        proof_cli.prove(root=tmp_path, json_output=True)


@pytest.mark.parametrize(
    ("case", "options", "check", "expected_gap"),
    [
        ("ready", _options(), _check(), ""),
        ("full-dry", _options(full=True), _check(), "full_proof_requires_execute"),
        ("head-drift", _options(expect_head="0" * 40), _check(), "expected_head_mismatch"),
        ("scope", _options(scope="novel"), _check(), "unknown_proof_scope:novel"),
        ("gate-failed", _options(execute=True), _check(verdict="block"), "gate_failed:gate"),
        ("gate-unknown", _options(execute=True), _check(verdict="unknown"), "gate_unknown:gate"),
        (
            "trust",
            _options(execute=True),
            _check(trust_bearing=False),
            "trust_bearing_proof_missing",
        ),
    ],
)
def test_prove_result_matrix(monkeypatch, tmp_path, case, options, check, expected_gap) -> None:
    """Each native outcome determines one state and one actionable continuation."""
    _repo, emitted = _arrange(monkeypatch, tmp_path, checks=(check,))
    monkeypatch.setattr(
        proof_cli,
        "issue_proof_attestation",
        lambda _repo, payload: _attestation(str(payload["verdict"])),
    )
    proof_cli.prove(options, root=tmp_path, json_output=True)
    result = emitted[-1]
    assert result.state == ("gapped" if expected_gap else "ready")
    assert (expected_gap in result.required_gaps) is bool(expected_gap)
    assert result.next_action == (
        "ethos plan --changed --json" if expected_gap else "ethos prove --execute"
    )
    assert result.data["expected_head"]["matches"] is (case != "head-drift")


@pytest.mark.parametrize("focused", [False, True])
def test_prove_persists_pass_and_routes_the_next_public_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, focused: bool
) -> None:
    _repo, emitted = _arrange(monkeypatch, tmp_path)
    persisted = []
    monkeypatch.setattr(
        proof_cli, "issue_proof_attestation", lambda *_args, **_kwargs: _attestation()
    )
    monkeypatch.setattr(
        proof_cli, "persist_proof_attestation", lambda *args, **_kwargs: persisted.append(args)
    )
    options = _options(execute=True, gate=("gate",) if focused else ())

    proof_cli.prove(options, root=tmp_path, json_output=True)

    result = emitted[-1]
    assert result.state == "proven"
    assert result.next_action == ("ethos prove --json" if focused else "ethos land")
    assert result.data["artifact_reference"]["path"] == "artifact.json"
    assert len(persisted) == 1


@pytest.mark.parametrize("boundary", ["issuance", "persistence"])
def test_prove_reports_failed_evidence_boundary_once(monkeypatch, tmp_path, boundary) -> None:
    """Issuance failure emits once; failed persistence reissues a blocked result."""
    _repo, emitted = _arrange(monkeypatch, tmp_path)
    issued = []

    def issue(_repo, payload):
        issued.append(payload)
        return _attestation(str(payload["verdict"]))

    monkeypatch.setattr(proof_cli, "issue_proof_attestation", issue)
    target, error, expected = (
        ("issue_proof_attestation", "proof_binding_invalid", "proof_binding_invalid")
        if boundary == "issuance"
        else (
            "persist_proof_attestation",
            "collision",
            "proof_attestation_persistence_failed:collision",
        )
    )
    monkeypatch.setattr(proof_cli, target, Mock(side_effect=ValueError(error)))
    proof_cli.prove(_options(execute=True), root=tmp_path, json_output=True)
    assert len(emitted) == 1
    assert emitted[0].state == "gapped"
    assert emitted[0].required_gaps == (expected,)
    assert [payload["verdict"] for payload in issued] == (
        [] if boundary == "issuance" else ["pass", "block"]
    )


def test_compact_and_detailed_proof_preserve_the_same_observed_meaning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A presentation choice cannot drop coordinates, checks or lifecycle identity."""
    _repo, emitted = _arrange(monkeypatch, tmp_path)
    proof_cli.prove(_options(expect_head="a" * 40), root=tmp_path, json_output=True)
    compact = emitted[-1]
    proof_cli.prove(_options(expect_head="a" * 40, gate=("gate",)), root=tmp_path, json_output=True)
    detailed = emitted[-1]
    assert compact.state == detailed.state == "ready"
    assert compact.data["boundary"] == "repository"
    assert detailed.data["boundary"] == "focused"
    assert compact.data["changed_path_count"] == len(detailed.data["changed_paths"]) == 1
    assert compact.data["gate_ids"] == ("gate",)
    for key in ("scope", "scope_binding", "host_probe", "checks", "expected_head", "attestation"):
        assert compact.data[key] == detailed.data[key], key
    assert detailed.data["expected_head"]["current"] == "a" * 40
    assert detailed.data["checks"][0]["action_id"] == "gate"
    assert compact.data["checks"][0]["duration_seconds"] is None
    assert compact.data["checks"][0]["started_after_seconds"] is None
    assert "transition_plan" not in compact.data
    assert detailed.data["transition_plan"]["facts"]["head"] == "a" * 40


@pytest.mark.parametrize("openspec", [False, True])
def test_prove_compiles_one_shared_repository_and_openspec_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, openspec: bool
) -> None:
    emitted = []
    scope = CurrentScope(("a.py",))
    commitment = commitment_fixture(id="change:proof-command", acceptance=("acceptance:fixture",))
    lifecycle = {
        "verdict": "pass",
        "change": "proof-command",
        "schema_name": "spec-driven",
        "required_gaps": [],
        "summary": {"change_count": 1},
    }
    binding = CurrentResolution(
        verdict="pass",
        authority=None,
        commitment=commitment,
        scope=scope,
        openspec=lifecycle if openspec else {},
    )
    audit = {
        "verdict": "pass",
        "mode": "repository",
        "governance_context": {"contract": "governed_repository"},
        "required_gaps": [],
        "openspec": {"mode": "deep"},
    }
    status = {"head": "a" * 40, "branch": "dev", "role": "accepted"}
    authority = object()
    monkeypatch.setattr(proof_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(proof_cli, "_emit_host_gate_observation", lambda **_kwargs: False)

    def audit_once(_root, **kwargs):
        assert kwargs["openspec"] == (
            lifecycle
            if openspec
            else {"verdict": "pass", "state": "not_applicable", "required_gaps": []}
        )
        return audit

    monkeypatch.setattr(proof_cli.status_domain, "audit_for_root", audit_once)
    monkeypatch.setattr(
        proof_cli,
        "workspace_status_observation",
        lambda *_args, **_kwargs: (status, authority),
    )

    def resolve(*_args, **kwargs):
        assert kwargs["status"] is status
        assert kwargs["authority"] is authority
        assert kwargs["change"] is None
        assert kwargs["changed"] is True
        return binding

    monkeypatch.setattr(proof_cli, "resolve_current_resolution", resolve)

    def compile_plan(*_args, **kwargs):
        assert kwargs["resolution"] is binding
        return _plan()

    monkeypatch.setattr(proof_cli, "proof_plan", compile_plan)
    monkeypatch.setattr(proof_cli, "run_plan_checks", lambda **_kwargs: ([_check()], True))
    monkeypatch.setattr(proof_cli, "emit", lambda result, **_kwargs: emitted.append(result))

    proof_cli.prove(_options(full=True), root=tmp_path, json_output=True)

    assert emitted[-1].data["changed_paths"] == ("a.py",)
    observed = emitted[-1].data["openspec_lifecycle"]
    assert observed.get("state") == (None if openspec else "not_applicable")
    assert observed.get("change") == ("proof-command" if openspec else None)

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.openspec.start_effect import CurrentGenerationBinding
from ethos.adapters.openspec.start_effect import CurrentGenerationScope
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
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
    return {
        "action_id": "gate",
        "command": ["gate"],
        "exit_code": 0 if verdict != "unknown" else None,
        "stdout": "",
        "stderr": "",
        "verdict": verdict,
        "evidence_class": "test",
        "trust_bearing": trust_bearing,
        "diagnostics": [],
    }


def _attestation(verdict: str = "pass") -> SimpleNamespace:
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "proof:repository",
            "verifier": "agent:test:proof-command",
            "subject": "repository:proof-command",
            "issued_at": datetime(2026, 1, 1, tzinfo=UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": verdict,
            "payload": {
                "kind": "proof:repository",
                "body": {"artifact": {"path": "artifact.json", "sha256": "sha256:" + "d" * 64}},
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": "a" * 64,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
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
):
    emitted = []
    repo = tmp_path / "repo"
    repo.mkdir()
    selected_plan = plan or _plan()
    audit = {
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
    binding = CurrentGenerationBinding({}, commitment, CurrentGenerationScope(("changed.py",), {}))
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


@pytest.mark.parametrize(
    ("case", "expected_gap", "next_action"),
    [
        ("plan-error", "proof_plan_invalid", "ethos adopt"),
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
    if case == "plan-error":
        monkeypatch.setattr(
            proof_cli,
            "proof_plan",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError(expected_gap)),
        )
    elif case == "runner-error":
        monkeypatch.setattr(
            proof_cli,
            "run_plan_checks",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError(expected_gap)),
        )

    proof_cli.prove(root=tmp_path, json_output=True)

    assert emitted[-1].required_gaps == (expected_gap,)
    assert emitted[-1].next_action == next_action


@pytest.mark.parametrize(
    ("case", "options", "checks", "expected_gap", "state", "next_action"),
    [
        ("ready", _options(), (_check(),), "", "ready", "ethos prove --execute"),
        (
            "full-dry",
            _options(full=True),
            (_check(),),
            "full_proof_requires_execute",
            "gapped",
            "ethos plan --changed --json",
        ),
        (
            "head-drift",
            _options(expect_head="0" * 40),
            (_check(),),
            "expected_head_mismatch",
            "gapped",
            "ethos plan --changed --json",
        ),
        (
            "scope",
            _options(scope="novel"),
            (_check(),),
            "unknown_proof_scope:novel",
            "gapped",
            "ethos plan --changed --json",
        ),
        (
            "gate-failed",
            _options(execute=True),
            (_check(verdict="block"),),
            "gate_failed:gate",
            "gapped",
            "ethos plan --changed --json",
        ),
        (
            "gate-unknown",
            _options(execute=True),
            (_check(verdict="unknown"),),
            "gate_unknown:gate",
            "gapped",
            "ethos plan --changed --json",
        ),
        (
            "trust",
            _options(execute=True),
            (_check(trust_bearing=False),),
            "trust_bearing_proof_missing",
            "gapped",
            "ethos plan --changed --json",
        ),
    ],
)
def test_prove_result_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    options: SimpleNamespace,
    checks: tuple[dict[str, object], ...],
    expected_gap: str,
    state: str,
    next_action: str,
) -> None:
    _repo, emitted = _arrange(monkeypatch, tmp_path, checks=checks)
    monkeypatch.setattr(
        proof_cli,
        "issue_proof_attestation",
        lambda _repo, payload: _attestation(str(payload["verdict"])),
    )

    proof_cli.prove(options, root=tmp_path, json_output=True)

    result = emitted[-1]
    assert result.state == state
    assert (expected_gap in result.required_gaps) is bool(expected_gap)
    assert result.next_action == next_action
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


def test_prove_reissues_a_blocked_attestation_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, emitted = _arrange(monkeypatch, tmp_path)
    issued = []

    def issue(_repo, payload):
        issued.append(payload)
        return _attestation(str(payload["verdict"]))

    monkeypatch.setattr(proof_cli, "issue_proof_attestation", issue)
    monkeypatch.setattr(
        proof_cli,
        "persist_proof_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("collision")),
    )

    proof_cli.prove(_options(execute=True), root=tmp_path, json_output=True)

    result = emitted[-1]
    assert result.state == "gapped"
    assert result.required_gaps == ("proof_attestation_persistence_failed:collision",)
    assert [payload["verdict"] for payload in issued] == ["pass", "block"]


def test_prove_emits_the_issuance_gap_without_a_second_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, emitted = _arrange(monkeypatch, tmp_path)
    monkeypatch.setattr(
        proof_cli,
        "issue_proof_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("proof_binding_invalid")),
    )

    proof_cli.prove(_options(execute=True), root=tmp_path, json_output=True)

    assert len(emitted) == 1
    assert emitted[0].required_gaps == ("proof_binding_invalid",)


@pytest.mark.parametrize("invalid", [False, True])
def test_resolve_generation_uses_the_shared_active_carrier_selector(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, invalid: bool
) -> None:
    commitment = commitment_fixture(
        id="repository:proof-command", acceptance=("acceptance:fixture",)
    )
    binding = CurrentGenerationBinding({}, commitment, CurrentGenerationScope(("a.py",), {}))
    authority = object()
    monkeypatch.setattr(
        proof_cli,
        "workspace_status_observation",
        lambda *_args, **_kwargs: (
            {"head": "a" * 40, "branch": "dev", "role": "accepted"},
            authority,
        ),
    )
    monkeypatch.setattr(proof_cli, "change_scope_paths_from_status", lambda *_args: ("a.py",))
    monkeypatch.setattr(proof_cli, "repository_identity", lambda *_args, **_kwargs: commitment.id)

    def select(*_args, **kwargs):
        assert kwargs["authority"] is authority
        assert kwargs["status"]["changed_paths"] == ["a.py"]
        if invalid:
            message = "invalid"
            raise ValueError(message)
        return binding

    monkeypatch.setattr(proof_cli, "current_generation_binding", select)

    assert proof_cli.resolve_generation(tmp_path) == (None if invalid else binding)


@pytest.mark.parametrize("openspec", [False, True])
def test_prove_compiles_one_shared_repository_and_openspec_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, openspec: bool
) -> None:
    emitted = []
    scope = CurrentGenerationScope(("a.py",), {})
    commitment = commitment_fixture(id="change:proof-command", acceptance=("acceptance:fixture",))
    binding = CurrentGenerationBinding({}, commitment, scope)
    audit = {
        "verdict": "pass",
        "mode": "repository",
        "governance_context": {"contract": "governed_repository"},
        "required_gaps": [],
        "openspec": {"mode": "deep"},
    }
    lifecycle = {
        "verdict": "pass",
        "change": "proof-command",
        "schema_name": "spec-driven",
        "required_gaps": [],
        "summary": {"change_count": 1},
    }
    monkeypatch.setattr(proof_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(proof_cli, "_emit_host_gate_observation", lambda **_kwargs: False)
    monkeypatch.setattr(proof_cli.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(proof_cli.status_domain, "audit_for_root", lambda *_args, **_kwargs: audit)
    monkeypatch.setattr(proof_cli, "resolve_generation", lambda *_args, **_kwargs: binding)
    monkeypatch.setattr(proof_cli, "openspec_profile_enabled", lambda *_args, **_kwargs: openspec)
    monkeypatch.setattr(
        proof_cli,
        "openspec_governance_report",
        lambda *_args, **_kwargs: lifecycle,
    )

    def compile_plan(*_args, **kwargs):
        assert kwargs["generation_binding"] is binding
        assert "generation_scope" not in kwargs
        return _plan()

    monkeypatch.setattr(proof_cli, "proof_plan", compile_plan)
    monkeypatch.setattr(proof_cli, "run_plan_checks", lambda **_kwargs: ([_check()], True))
    monkeypatch.setattr(proof_cli, "emit", lambda result, **_kwargs: emitted.append(result))

    proof_cli.prove(_options(full=True), root=tmp_path, json_output=True)

    assert emitted[-1].data["changed_paths"] == ("a.py",)
    observed = emitted[-1].data["openspec_lifecycle"]
    assert observed.get("state") == (None if openspec else "not_applicable")
    assert observed.get("change") == ("proof-command" if openspec else None)

"""Reject stale landing effects and expose unsuccessful compensation."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.landing as landing
import ethos.adapters.mutation.proof_admission as proof_admission
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.governed_repository import prepared_work_lane
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path


def _pass_decision() -> SimpleNamespace:
    return SimpleNamespace(verdict="pass", required_gaps=())


def _candidate_plan(monkeypatch, root, current, previous):
    """Share the exact plan shape while each failure owns its effect boundary."""
    transition = (BranchRolePolicy(), {"head": current}, root, previous, object())
    monkeypatch.setattr(landing, "_candidate_plan", Mock(return_value=(None, transition)))


@pytest.mark.parametrize("case", ["same", "drift", "unreadable"])
def test_candidate_preview_checks_selected_runtime_policy_before_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """A source proof cannot turn predecessor policy drift into ready-to-land."""
    fixture = prepared_work_lane(tmp_path)
    head = commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(fixture.worktree, head, full=True)
    proof = proof_attestation(fixture.worktree, head)
    assert proof is not None
    plan = plan_from_statement(proof)
    assert plan.commitment is not None
    predecessor = (
        compile_plan(
            Commitment.model_validate(dict(plan.commitment)),
            Facts.model_validate(dict(plan.facts) | {"observed_at": datetime.now(UTC)}),
            plan.nodes,
            policy=dict(plan.policy) | {"predecessor_only": True},
            prior_attestations=dict(plan.prior_attestations),
        )
        if case == "drift"
        else plan
    )
    observed = {
        "command": "prove",
        "verdict": "block",
        "required_gaps": ["full_proof_requires_execute"],
        "data": {
            "expected_head": {"expected": head, "current": head, "matches": True},
            "transition_plan": predecessor.model_dump(mode="json"),
        },
    }
    if case == "unreadable":
        observed["required_gaps"] = ["gate_registry_invalid:system/gates.toml"]
        observed["data"] = {"expected_head": {"expected": head, "current": head, "matches": True}}
    monkeypatch.setattr(
        proof_admission,
        "current_runtime",
        lambda _common: SimpleNamespace(build=object(), python=tmp_path / "runtime-python"),
        raising=False,
    )
    monkeypatch.setattr(proof_admission, "invoking_build_identity", object, raising=False)
    command = Mock(
        return_value=SimpleNamespace(returncode=1, stdout=json.dumps(observed), stderr="")
    )
    monkeypatch.setattr(proof_admission, "run_command", command, raising=False)

    report = landing.candidate_transition_readiness(root=fixture.worktree)

    assert (
        report["required_gaps"]
        == {
            "same": [],
            "drift": ["proof_attestation_repository_policy_mismatch"],
            "unreadable": ["gate_registry_invalid:system/gates.toml"],
        }[case]
    )
    assert command.call_count == 1
    assert "--execute" not in command.call_args.args[1]
    assert git(fixture.candidate, "rev-parse", "HEAD") != head


@pytest.mark.parametrize(
    ("error", "gap"),
    [
        ("git_effect_permission_denied", "git_effect_permission_denied"),
        ("git_effect_lease_generation_stale", "git_effect_lease_generation_stale"),
        ("novel internal failure", "candidate_update_failed"),
    ],
)
def test_candidate_readiness_preserves_known_admission_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: str,
    gap: str,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    head = git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(
        landing,
        "_candidate_plan",
        Mock(side_effect=ValueError(error)),
    )

    report = landing.candidate_transition_readiness(root=repo)

    assert report["required_gaps"] == [gap]
    if gap == error:
        assert "stderr" not in report
    else:
        assert report["stderr"] == error
    assert report["head"] == head


@pytest.mark.parametrize(
    ("observed", "gap", "attempts"),
    [
        ("changed", "candidate_cas_stale", 1),
        ("expected", "candidate_cas_retry_exhausted", 2),
        ("rejected", "git_effect_cas_rejected", 1),
        ("unknown", "git_effect_cas_rejected", 1),
        ("retry-native", "git_effect_cas_rejected", 2),
    ],
)
def test_candidate_apply_never_overwrites_observed_ref_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observed: str,
    gap: str,
    attempts: int,
) -> None:
    native_failure = ProcessExecutionError(
        "git_effect_cas_rejected",
        reason="native_exit_nonzero",
        observation={"outcome": "unknown" if observed == "unknown" else "unchanged"},
    )
    execute = Mock(
        side_effect=native_failure
        if observed in {"rejected", "unknown"}
        else ValueError("git_effect_cas_rejected")
    )
    if observed == "retry-native":
        execute.side_effect = [ValueError("git_effect_cas_mismatch"), native_failure]
    monkeypatch.setattr(landing, "execute_candidate_plan", execute)
    monkeypatch.setattr(
        landing,
        "run_git",
        Mock(
            return_value=SimpleNamespace(
                stdout="expected" if observed == "retry-native" else observed
            )
        ),
    )

    current = "source"
    _candidate_plan(monkeypatch, tmp_path / "candidate", current, "expected")
    monkeypatch.setattr(landing, "evaluate_mutation", lambda **_kwargs: _pass_decision())
    monkeypatch.setattr(
        landing, "sync_worktree", lambda *_a, **_k: pytest.fail("no sync after failed CAS")
    )

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head=current)

    assert report["required_gaps"] == [gap]
    if observed in {"rejected", "unknown", "retry-native"}:
        assert report["process_failure"] == native_failure.evidence()
    else:
        assert report["candidate_head"] == observed
        assert report["cas_attempts"] == attempts
    assert execute.call_count == attempts
    assert report["verdict"] == ("unknown" if observed == "unknown" else "block")


def test_apply_land_reports_worktree_compensation_failure_without_hiding_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    current = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    attestation = Mock()
    _candidate_plan(monkeypatch, candidate, current, candidate_head)
    monkeypatch.setattr(
        landing,
        "_candidate_cas",
        Mock(return_value=(attestation, None, "", 1)),
    )
    monkeypatch.setattr(
        landing,
        "sync_worktree",
        Mock(side_effect=ValueError("projection failed")),
    )

    report = landing.apply_land_to_candidate(
        root=repo,
        authorized=True,
        expect_head=current,
        admitted_decision=_pass_decision(),
    )

    assert report["required_gaps"] == ["candidate_worktree_sync_failed"]
    assert report["stderr"] == "projection failed"
    assert report["attestation"] == attestation.model_dump(mode="json")

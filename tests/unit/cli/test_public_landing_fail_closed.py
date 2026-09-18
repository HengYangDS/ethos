from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.landing as landing
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


def _pass_decision() -> SimpleNamespace:
    return SimpleNamespace(verdict="pass", required_gaps=())


def _candidate_plan(monkeypatch, root, current, previous):
    """Share the exact plan shape while each failure owns its effect boundary."""
    transition = (BranchRolePolicy(), {"head": current}, root, previous, object())
    monkeypatch.setattr(landing, "_candidate_plan", Mock(return_value=(None, transition)))


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

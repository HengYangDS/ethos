from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.landing as landing
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


def _pass_decision() -> SimpleNamespace:
    return SimpleNamespace(verdict="pass", required_gaps=())


def _attestation() -> Attestation:
    return Attestation.issue(
        {
            "predicate": "effect:git-ref-transaction",
            "verifier": "agent:test:case:landing",
            "subject": "git:ref:candidate/dev",
            "issued_at": datetime(2026, 8, 10, tzinfo=UTC),
            "verdict": "pass",
            "statement": {},
            "effect_digest": "a" * 64,
        }
    )


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
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError(error)),
    )

    report = landing.candidate_transition_readiness(root=repo)

    assert report["required_gaps"] == [gap]
    if gap == error:
        assert "stderr" not in report
    else:
        assert report["stderr"] == error
    assert report["head"] == head


@pytest.mark.parametrize(
    ("observed", "second_error", "gap", "attempts"),
    [
        ("changed", "", "candidate_cas_stale", 1),
        ("expected", "git_effect_cas_rejected", "candidate_cas_retry_exhausted", 2),
    ],
)
def test_candidate_apply_never_overwrites_observed_ref_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observed: str,
    second_error: str,
    gap: str,
    attempts: int,
) -> None:
    calls = 0

    def execute(*_args: object, **_kwargs: object) -> Attestation:
        nonlocal calls
        calls += 1
        raise ValueError("git_effect_cas_rejected" if calls == 1 else second_error)

    monkeypatch.setattr(landing, "execute_candidate_plan", execute)
    monkeypatch.setattr(
        landing,
        "run_git",
        lambda *_a, **_k: type("Result", (), {"stdout": observed})(),
    )

    current = "source"
    candidate = tmp_path / "candidate"
    monkeypatch.setattr(
        landing,
        "_candidate_plan",
        lambda _root: (
            None,
            (BranchRolePolicy(), {"head": current}, candidate, "expected", object()),
        ),
    )
    monkeypatch.setattr(landing, "evaluate_mutation", lambda **_kwargs: _pass_decision())
    monkeypatch.setattr(
        landing, "sync_worktree", lambda *_a, **_k: pytest.fail("no sync after failed CAS")
    )

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head=current)

    assert report["required_gaps"] == [gap]
    assert report["candidate_head"] == observed
    assert report["cas_attempts"] == attempts
    assert calls == attempts


def test_apply_land_reports_worktree_compensation_failure_without_hiding_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    current = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    attestation = _attestation()
    monkeypatch.setattr(
        landing,
        "_candidate_plan",
        lambda _root: (
            None,
            (
                BranchRolePolicy(),
                {"head": current},
                candidate,
                candidate_head,
                object(),
            ),
        ),
    )
    monkeypatch.setattr(
        landing,
        "_candidate_cas",
        lambda **_kwargs: (attestation, None, "", 1),
    )
    monkeypatch.setattr(
        landing,
        "sync_worktree",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("projection failed")),
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

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.landing as landing
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.governed_repository import render_branch_policy

if TYPE_CHECKING:
    from pathlib import Path

HEAD = "a" * 40
CANDIDATE = "b" * 40


def _git(stdout: str = "head", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode)


def _candidate_transition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, object]:
    candidate = tmp_path / "candidate"
    candidate.mkdir(exist_ok=True)
    plan = object()
    base = {
        "verdict": "pass",
        "state": "candidate_base_current",
        "head": HEAD,
        "candidate_head": CANDIDATE,
        "path": candidate.as_posix(),
        "required_gaps": [],
    }
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(landing, "candidate_base_report", lambda **_kwargs: base)
    monkeypatch.setattr(
        landing,
        "proof_attestation",
        lambda *_args: SimpleNamespace(
            commitment_digest="digest",
            model_dump=lambda **_kwargs: {"id": "proof"},
        ),
    )
    monkeypatch.setattr(
        landing,
        "workspace_status",
        lambda *_args, **_kwargs: {"branch": "work/example"},
    )
    monkeypatch.setattr(landing, "leases_by_branch", lambda _root: {"work/example": {}})
    monkeypatch.setattr(
        landing,
        "load_lease_bound_commitment",
        lambda *_args, **_kwargs: SimpleNamespace(digest=lambda: "digest"),
    )
    monkeypatch.setattr(landing, "compile_observed_git_effect", lambda *_args, **_kwargs: plan)
    return candidate, plan


def test_apply_returns_candidate_plan_block_without_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked = {"verdict": "block", "state": "blocked", "required_gaps": ["proof_not_proven"]}
    monkeypatch.setattr(landing, "run_git", lambda *_args, **_kwargs: _git())
    monkeypatch.setattr(
        landing,
        "evaluate_mutation",
        lambda **_kwargs: SimpleNamespace(verdict="pass", required_gaps=()),
    )
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(landing, "candidate_base_report", lambda **_kwargs: blocked)

    assert (
        landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head="head")
        == blocked
    )


@pytest.mark.parametrize(
    ("failure", "expected_gap", "attempts"),
    [
        (TypeError("invalid plan"), "candidate_update_failed", 0),
        (ValueError("git_effect_cas_mismatch"), "candidate_cas_retry_exhausted", 2),
    ],
)
def test_apply_reports_candidate_effect_failure_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_gap: str,
    attempts: int,
) -> None:
    _candidate_transition(tmp_path, monkeypatch)
    monkeypatch.setattr(
        landing,
        "run_git",
        lambda _root, *args, **_kwargs: _git(
            CANDIDATE if args[:2] == ("rev-parse", "candidate/dev") else HEAD
        ),
    )
    monkeypatch.setattr(
        landing,
        "evaluate_mutation",
        lambda **_kwargs: SimpleNamespace(verdict="pass", required_gaps=()),
    )
    if attempts:
        calls = 0

        def execute(*_args: object, **_kwargs: object) -> object:
            nonlocal calls
            calls += 1
            raise failure

        monkeypatch.setattr(landing, "execute_candidate_plan", execute)
        monkeypatch.setattr(
            landing,
            "run_git",
            lambda _root, *args, **_kwargs: _git(
                CANDIDATE if args[:2] == ("rev-parse", "candidate/dev") else HEAD
            ),
        )
    else:
        monkeypatch.setattr(
            landing,
            "execute_candidate_plan",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(failure),
        )

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head=HEAD)

    assert report["required_gaps"] == [expected_gap]
    assert report["stderr"] == str(failure)
    if attempts:
        assert (report["candidate_head"], report["cas_attempts"]) == (CANDIDATE, attempts)


def test_candidate_cas_rethrows_non_cas_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = "permission denied"
    monkeypatch.setattr(
        landing,
        "execute_candidate_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError(message)),
    )

    _candidate_transition(tmp_path, monkeypatch)
    monkeypatch.setattr(landing, "run_git", lambda *_args, **_kwargs: _git(HEAD))
    monkeypatch.setattr(
        landing,
        "evaluate_mutation",
        lambda **_kwargs: SimpleNamespace(verdict="pass", required_gaps=()),
    )

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head="head")

    assert report["required_gaps"] == ["candidate_update_failed"]
    assert report["stderr"] == message


def test_candidate_transition_readiness_requires_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    base = {
        "verdict": "pass",
        "state": "candidate_base_current",
        "head": "a" * 40,
        "candidate_head": "b" * 40,
        "path": candidate.as_posix(),
        "required_gaps": [],
    }
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(landing, "run_git", lambda *_args, **_kwargs: _git("a" * 40))
    monkeypatch.setattr(landing, "candidate_base_report", lambda **_kwargs: base)
    monkeypatch.setattr(landing, "proof_attestation", lambda *_args: None)
    monkeypatch.setattr(
        landing,
        "proof_gaps",
        lambda *_args: ["proof_not_proven"],
    )

    report = landing.candidate_transition_readiness(root=tmp_path)

    assert report["required_gaps"] == ["proof_not_proven"]


def test_candidate_to_accepted_stops_at_decision_and_reobservation_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked_decision = SimpleNamespace(verdict="block", required_gaps=("authorization_required",))
    monkeypatch.setattr(landing, "run_git", lambda *_args, **_kwargs: _git("head"))
    monkeypatch.setattr(
        landing,
        "committed_file_text",
        lambda *_args: render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ),
    )
    monkeypatch.setattr(landing, "evaluate_closeout_mutation", lambda **_kwargs: blocked_decision)
    monkeypatch.setattr(landing, "accepted", SimpleNamespace(accepted_payload=lambda *_args: {}))

    report = landing.apply_candidate_to_accepted(
        root=tmp_path, authorized=False, expect_head="head", candidate_head="candidate"
    )
    assert report["required_gaps"] == ["authorization_required"]

    monkeypatch.setattr(
        landing,
        "evaluate_closeout_mutation",
        lambda **_kwargs: SimpleNamespace(verdict="pass", required_gaps=()),
    )
    monkeypatch.setattr(
        landing,
        "workspace_status",
        lambda *_args, **_kwargs: {"candidate": {"head": "changed"}},
    )
    report = landing.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="head", candidate_head="candidate"
    )
    assert report["required_gaps"] == ["candidate_head_changed_after_control_replacement_check"]


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [(1, ""), (0, ".ethos/workspace.toml\n")],
)
def test_default_accepted_policy_rejects_unreadable_or_changed_carrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
) -> None:
    monkeypatch.setattr(
        landing,
        "run_git",
        lambda *_args, **_kwargs: _git(stdout, returncode),
    )

    report = landing.apply_candidate_to_accepted(
        root=tmp_path,
        authorized=True,
        expect_head="head",
    )

    assert report["required_gaps"] == ["accepted_policy_unavailable"]

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.landing as landing
from ethos.contracts.branch.roles import BranchRolePolicy


def _git(stdout: str = "head", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode)


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
    monkeypatch.setattr(landing, "_candidate_plan", lambda *_args, **_kwargs: (blocked, None))

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
    policy = BranchRolePolicy()
    transition = (policy, {"head": "head"}, tmp_path / "candidate", "candidate", object())
    monkeypatch.setattr(landing, "run_git", lambda *_args, **_kwargs: _git("head"))
    monkeypatch.setattr(
        landing,
        "evaluate_mutation",
        lambda **_kwargs: SimpleNamespace(verdict="pass", required_gaps=()),
    )
    monkeypatch.setattr(landing, "_candidate_plan", lambda *_args, **_kwargs: (None, transition))
    if attempts:
        monkeypatch.setattr(
            landing,
            "_candidate_cas",
            lambda **_kwargs: (None, (expected_gap, str(failure)), "observed", attempts),
        )
    else:
        monkeypatch.setattr(
            landing,
            "_candidate_cas",
            lambda **_kwargs: (_ for _ in ()).throw(failure),
        )

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head="head")

    assert report["required_gaps"] == [expected_gap]
    assert report["stderr"] == str(failure)
    if attempts:
        assert (report["candidate_head"], report["cas_attempts"]) == ("observed", attempts)


def test_candidate_cas_rethrows_non_cas_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = "permission denied"
    monkeypatch.setattr(
        landing,
        "execute_candidate_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError(message)),
    )

    with pytest.raises(ValueError, match=message):
        landing._candidate_cas(  # noqa: SLF001
            root=tmp_path,
            policy=BranchRolePolicy(),
            plan=object(),  # type: ignore[arg-type]
            candidate_head="candidate",
        )


def test_candidate_transition_plan_requires_proof() -> None:
    with pytest.raises(ValueError, match="candidate_prior_proof_missing"):
        landing._candidate_transition_plan(  # noqa: SLF001
            root=Path("/repo"),
            authority=object(),  # type: ignore[arg-type]
            effect=object(),  # type: ignore[arg-type]
            head="a" * 40,
            lease={},
            prior_attestations={},
            policy=BranchRolePolicy(),
        )


def test_candidate_to_accepted_stops_at_decision_and_reobservation_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked_decision = SimpleNamespace(verdict="block", required_gaps=("authorization_required",))
    monkeypatch.setattr(landing, "run_git", lambda *_args, **_kwargs: _git("head"))
    monkeypatch.setattr(landing, "committed_file_text", lambda *_args: "")
    monkeypatch.setattr(
        landing,
        "_default_accepted_transition_policy",
        lambda *_args: BranchRolePolicy(),
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

    with pytest.raises(ValueError, match="accepted transition policy is unreadable"):
        landing._default_accepted_transition_policy(tmp_path, "head")  # noqa: SLF001

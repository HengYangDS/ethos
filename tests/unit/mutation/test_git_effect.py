from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from ethos.adapters.repo.git import execute_git_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo


def _effect(*, old: str, new: str) -> GitEffect:
    return GitEffect(
        id="effect:advance-dev",
        plan_digest="a" * 64,
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
    )


def test_git_effect_applies_exact_cas_and_replays_matching_attestation(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    git(repo, "add", "NEXT.md")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)

    applied = execute_git_effect(
        repo,
        effect,
        issuer="agent:test:case:one",
        permissions=("git.ref.compare-and-swap",),
    )
    replayed = execute_git_effect(
        repo,
        effect,
        issuer="agent:test:case:one",
        attestations=(applied,),
        permissions=("git.ref.compare-and-swap",),
    )

    assert git(repo, "rev-parse", "dev") == new
    assert applied.kind == "git-effect"
    assert applied.subject == effect.plan_digest
    assert applied.content["state"] == "applied"
    assert replayed is applied


def test_git_effect_recovers_attestation_when_desired_state_already_holds(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    git(repo, "update-ref", "refs/heads/dev", new, old)

    recovered = execute_git_effect(
        repo,
        _effect(old=old, new=new),
        issuer="agent:test:case:one",
        permissions=("git.ref.compare-and-swap",),
    )

    assert recovered.content["state"] == "recovered"


def test_git_effect_blocks_identity_collision_and_stale_cas(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    collision = Attestation(
        id=effect.id,
        kind="git-effect",
        issuer="agent:test:case:one",
        subject=effect.plan_digest,
        issued_at=datetime(2026, 7, 25, tzinfo=UTC),
        content={"effect_digest": "b" * 64, "state": "applied"},
    )

    with pytest.raises(ValueError, match="git_effect_identity_collision"):
        execute_git_effect(
            repo,
            effect,
            issuer="agent:test:case:one",
            attestations=(collision,),
            permissions=("git.ref.compare-and-swap",),
        )

    git(repo, "update-ref", "refs/heads/dev", new, old)
    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        execute_git_effect(
            repo,
            _effect(old="0" * 40, new=old),
            issuer="agent:test:case:one",
            permissions=("git.ref.compare-and-swap",),
        )


def test_git_effect_requires_explicit_permission_admission(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        execute_git_effect(
            repo,
            _effect(old=old, new=new),
            issuer="agent:test:case:one",
            permissions=(),
        )


def test_git_effect_blocks_assertion_drift_before_recovery(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    git(repo, "branch", "candidate/dev", old)
    effect = _effect(old=old, new=new).model_copy(
        update={"assertions": {"refs/heads/candidate/dev": old}}
    )
    git(repo, "update-ref", "refs/heads/candidate/dev", new, old)

    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        execute_git_effect(
            repo,
            effect,
            issuer="agent:test:case:one",
            permissions=("git.ref.compare-and-swap",),
        )


def test_git_effect_revalidates_state_before_replaying_attestation(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = execute_git_effect(
        repo,
        effect,
        issuer="agent:test:case:one",
        permissions=("git.ref.compare-and-swap",),
    )
    git(repo, "update-ref", "refs/heads/dev", old, new)

    with pytest.raises(ValueError, match="git_effect_postcondition_failed"):
        execute_git_effect(
            repo,
            effect,
            issuer="agent:test:case:one",
            attestations=(applied,),
            permissions=("git.ref.compare-and-swap",),
        )


@pytest.mark.parametrize(
    ("updates", "assertions"),
    [
        (
            {"refs/heads/dev": GitRefUpdate(expected="0" * 40, desired="1" * 40)},
            {"refs/heads/dev": "0" * 40},
        ),
        (
            {"refs/heads/dev": GitRefUpdate(expected="0" * 40, desired="1" * 40)},
            {"refs/heads/candidate/dev": "invalid"},
        ),
    ],
)
def test_git_effect_rejects_invalid_assertions(
    updates: dict[str, GitRefUpdate],
    assertions: dict[str, str],
) -> None:
    with pytest.raises(ValidationError, match="git_effect_permissions_invalid"):
        GitEffect(
            id="effect:invalid",
            plan_digest="a" * 64,
            updates=updates,
            assertions=assertions,
        )


def test_git_effect_rejects_noncanonical_ref_name() -> None:
    with pytest.raises(ValidationError, match="git_effect_permissions_invalid"):
        GitEffect(
            id="effect:invalid-ref",
            plan_digest="a" * 64,
            updates={
                "refs/heads/dev\nupdate refs/heads/main": GitRefUpdate(
                    expected="0" * 40,
                    desired="1" * 40,
                )
            },
        )

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.adapters.repo.git import GitEffectExecutionRequest
from ethos.adapters.repo.git import execute_git_effect
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_CHANGE_CONTRACT_DIGEST = "c" * 64
_REPOSITORY_FACTS_DIGEST = "f" * 64
_POLICY_DIGEST = "d" * 64


def _effect(*, old: str, new: str) -> GitEffect:
    return GitEffect(
        id="effect:advance-dev",
        plan_digest="a" * 64,
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
    )


def _execute(
    repo: Path,
    effect: GitEffect,
    *,
    attestations: tuple[Attestation, ...] = (),
    permissions: tuple[str, ...] = ("git.ref.compare-and-swap",),
    change_contract_digest: str = _CHANGE_CONTRACT_DIGEST,
    repository_facts_digest: str = _REPOSITORY_FACTS_DIGEST,
    policy_digest: str = _POLICY_DIGEST,
) -> Attestation:
    return execute_git_effect(
        repo,
        effect,
        GitEffectExecutionRequest(
            issuer="agent:test:case:one",
            attestations=attestations,
            permissions=permissions,
            change_contract_digest=change_contract_digest,
            repository_facts_digest=repository_facts_digest,
            policy_digest=policy_digest,
        ),
    )


def test_git_effect_applies_exact_cas_and_replays_matching_attestation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    git(repo, "add", "NEXT.md")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)

    applied = _execute(repo, effect)
    replayed = _execute(repo, effect, attestations=(applied,))

    assert git(repo, "rev-parse", "dev") == new
    assert applied.kind == "effect"
    assert applied.subject == effect.id
    assert applied.verdict == "pass"
    assert applied.plan_digest == effect.plan_digest
    assert applied.effect_digest == effect.digest()
    assert applied.change_contract_digest == _CHANGE_CONTRACT_DIGEST
    assert applied.repository_facts_digest == _REPOSITORY_FACTS_DIGEST
    assert applied.policy_digest == _POLICY_DIGEST
    assert len(applied.id) == 64
    assert applied.content["state"] == "applied"
    assert replayed is applied


def test_git_effect_recovers_attestation_when_desired_state_already_holds(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    git(repo, "update-ref", "refs/heads/dev", new, old)

    recovered = _execute(repo, _effect(old=old, new=new))

    assert recovered.content["state"] == "recovered"


def test_git_effect_blocks_identity_collision_and_stale_cas(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    collision = Attestation.issue(
        {
            "kind": "effect",
            "issuer": "agent:test:case:one",
            "subject": effect.id,
            "issued_at": datetime(2026, 7, 25, tzinfo=UTC),
            "verdict": "pass",
            "content": {"state": "applied", "updates": effect.model_dump(mode="json")["updates"]},
            "change_contract_digest": _CHANGE_CONTRACT_DIGEST,
            "repository_facts_digest": _REPOSITORY_FACTS_DIGEST,
            "plan_digest": effect.plan_digest,
            "policy_digest": _POLICY_DIGEST,
            "effect_digest": "b" * 64,
        }
    )

    with pytest.raises(ValueError, match="git_effect_identity_collision"):
        _execute(repo, effect, attestations=(collision,))

    git(repo, "update-ref", "refs/heads/dev", new, old)
    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        _execute(repo, _effect(old="0" * 40, new=old))


def test_git_effect_requires_explicit_permission_admission(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        _execute(repo, _effect(old=old, new=new), permissions=())


def test_git_effect_blocks_assertion_drift_before_recovery(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    git(repo, "branch", "candidate/dev", old)
    effect = _effect(old=old, new=new).model_copy(
        update={"assertions": {"refs/heads/candidate/dev": old}}
    )
    git(repo, "update-ref", "refs/heads/candidate/dev", new, old)

    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        _execute(repo, effect)


def test_git_effect_revalidates_state_before_replaying_attestation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
    git(repo, "update-ref", "refs/heads/dev", old, new)

    with pytest.raises(ValueError, match="git_effect_postcondition_failed"):
        _execute(repo, effect, attestations=(applied,))


@pytest.mark.parametrize(
    ("field", "error"),
    [
        ("change_contract_digest", "git_effect_binding_missing:change_contract_digest"),
        ("repository_facts_digest", "git_effect_binding_missing:repository_facts_digest"),
        ("policy_digest", "git_effect_binding_missing:policy_digest"),
    ],
)
def test_git_effect_blocks_before_mutation_when_required_binding_is_missing(
    tmp_path: Path, field: str, error: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    with pytest.raises(ValueError, match=error):
        _execute(
            repo,
            effect,
            change_contract_digest=(
                "" if field == "change_contract_digest" else _CHANGE_CONTRACT_DIGEST
            ),
            repository_facts_digest=(
                "" if field == "repository_facts_digest" else _REPOSITORY_FACTS_DIGEST
            ),
            policy_digest="" if field == "policy_digest" else _POLICY_DIGEST,
        )
    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") == old


def test_git_effect_replay_blocks_stale_binding_unknown_verdict_and_duplicate(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)

    with pytest.raises(
        ValueError,
        match="git_effect_attestation_binding_mismatch:repository_facts_digest",
    ):
        _execute(
            repo,
            effect,
            attestations=(applied,),
            repository_facts_digest="e" * 64,
        )

    unknown = Attestation.issue(
        {
            "kind": "effect",
            "issuer": applied.issuer,
            "subject": effect.id,
            "issued_at": applied.issued_at,
            "verdict": "unknown",
            "content": applied.content,
            "change_contract_digest": applied.change_contract_digest,
            "repository_facts_digest": applied.repository_facts_digest,
            "plan_digest": applied.plan_digest,
            "policy_digest": applied.policy_digest,
            "effect_digest": applied.effect_digest,
        }
    )
    with pytest.raises(ValueError, match="git_effect_attestation_verdict_unknown"):
        _execute(repo, effect, attestations=(unknown,))

    with pytest.raises(ValueError, match="git_effect_attestation_duplicate"):
        _execute(repo, effect, attestations=(applied, applied))


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

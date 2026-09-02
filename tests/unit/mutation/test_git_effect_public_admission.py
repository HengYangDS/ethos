from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effect_admission as admission
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


ZERO = "0" * 40
ACTOR = "agent:test:case:owner"


def test_observed_effect_compiler_promotes_semantic_policy_to_exact_cas_authority(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root)
    git(root, "add", ".ethos/profile.toml")
    git(root, "commit", "-m", "declare repository identity")
    head = git(root, "rev-parse", "HEAD")
    effect = GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=head, desired=head)})
    authority = commitment_fixture(id=f"repository:{root.name}", acceptance=("acceptance:fixture",))

    carried = compile_observed_git_effect(
        root,
        authority,
        effect,
        head=head,
        policy={"operation": "lane.refresh", "execution_branch": "work/example"},
    )

    assert carried.policy == {
        "operation": "git.ref.compare-and-swap",
        "transition": "lane.refresh",
        "effect_digest": effect.digest(),
        "execution_branch": "work/example",
    }
    admission.require_effect_permission(effect, carried)


def _plan(
    root: Path,
    effect: GitEffect,
    *,
    values: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
) -> TransitionPlan:
    facts = Facts(
        repository=f"repository:{root.name}",
        head=git(root, "rev-parse", "HEAD"),
        tree=git(root, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={
            "refs": {ref: update.expected for ref, update in effect.updates.items()},
            "assertions": effect.assertions,
            **(values or {}),
        },
    )
    authority = commitment_fixture(
        id="authority:test:git-effect", acceptance=("acceptance:fixture",)
    )
    return compile_git_effect_plan(
        authority,
        facts,
        prior_attestations={},
        policy=policy or {"operation": "test.apply"},
        effect=effect,
    )


def _generation(branch: str, *, generation: int = 4) -> dict[str, object]:
    return {
        "lane_ref": branch,
        "generation": generation,
        "holder_ref": ACTOR,
        "expires_at": "2030-01-01T00:00:00+00:00",
    }


def test_lease_generation_uses_the_canonical_four_field_vocabulary() -> None:
    observed = _generation("work/example") | {"lease_state": "valid"}

    assert admission.lease_generation(observed) == _generation("work/example")


def test_raw_semantic_operation_never_authorizes_an_effect(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    old = git(root, "rev-parse", "HEAD")
    new = git(root, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "target")
    branch = "work/example"
    generation = _generation(branch)
    effect = GitEffect(updates={f"refs/heads/{branch}": GitRefUpdate(expected=old, desired=new)})
    carried = _plan(
        root,
        effect,
        values={"lease_generation": generation},
        policy={"operation": "openspec.change.start"},
    )

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        admission.require_effect_permission(effect, carried)


def test_recovery_accepts_the_same_minimal_lease_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    old = git(root, "rev-parse", "HEAD")
    new = git(root, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "target")
    branch = "work/example"
    current = _generation(branch) | {
        "lane_ref": branch,
        "lease_state": "valid",
    }
    generation = admission.lease_generation(current)
    effect = GitEffect(updates={f"refs/heads/{branch}": GitRefUpdate(expected=old, desired=new)})
    carried = _plan(
        root,
        effect,
        values={"lease_generation": generation},
        policy={"operation": "openspec.change.start", "execution_branch": branch},
    )
    monkeypatch.setenv("ETHOS_ACTOR", ACTOR)
    monkeypatch.setattr(admission, "leases_by_branch", lambda *_args, **_kwargs: {branch: current})
    monkeypatch.setattr(
        admission,
        "run_git",
        lambda *_args, **_kwargs: type("Result", (), {"stdout": f"{branch}\n"})(),
    )

    admission.require_lease_generation(root, carried)


@pytest.mark.parametrize("drift", ["refs", "assertions", "head", "tree"])
def test_plan_prestate_rejects_each_observed_authority_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    head = git(root, "rev-parse", "HEAD")
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=head, desired=head)},
        assertions={"refs/heads/source": head},
    )
    carried = _plan(root, effect)
    monkeypatch.setattr(admission, "require_lease_generation", lambda *_args, **_kwargs: None)
    if drift == "refs":
        effect = GitEffect(
            updates={"refs/heads/dev": GitRefUpdate(expected=ZERO, desired=head)},
            assertions=effect.assertions,
        )
    elif drift == "assertions":
        effect = GitEffect(updates=effect.updates, assertions={})
    elif drift == "head":
        monkeypatch.setattr(admission, "current_tracked_head", lambda _root: ZERO)
    else:
        monkeypatch.setattr(admission, "current_tree", lambda *_args: "0" * 40)

    expected = (
        "git_effect_plan_prestate_mismatch"
        if drift in {"refs", "assertions"}
        else "git_effect_plan_prestate_stale"
    )
    with pytest.raises(ValueError, match=expected):
        admission.require_plan_prestate(root, carried, effect)


@pytest.mark.parametrize(
    ("operation", "attached", "detached", "error"),
    [
        ("lane.start", "work/existing", "", "git_effect_lease_branch_mismatch"),
        ("lane.refresh", "work/other", "", "git_effect_lease_branch_mismatch"),
        ("lane.refresh", "", "work/example", ""),
    ],
)
def test_lease_generation_binds_actor_branch_and_detached_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    attached: str,
    detached: str,
    error: str,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    head = git(root, "rev-parse", "HEAD")
    branch = "work/example"
    generation = _generation(branch)
    observed = generation | {
        "lane_ref": branch,
        "lease_state": "valid",
    }
    effect = GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=head, desired=head)})
    carried = _plan(
        root,
        effect,
        values={"lease_generation": generation},
        policy={"operation": operation, "holder_ref": ACTOR, "execution_branch": branch},
    )
    monkeypatch.setenv("ETHOS_ACTOR", ACTOR)
    monkeypatch.setattr(admission, "leases_by_branch", lambda *_args, **_kwargs: {branch: observed})
    monkeypatch.setattr(admission, "lease_generation", lambda _lease: generation)
    monkeypatch.setattr(
        admission,
        "run_git",
        lambda *_args, **_kwargs: type("Result", (), {"stdout": attached + "\n"})(),
    )
    if error:
        with pytest.raises(ValueError, match=error):
            admission.require_lease_generation(root, carried, detached_branch=detached)
    else:
        admission.require_lease_generation(root, carried, detached_branch=detached)


def test_lease_generation_rejects_wrong_actor_before_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init_git_repo(tmp_path / "repo")
    head = git(root, "rev-parse", "HEAD")
    branch = "work/example"
    generation = _generation(branch)
    observed = generation | {
        "lane_ref": branch,
        "lease_state": "valid",
    }
    effect = GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=head, desired=head)})
    carried = _plan(root, effect, values={"lease_generation": generation})
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    monkeypatch.setattr(admission, "leases_by_branch", lambda *_args, **_kwargs: {branch: observed})
    monkeypatch.setattr(admission, "lease_generation", lambda _lease: generation)

    with pytest.raises(ValueError, match="lease_actor_mismatch"):
        admission.require_lease_generation(root, carried)


@pytest.mark.parametrize(
    "policy",
    [
        {"operation": "lane.refresh", "execution_branch": "work/example"},
        {
            "operation": "lane.retire",
            "retirement_kind": "linked-lane",
            "retirement_mode": "superseded",
            "execution_branch": "work/example",
        },
        {
            "operation": "lane.retire",
            "retirement_kind": "absorbed-ref",
            "retirement_mode": "landed",
            "execution_branch": "work/example",
        },
    ],
)
def test_expired_lease_generation_is_exclusive_to_linked_landed_retirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: dict[str, object],
) -> None:
    root = init_git_repo(tmp_path / "repo")
    head = git(root, "rev-parse", "HEAD")
    branch = "work/example"
    generation = _generation(branch)
    observed = generation | {"lease_state": "expired"}
    effect = GitEffect(updates={f"refs/heads/{branch}": GitRefUpdate(expected=head, desired=ZERO)})
    carried = _plan(
        root,
        effect,
        values={
            "lease_generation": generation,
            "lease_generation_state": "expired",
        },
        policy={**policy, "actor": ACTOR},
    )
    monkeypatch.setattr(admission, "leases_by_branch", lambda *_args, **_kwargs: {branch: observed})
    monkeypatch.setattr(admission, "lease_generation", lambda _lease: generation)

    with pytest.raises(ValueError, match="git_effect_expired_lease_not_admitted"):
        admission.require_lease_generation(root, carried)

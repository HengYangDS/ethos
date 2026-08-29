from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.repo.git_effect_attestation as attest
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

ISSUER = "agent:test:attestation"


def _case(tmp_path: Path) -> tuple[Path, GitEffect, Any, dict[str, object], dict[str, object]]:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)}, assertions={}
    )
    observed = datetime.now(UTC) - timedelta(seconds=2)
    facts = Facts(
        repository="repository:repo",
        head=old,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=observed,
        values={"refs": {"refs/heads/dev": old}, "assertions": {}},
    )
    plan = compile_git_effect_plan(
        commitment_fixture(id="authority:test:attestation", acceptance=("acceptance:fixture",)),
        facts,
        prior_attestations={},
        policy={"operation": "git.ref.compare-and-swap", "effect_digest": effect.digest()},
        effect=effect,
    )
    return (
        repo,
        effect,
        plan,
        {
            "head": old,
            "tree": facts.tree,
            "refs": {"refs/heads/dev": old},
            "assertions": {},
            "observed_at": observed.isoformat(),
        },
        {
            "head": new,
            "tree": facts.tree,
            "refs": {"refs/heads/dev": new},
            "observed_at": (observed + timedelta(seconds=1)).isoformat(),
        },
    )


def _record(effect: GitEffect, plan: Any, before: dict[str, object], after: dict[str, object]):
    return attest.issue(
        effect,
        plan=plan,
        issuer=ISSUER,
        evidence=("repository:repo", "applied", before, after),
    )


def _reissue(value: Attestation, **updates: object) -> Attestation:
    payload = value.model_dump(mode="python", exclude={"id", *updates})
    payload.update(updates)
    return Attestation.issue(payload)


def test_git_effect_attestation_binds_exact_plan_effect_and_observations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    record = attest.issue(
        effect,
        plan=plan,
        issuer=ISSUER,
        evidence=("repository:repo", "applied", before, after),
    )
    update = effect.updates["refs/heads/dev"]
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    monkeypatch.setattr(
        attest, "resolve_git_effect_repository", lambda *_args, **_kwargs: "repository:repo"
    )

    attest.validate(repo, effect, record, issuer=ISSUER, plan=plan)

    assert attest.plan_from_attestation(record) == plan
    assert record.subject == f"git-effect:{effect.digest()}"
    assert record.plan_digest == plan.digest
    assert record.effect_digest == effect.digest()
    assert record.payload.body["input"] == {
        name: before[name] for name in ("head", "tree", "refs", "assertions")
    }
    assert record.payload.body["output"] == {name: after[name] for name in ("head", "tree", "refs")}
    assert record.mints_authority is False


def test_git_effect_recovery_requires_the_exact_attestation_set_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    record = attest.issue(
        effect,
        plan=plan,
        issuer=ISSUER,
        evidence=("repository:repo", "applied", before, after),
    )
    update = effect.updates["refs/heads/dev"]
    assert (
        attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=update.desired)
        is None
    )

    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    record_attestations(repo, (record,))
    monkeypatch.setattr(
        attest, "resolve_git_effect_repository", lambda *_args, **_kwargs: "repository:repo"
    )
    monkeypatch.setattr(attest, "_matches", lambda *_args, **_kwargs: True)
    assert (
        attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=update.desired)
        == plan
    )


def test_git_effect_attestation_fails_closed_on_invalid_time_plan_and_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, effect, plan, before, after = _case(tmp_path)
    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        attest.issue(
            effect,
            plan=plan,
            issuer=ISSUER,
            evidence=(
                "repository:repo",
                "applied",
                before,
                after | {"observed_at": "invalid"},
            ),
        )
    record = _record(effect, plan, before, after)
    invalid_plan = _reissue(
        record,
        payload={"kind": record.payload.kind, "body": {**record.payload.body, "plan": {}}},
    )
    with pytest.raises(ValueError, match="git_effect_attestation_plan_invalid"):
        attest.plan_from_attestation(invalid_plan)
    monkeypatch.setattr(attest, "mutable_json", lambda _value: ())
    with pytest.raises(TypeError, match="git_effect_attestation_statement_invalid"):
        attest.plan_from_attestation(record)


def test_validated_plan_selection_rejects_store_collision_and_wrong_issuer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    with pytest.raises(ValueError, match="git_effect_attestation_collision"):
        attest.validated_plan_attestation(
            repo,
            plan.digest,
            issuer=ISSUER,
            attestations=(record, record),
        )
    assert (
        attest.validated_plan_attestation(
            repo,
            plan.digest,
            issuer=ISSUER,
            attestations=(),
        )
        is None
    )
    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        attest.validated_plan_attestation(
            repo,
            plan.digest,
            issuer="agent:test:other",
            attestations=(record,),
        )
    monkeypatch.setattr(
        attest,
        "read_attestation_set",
        lambda _root: (_ for _ in ()).throw(ValueError("corrupt")),
    )
    with pytest.raises(ValueError, match="git_effect_attestation_invalid"):
        attest.validated_plan_attestation(repo, plan.digest, issuer=ISSUER)


def test_accepted_closeout_selects_one_exact_candidate_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _effect, plan, before, after = _case(tmp_path)
    accepted_ref, candidate_ref = "refs/heads/dev", "refs/heads/candidate/dev"
    candidate_head = "f" * 40
    effect = GitEffect(
        updates={accepted_ref: GitRefUpdate(expected="a" * 40, desired=candidate_head)},
        assertions={candidate_ref: candidate_head},
    )
    record = _record(effect, plan, before, after)
    selected_plan = plan.model_copy(update={"policy": {"transition": "candidate.accept"}})
    monkeypatch.setattr(attest, "plan_from_attestation", lambda _item: selected_plan)
    monkeypatch.setattr(attest, "git_effect_from_plan", lambda _plan: effect)
    monkeypatch.setattr(attest, "validate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(attest, "read_attestation_set", lambda _root: ("repository", (record,)))

    assert attest.accepted_closeout_attestation(
        repo,
        accepted_ref=accepted_ref,
        candidate_ref=candidate_ref,
        candidate_head=candidate_head,
    ) == (selected_plan, record)

    monkeypatch.setattr(
        attest,
        "read_attestation_set",
        lambda _root: ("repository", (record, record)),
    )
    with pytest.raises(ValueError, match="accepted_closeout_effect_ambiguous"):
        attest.accepted_closeout_attestation(
            repo,
            accepted_ref=accepted_ref,
            candidate_ref=candidate_ref,
            candidate_head=candidate_head,
        )


def test_recovery_selection_rejects_invalid_store_and_ambiguous_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    desired = next(iter(effect.updates.values())).desired
    monkeypatch.setattr(attest, "plan_from_attestation", lambda _item: plan)
    monkeypatch.setattr(attest, "validate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        attest,
        "read_attestation_set",
        lambda _root: ("repository", (_reissue(record, predicate="proof:other"), record)),
    )
    assert attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=desired) == plan

    monkeypatch.setattr(
        attest,
        "read_attestation_set",
        lambda _root: ("repository", (record, record)),
    )
    with pytest.raises(ValueError, match="git_effect_recovery_ambiguous"):
        attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=desired)

    monkeypatch.setattr(
        attest,
        "read_attestation_set",
        lambda _root: (_ for _ in ()).throw(ValueError("corrupt")),
    )
    with pytest.raises(ValueError, match="git_effect_recovery_unproven"):
        attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=desired)


def test_attestation_record_store_is_idempotent_and_rejects_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    monkeypatch.setattr(attest, "validate", lambda *_args, **_kwargs: None)
    observations = iter(((), (record,), (record,)))
    monkeypatch.setattr(attest, "_matching_plan_attestations", lambda *_a, **_k: next(observations))
    persisted: list[Attestation] = []
    monkeypatch.setattr(
        attest, "record_attestations", lambda _root, values: persisted.extend(values)
    )

    assert attest.records(repo, plan, record) == (record,)
    assert persisted == [record]

    other = _reissue(record, verifier="agent:test:other")
    monkeypatch.setattr(attest, "_matching_plan_attestations", lambda *_a, **_k: (other,))
    with pytest.raises(ValueError, match="git_effect_attestation_collision"):
        attest.records(repo, plan, record)

    monkeypatch.setattr(attest, "_matching_plan_attestations", lambda *_a, **_k: ())
    monkeypatch.setattr(
        attest,
        "record_attestations",
        lambda *_a, **_k: (_ for _ in ()).throw(
            ValueError("attestation_set_identity_collision:test")
        ),
    )
    with pytest.raises(ValueError, match="git_effect_attestation_collision"):
        attest.records(repo, plan, record)

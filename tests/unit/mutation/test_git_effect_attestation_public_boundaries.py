from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effect_attestation as attest
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

ISSUER = "agent:test:attestation"


def _case(tmp_path: Path, *, transition="git.ref.compare-and-swap"):
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    git(repo, "add", ".ethos/profile.toml")
    git(repo, "commit", "-m", "declare repository identity")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    assertions = {"refs/heads/candidate/dev": new} if transition == "candidate.accept" else {}
    for ref, head in assertions.items():
        git(repo, "update-ref", ref, head)
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)}, assertions=assertions
    )
    observed = datetime.now(UTC) - timedelta(seconds=2)
    facts = Facts(
        repository="repository:repo",
        head=old,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=observed,
        values={"refs": {"refs/heads/dev": old}, "assertions": assertions},
    )
    plan = compile_git_effect_plan(
        commitment_fixture(id="authority:test:attestation", acceptance=("acceptance:fixture",)),
        facts,
        prior_attestations={},
        policy={"operation": "git.ref.compare-and-swap", "transition": transition},
        effect=effect,
    )
    before = {
        "head": old,
        "tree": facts.tree,
        "refs": {"refs/heads/dev": old},
        "assertions": assertions,
        "observed_at": observed.isoformat(),
    }
    after = {
        "head": new,
        "tree": facts.tree,
        "refs": {"refs/heads/dev": new},
        "observed_at": (observed + timedelta(seconds=1)).isoformat(),
    }
    return repo, effect, plan, before, after


def _record(
    effect: GitEffect, plan: TransitionPlan, before: dict[str, object], after: dict[str, object]
):
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


def test_git_effect_attestation_binds_exact_plan_effect_and_observations(tmp_path: Path) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    update = effect.updates["refs/heads/dev"]
    assert (
        attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=update.desired)
        is None
    )
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)

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
    record_attestations(repo, (record,))
    assert (
        attest.recover_plan(repo, operation="git.ref.compare-and-swap", desired=update.desired)
        == plan
    )


@pytest.mark.parametrize(
    "mode",
    [
        "issue_time",
        "effect",
        "missing_time",
        "invalid_time",
        "chronology",
        "postobserve",
    ],
)
def test_git_effect_attestation_rejects_invalid_observation(tmp_path, monkeypatch, mode):
    repo, effect, plan, before, after = _case(tmp_path)
    if mode == "issue_time":
        with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
            _record(effect, plan, before, after | {"observed_at": "invalid"})
        return
    if mode == "chronology":
        before, after = (
            before | {"observed_at": after["observed_at"]},
            after | {"observed_at": before["observed_at"]},
        )
    record = _record(effect, plan, before, after)
    if mode in {"missing_time", "invalid_time"}:
        body = dict(record.payload.body)
        body["observed_at"] = {} if mode == "missing_time" else {"after": "invalid"}
        record = _reissue(record, payload={"kind": record.payload.kind, "body": body})
    elif mode == "effect":
        effect = effect.model_copy(update={"assertions": {"refs/heads/other": before["head"]}})
    elif mode == "postobserve":
        original, calls = attest.resolve_git_effect_repository, []

        def observe(*args, **kwargs):
            calls.append(args)
            if len(calls) > 1:
                message = "repository_observation_unavailable"
                raise ValueError(message)
            return original(*args, **kwargs)

        monkeypatch.setattr(attest, "resolve_git_effect_repository", observe)
    git(repo, "update-ref", "refs/heads/dev", after["head"], before["head"])
    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        attest.validate(repo, effect, record, issuer=ISSUER, plan=plan)
    if mode == "postobserve":
        assert len(calls) == 2


@pytest.mark.parametrize("mode", ["plan", "statement"])
def test_attestation_parsing_rejects_malformed_projection(tmp_path, monkeypatch, mode):
    _repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    if mode == "plan":
        record = _reissue(record, payload={"kind": record.payload.kind, "body": {"plan": {}}})
    else:
        monkeypatch.setattr(attest, "mutable_json", lambda _value: ())
    with pytest.raises(
        ValueError if mode == "plan" else TypeError, match=f"git_effect_attestation_{mode}_invalid"
    ):
        attest.plan_from_attestation(record)


@pytest.mark.parametrize(
    ("mode", "error"),
    [
        ("empty", ""),
        ("exact", ""),
        ("duplicate", "collision"),
        ("issuer", "content_mismatch"),
        ("store", "invalid"),
    ],
)
def test_validated_plan_selection_requires_unique_evidence(tmp_path, monkeypatch, mode, error):
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)

    def read(_root):
        if mode == "store":
            message = "corrupt"
            raise ValueError(message)
        return {}, () if mode == "empty" else (record, record) if mode == "duplicate" else (record,)

    monkeypatch.setattr(attest, "read_attestation_set", read)

    def select():
        return attest.validated_plan_attestation(
            repo, plan.digest, issuer="agent:test:other" if mode == "issuer" else ISSUER
        )

    if error:
        with pytest.raises(ValueError, match="git_effect_attestation_" + error):
            select()
    else:
        assert select() == ((plan, record) if mode == "exact" else None)


@pytest.mark.parametrize(
    "mode",
    [
        "exact",
        "ambiguous",
        "store",
        "predicate",
        "plan",
        "invalid",
        "transition",
        "ref",
        "head",
        "assertion",
    ],
)
def test_accepted_closeout_selects_only_valid_exact_candidate_effect(tmp_path, monkeypatch, mode):
    repo, effect, plan, before, after = _case(
        tmp_path, transition="other" if mode == "transition" else "candidate.accept"
    )
    record = _record(effect, plan, before, after)
    if mode == "predicate":
        record = _reissue(record, predicate="proof:execution")
    elif mode in {"plan", "invalid"}:
        record = _reissue(
            record,
            payload={
                "kind": record.payload.kind,
                "body": {
                    **record.payload.body,
                    **({"plan": {}} if mode == "plan" else {"command": ["git"]}),
                },
            },
        )
    if mode in {"ambiguous", "store"}:

        def read(_root):
            if mode == "store":
                message = "unreadable store"
                raise ValueError(message)
            return {}, (record, record)

        monkeypatch.setattr(attest, "read_attestation_set", read)
    else:
        record_attestations(repo, (record,))

    def select():
        return attest.accepted_closeout_attestation(
            repo,
            accepted_ref="refs/heads/other" if mode == "ref" else "refs/heads/dev",
            candidate_ref="refs/heads/other" if mode == "assertion" else "refs/heads/candidate/dev",
            candidate_head=before["head"] if mode == "head" else after["head"],
        )

    if mode in {"ambiguous", "store"}:
        with pytest.raises(
            ValueError,
            match="accepted_closeout_effect_" + ("ambiguous" if mode == "ambiguous" else "invalid"),
        ):
            select()
    else:
        assert select() == ((plan, record) if mode == "exact" else None)


@pytest.mark.parametrize(
    "mode", ["exact", "ambiguous", "store", "invalid", "operation", "ref", "head", "assertions"]
)
def test_recovery_selection_binds_valid_current_effect(tmp_path, monkeypatch, mode):
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    desired = next(iter(effect.updates.values())).desired
    git(repo, "update-ref", "refs/heads/dev", desired, before["head"])
    if mode == "invalid":
        record = _reissue(record, facts_digest="e" * 64)

    def read(_root):
        if mode == "store":
            message = "unreadable store"
            raise ValueError(message)
        return {}, (record, record) if mode == "ambiguous" else (
            _reissue(record, predicate="proof:other"),
            record,
        )

    monkeypatch.setattr(attest, "read_attestation_set", read)

    def select():
        return attest.recover_plan(
            repo,
            operation="other" if mode == "operation" else "git.ref.compare-and-swap",
            desired=before["head"] if mode == "head" else desired,
            ref_name="refs/heads/other" if mode == "ref" else "refs/heads/dev",
            assertions={"refs/heads/other": desired} if mode == "assertions" else {},
        )

    if mode in {"ambiguous", "store"}:
        with pytest.raises(
            ValueError,
            match="git_effect_recovery_" + ("ambiguous" if mode == "ambiguous" else "unproven"),
        ):
            select()
    else:
        assert select() == (plan if mode == "exact" else None)


@pytest.mark.parametrize("mode", ["exact", "collision", "store_collision", "store_failure"])
def test_attestation_record_store_preserves_exact_identity(tmp_path, monkeypatch, mode):
    repo, effect, plan, before, after = _case(tmp_path)
    record = _record(effect, plan, before, after)
    git(repo, "update-ref", "refs/heads/dev", after["head"], before["head"])
    assert attest.records(repo, plan) == ()
    if mode == "exact":
        assert attest.records(repo, plan, record) == (record,)
        assert attest.records(repo, plan, record) == attest.records(repo, plan) == (record,)
        return
    if mode == "collision":
        record_attestations(repo, (_reissue(record, verifier="agent:test:other"),))
    else:

        def refuse(*_args):
            raise ValueError(
                "attestation_set_identity_collision:test"
                if mode == "store_collision"
                else "storage_unavailable"
            )

        monkeypatch.setattr(attest, "record_attestations", refuse)
    with pytest.raises(
        ValueError,
        match="storage_unavailable"
        if mode == "store_failure"
        else "git_effect_attestation_collision",
    ):
        attest.records(repo, plan, record)

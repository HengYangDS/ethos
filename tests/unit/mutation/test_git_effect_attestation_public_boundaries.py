from __future__ import annotations

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.repo.git_effect_attestation as attest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ISSUER = "agent:test:attestation"


def _case(tmp_path: Path) -> tuple[Path, GitEffect, Any, dict[str, object], dict[str, object]]:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
        assertions={},
    )
    facts = Facts(
        repository="repository:repo",
        head=old,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={"refs": {"refs/heads/dev": old}, "assertions": {}},
    )
    plan = compile_git_effect_plan(
        Commitment(
            id="authority:test:attestation",
            intent="Exercise attestation boundaries.",
            subjects=("repository:repo",),
            permissions=("git.ref.compare-and-swap",),
        ),
        facts,
        prior_attestations={},
        policy={"operation": "test.attestation"},
        effect=effect,
    )
    before = {
        "head": old,
        "tree": facts.tree,
        "refs": {"refs/heads/dev": old},
        "assertions": {},
        "observed_at": "2026-08-10T00:00:00+00:00",
    }
    after = {
        "head": new,
        "tree": facts.tree,
        "refs": {"refs/heads/dev": new},
        "observed_at": "2026-08-10T00:00:01+00:00",
    }
    return repo, effect, plan, before, after


def _issued_record(tmp_path: Path) -> tuple[Path, GitEffect, Any, Attestation]:
    repo, effect, plan, before, after = _case(tmp_path)
    record = attest.issue(
        effect,
        plan=plan,
        issuer=ISSUER,
        evidence=("repository:repo", "applied", before, after),
    )
    return repo, effect, plan, record


@pytest.mark.parametrize("statement", [(), "not-an-object", ["not", "an", "object"]])
def test_statement_projection_rejects_non_object_claims(statement: object) -> None:
    record = Attestation.model_construct(statement=statement)
    with pytest.raises(TypeError, match="statement"):
        attest._statement(record)  # noqa: SLF001


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        ("ref_intent_missing", None),
        ("ref_intent_ambiguous", "git_effect_recovery_ambiguous"),
        ("ref_intent_corrupt", "git_effect_recovery_unproven"),
    ],
)
def test_recover_plan_classifies_missing_ambiguous_and_unproven_intents(
    monkeypatch: pytest.MonkeyPatch,
    gap: str,
    expected: str | None,
) -> None:
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {"gap": gap},
    )

    if expected is None:
        assert attest.recover_plan(Path("/repo"), operation="lane.retire", desired="a" * 40) is None
    else:
        with pytest.raises(ValueError, match=expected):
            attest.recover_plan(Path("/repo"), operation="lane.retire", desired="a" * 40)


def test_recover_plan_rejects_missing_or_mismatched_attested_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, effect, plan, _ = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {
            "gap": "",
            "plan_digest": plan.digest,
            "ref_name": "refs/heads/dev",
            "old_value": update.expected,
        },
    )

    with pytest.raises(ValueError, match="git_effect_recovery_unproven"):
        attest.recover_plan(repo, operation="test.attestation", desired=update.desired)


def test_plan_from_attestation_rejects_missing_carried_plan(tmp_path: Path) -> None:
    _repo, _effect, _plan, record = _issued_record(tmp_path)
    invalid = Attestation.issue(
        record.model_dump(mode="python", exclude={"id", "statement_digest", "schema_version"})
        | {"statement": {"claim": {"operation": "git.ref.compare-and-swap"}}}
    )

    with pytest.raises(ValueError, match="git_effect_attestation_plan_invalid"):
        attest.plan_from_attestation(invalid)


def test_records_rejects_corrupt_existing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _effect, plan, _ = _issued_record(tmp_path)
    directory = tmp_path / "ethos" / "git-effects"
    directory.mkdir(parents=True)
    (directory / f"{plan.digest}.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(attest, "git_common_dir", lambda _root: tmp_path)

    with pytest.raises(ValueError, match="git_effect_attestation_invalid"):
        attest.records(repo, plan)


@pytest.mark.parametrize("failure", ["time-order", "invalid-time", "repository"])
def test_matches_rejects_temporal_and_repository_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    repo, effect, _plan, before, after = _case(tmp_path)
    observed = {
        "before": before["observed_at"],
        "after": after["observed_at"],
    }
    if failure == "time-order":
        observed = {"before": after["observed_at"], "after": before["observed_at"]}
    elif failure == "invalid-time":
        observed = {"before": "invalid", "after": after["observed_at"]}
    else:
        monkeypatch.setattr(
            attest,
            "resolve_git_effect_repository",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("drift")),
        )

    assert not attest._matches(  # noqa: SLF001
        repo,
        effect,
        ("repository:repo", "applied", before, after),
        observed,
        {
            "mode": "semantic_scope",
            "repository": "repository:repo",
            "head": after["head"],
            "tree": after["tree"],
            "refs": after["refs"],
        },
    )

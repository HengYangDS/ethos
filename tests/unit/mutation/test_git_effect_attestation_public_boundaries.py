from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.repo.git_effect_attestation as attest
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

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
        commitment_fixture(
            id="authority:test:attestation",
            intent="Exercise attestation boundaries.",
            subjects=("repository:repo",),
        ),
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
    assert attest.recover_plan(
        repo, operation="git.ref.compare-and-swap", desired=update.desired
    ) is None

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

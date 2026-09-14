"""Native repository, CAS and proof inputs for Git effect boundary tests."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

ISSUER = "agent:test:case:one"


def fixture(root: Path, identity: str = "repository:repo") -> SimpleNamespace:
    repo = init_git_repo(root / "repo")
    write_test_profile(repo, profile_id=identity.removeprefix("repository:"))
    git(repo, "add", ".ethos/profile.toml")
    git(repo, "commit", "-m", "declare repository identity")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    return SimpleNamespace(repo=repo, old=old, new=new, effect=effect(old, new))


def effect(old: str, new: str, ref: str = "refs/heads/dev") -> GitEffect:
    return GitEffect(updates={ref: GitRefUpdate(expected=old, desired=new)})


def plan(
    root: Path,
    value: GitEffect,
    values: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
    prior: dict[str, object] | None = None,
) -> TransitionPlan:
    identity = f"repository:{root.name}"
    facts = Facts(
        repository=identity,
        head=git(root, "rev-parse", "HEAD"),
        tree=git(root, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={
            "refs": {name: update.expected for name, update in value.updates.items()},
            "assertions": value.assertions,
            **(values or {}),
        },
    )
    authority = commitment_fixture(
        id="authority:test:git-effect", acceptance=("acceptance:fixture",)
    )
    return compile_git_effect_plan(
        authority,
        facts,
        prior_attestations=prior or {},
        policy=policy or {"operation": "git.ref.compare-and-swap", "effect_digest": value.digest()},
        effect=value,
    )


def proof_plan(case: Any, value: GitEffect | None = None) -> TransitionPlan:
    value = value or case.effect
    desired = next(iter(value.updates.values())).desired
    policy = {"operation": "git.ref.compare-and-swap", "effect_digest": value.digest()}
    proof = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "proof:execution",
            "verifier": ISSUER,
            "subject": f"git:commit:{desired}",
            "issued_at": datetime(2026, 8, 1, tzinfo=UTC),
            "valid_from": datetime(2026, 8, 1, tzinfo=UTC),
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": "proof:execution", "body": {"head": desired}},
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": "a" * 64,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": canonical_json_digest(policy),
            "effect_digest": None,
            "mints_authority": False,
        }
    )
    return plan(
        case.repo,
        value,
        policy=policy,
        prior={"proof": proof.model_dump(mode="json")},
    )


def generation(branch: str) -> dict[str, object]:
    return {
        "lane_ref": branch,
        "generation": 1,
        "holder_ref": ISSUER,
        "expires_at": "2026-08-02T00:00:00+00:00",
    }

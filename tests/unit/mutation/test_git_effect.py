from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from stat import S_ISDIR

import pytest
from pydantic import ValidationError

import ethos.adapters.repo.git_effect_attestation
import ethos.adapters.repo.git_effects
import ethos.adapters.store.content_addressed
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import git_effect_attestations
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

_ISSUER = "agent:test:case:one"


def test_git_effect_lease_generation_binds_exact_carrier_coordinates() -> None:
    lease = {
        "lane_ref": "work/example",
        "lane_incarnation_id": "lane-incarnation:example",
        "lease_id": "lease:example",
        "epoch": 2,
        "holder_ref": _ISSUER,
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
        "issued_at": "2026-08-01T00:00:00+00:00",
        "renewed_at": "2026-08-01T12:00:00+00:00",
        "path_scope": ("src/**",),
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "e" * 64,
    }

    assert lease_generation(lease) == {
        "branch": lease["lane_ref"],
        **{name: lease[name] for name in lease if name != "lane_ref"},
    }


def _declare_repository(repo: Path, repository_id: str | None = None) -> str:
    repository_id = repository_id or f"repository:{repo.name}"
    (repo / ".ethos" / "commitment.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'id = "{repository_id}"',
                'intent = "Govern the fixture repository."',
                f'subjects = ["{repository_id}"]',
                "",
            )
        ),
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/commitment.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "declare repository identity",
    )
    return repository_id


def _effect(*, old: str, new: str) -> GitEffect:
    return GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)})


def _plan(
    repo: Path,
    effect: GitEffect,
    *,
    permissions: tuple[str, ...] = ("git.ref.compare-and-swap",),
    facts_values: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
) -> TransitionPlan:
    repository = f"repository:{repo.name}"
    authority = Commitment(
        id="authority:test:git-effect",
        intent="Apply one verified Git ref transition.",
        subjects=(repository,),
        permissions=permissions,
    )
    values = facts_values or {}
    facts = Facts(
        repository=repository,
        head=git(repo, "rev-parse", "HEAD"),
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={
            "refs": {ref: update.expected for ref, update in effect.updates.items()},
            "assertions": effect.assertions,
            **values,
        },
    )
    return compile_git_effect_plan(
        authority,
        facts,
        prior_attestations={},
        policy=policy or {"name": "test"},
        effect=effect,
    )


def test_git_effect_applies_exact_cas_and_replays_matching_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    repository_id = _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    old_tree = git(repo, "rev-parse", "HEAD^{tree}")
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    git(repo, "add", "NEXT.md")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    programs: list[tuple[object, object]] = []
    run_git = ethos.adapters.repo.git_effects.run_git

    def record_program(root, *args, **kwargs):
        if args == ("update-ref", "--stdin", "-z"):
            programs.append((kwargs.get("stdin"), kwargs.get("text", True)))
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(ethos.adapters.repo.git_effects, "run_git", record_program)

    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    replayed = execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(applied,))

    assert git(repo, "rev-parse", "dev") == new
    assert applied.predicate == "effect:git-ref-update"
    assert applied.subject == f"git-effect:{effect.digest()}"
    assert applied.verdict == "pass"
    assert applied.plan_digest == plan.digest
    assert applied.effect_digest == effect.digest()
    assert applied.commitment_digest == plan.inputs.commitment
    assert applied.facts_digest == plan.inputs.facts
    assert applied.policy_digest == plan.inputs.policy
    assert len(applied.id) == 64
    assert "state" not in applied.statement
    assert "updates" not in applied.statement
    assert applied.statement["claim"] == {
        "operation": "git.ref.compare-and-swap",
        "effect": applied.subject,
    }
    assert applied.statement["repository"] == repository_id
    assert applied.statement["command"] == ("git", "update-ref", "--stdin", "-z")
    program = f"start\0update refs/heads/dev\0{new}\0{old}\0prepare\0commit\0".encode()
    assert programs == [(program, False)]
    assert applied.statement["program_sha256"] == hashlib.sha256(program).hexdigest()
    assert mutable_json(applied.statement["plan"]) == plan.model_dump(mode="json")
    assert mutable_json(applied.statement["effect"]) == effect.model_dump(mode="json")
    assert applied.statement["input"] == {
        "head": old,
        "tree": old_tree,
        "refs": {"refs/heads/dev": old},
        "assertions": {},
    }
    assert applied.statement["result"]["state"] == "applied"
    assert applied.statement["result"]["executed"] is True
    assert applied.statement["result"]["exit_code"] == 0
    assert applied.statement["result"]["refs"] == {"refs/heads/dev": new}
    assert applied.statement["output"] == {
        "head": new,
        "tree": old_tree,
        "refs": {"refs/heads/dev": new},
    }
    assert applied.statement["inputs"] == {
        "commitment": plan.inputs.commitment,
        "facts": plan.inputs.facts,
        "prior_attestations": plan.inputs.prior_attestations,
        "plan": plan.digest,
        "policy": plan.inputs.policy,
        "effect": effect.digest(),
    }
    assert isinstance(applied.statement["input_digest"], str)
    assert isinstance(applied.statement["output_digest"], str)
    assert applied.statement["observed_at"]["before"] <= applied.statement["observed_at"]["after"]
    assert applied.statement["freshness"] == {
        "mode": "semantic_scope",
        "repository": repository_id,
        "head": new,
        "tree": old_tree,
        "refs": {"refs/heads/dev": new},
    }
    assert applied.valid_from == applied.issued_at
    assert replayed is applied


def test_git_effect_repository_identity_is_stable_across_worktrees(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    repository_id = _declare_repository(repo, "repository:portable")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", linked.as_posix(), "dev")
    effect = _effect(old=old, new=new)

    attestation = execute_git_effect(linked, _plan(linked, effect), issuer=_ISSUER)

    assert attestation.statement["repository"] == repository_id


def test_git_effect_repository_identity_ignores_dirty_carrier_edits(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    repository_id = _declare_repository(repo, "repository:committed")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    carrier = repo / ".ethos" / "commitment.toml"
    carrier.write_text(
        carrier.read_text(encoding="utf-8").replace(repository_id, "repository:dirty"),
        encoding="utf-8",
    )
    effect = _effect(old=old, new=new)

    attestation = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)

    assert attestation.statement["repository"] == repository_id


def test_git_effect_blocks_repository_identity_change_before_ref_mutation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo, "repository:stable")
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "identity-change")
    carrier = repo / ".ethos" / "commitment.toml"
    carrier.write_text(
        carrier.read_text(encoding="utf-8").replace("repository:stable", "repository:changed"),
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/commitment.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "change repository identity",
    )
    new = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "dev")
    effect = _effect(old=old, new=new)

    with pytest.raises(ValueError, match="git_effect_repository_identity_mismatch"):
        execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)

    assert git(repo, "rev-parse", "dev") == old


def test_git_effect_blocks_foreign_expected_ref_identity(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo, "repository:stable")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    foreign = init_git_repo(tmp_path / "foreign")
    _declare_repository(foreign, "repository:foreign")
    foreign_head = git(foreign, "rev-parse", "HEAD")
    git(repo, "fetch", foreign.as_posix(), f"{foreign_head}:refs/heads/foreign")
    effect = _effect(old=foreign_head, new=new)

    with pytest.raises(ValueError, match="git_effect_repository_identity_mismatch"):
        execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)


def test_git_effect_program_is_canonical_across_mapping_order() -> None:
    first = GitEffect(
        updates={
            "refs/heads/z": GitRefUpdate(expected="0" * 40, desired="1" * 40),
            "refs/heads/a": GitRefUpdate(expected="2" * 40, desired="3" * 40),
        },
        assertions={"refs/heads/y": "4" * 40, "refs/heads/b": "5" * 40},
    )
    reordered = GitEffect(
        updates=dict(reversed(tuple(first.updates.items()))),
        assertions=dict(reversed(tuple(first.assertions.items()))),
    )

    assert first.digest() == reordered.digest()
    assert first.program() == reordered.program()
    assert isinstance(first.program(), bytes)


def test_git_effect_program_hashes_the_exact_utf8_ref_bytes() -> None:
    effect = GitEffect(
        updates={
            "refs/heads/变更": GitRefUpdate(expected="0" * 40, desired="1" * 40),
        }
    )

    assert b"refs/heads/\xe5\x8f\x98\xe6\x9b\xb4" in effect.program()
    assert effect.digest() == hashlib.sha256(effect.program()).hexdigest()


def test_git_effect_mappings_are_immutable() -> None:
    effect = GitEffect(
        updates={
            "refs/heads/dev": GitRefUpdate(expected="0" * 40, desired="1" * 40),
        },
        assertions={"refs/heads/main": "2" * 40},
    )

    with pytest.raises(TypeError):
        effect.updates["refs/heads/main"] = GitRefUpdate(
            expected="2" * 40,
            desired="3" * 40,
        )
    with pytest.raises(TypeError):
        effect.assertions["refs/heads/main"] = "3" * 40


def test_git_effect_recovers_attestation_when_desired_state_already_holds(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    git(repo, "add", "NEXT.md")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    git(repo, "update-ref", "refs/heads/dev", new, old)

    recovered = execute_git_effect(repo, plan, issuer=_ISSUER)

    assert recovered.statement["result"]["state"] == "recovered"
    assert recovered.statement["result"]["executed"] is False


@pytest.mark.parametrize(
    ("lease_state", "commitment_binding"),
    [("expired", "expired"), ("unknown", "unknown"), ("valid", "mismatch")],
)
def test_git_effect_recovery_requires_a_live_commitment_bound_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lease_state: str,
    commitment_binding: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    generation = {
        "branch": "dev",
        "lease_id": "lease:test",
        "epoch": 1,
        "holder_ref": _ISSUER,
        "expected_head": old,
        "expected_tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "base_commitment_path": ".ethos/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "a" * 64,
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "b" * 64,
    }
    plan = _plan(repo, effect, facts_values={"lease_generation": generation})
    git(repo, "update-ref", "refs/heads/dev", new, old)
    monkeypatch.setenv("ETHOS_ACTOR", _ISSUER)
    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects.leases_by_branch",
        lambda _root: {
            "dev": generation
            | {
                "lease_state": lease_state,
                "commitment_binding": commitment_binding,
            }
        },
    )

    with pytest.raises(ValueError, match="git_effect_lease_generation_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER)


def test_git_effect_blocks_identity_collision_and_stale_cas(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    collision = Attestation.issue(
        {
            "predicate": "effect:git-ref-update",
            "verifier": _ISSUER,
            "subject": f"git-effect:{'b' * 64}",
            "issued_at": datetime(2026, 7, 25, tzinfo=UTC),
            "verdict": "pass",
            "statement": {},
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect.digest(),
        }
    )

    with pytest.raises(ValueError, match="git_effect_identity_collision"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(collision,))

    git(repo, "update-ref", "refs/heads/dev", new, old)
    stale_effect = _effect(old="0" * 40, new=old)
    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        execute_git_effect(repo, _plan(repo, stale_effect), issuer=_ISSUER)


def test_git_effect_requires_explicit_permission_admission(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        execute_git_effect(repo, _plan(repo, effect, permissions=()), issuer=_ISSUER)


def test_git_effect_blocks_assertion_drift_before_recovery(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    git(repo, "branch", "candidate/dev", old)
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
        assertions={"refs/heads/candidate/dev": old},
    )
    git(repo, "update-ref", "refs/heads/candidate/dev", new, old)

    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)


def test_git_effect_revalidates_state_before_replaying_attestation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    git(repo, "update-ref", "refs/heads/dev", old, new)

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(applied,))


def test_git_effect_replay_rejects_typed_evidence_drift(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)

    for field, value in (
        ("repository", "git:other"),
        ("command", ("git", "update-ref")),
        ("program_sha256", "0" * 64),
        ("result", applied.statement["result"] | {"exit_code": 7}),
        ("inputs", {}),
        ("output_digest", "0" * 64),
    ):
        forged = Attestation.issue(
            applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
            | {"statement": applied.statement | {field: value}}
        )
        with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
            execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(forged,))


def test_git_effect_replay_rejects_invalid_validity_window(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    stale = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "issued_at": applied.issued_at - timedelta(minutes=2),
            "valid_from": applied.issued_at - timedelta(minutes=2),
            "valid_until": applied.issued_at - timedelta(minutes=1),
        }
    )

    with pytest.raises(ValueError, match="git_effect_attestation_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(stale,))


def test_git_effect_replay_binds_issue_time_to_post_observation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    forged = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"issued_at": applied.issued_at + timedelta(seconds=1)}
    )

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(forged,))


def test_git_effect_stale_evidence_is_classified_before_live_postcondition(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    stale = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "issued_at": applied.issued_at - timedelta(minutes=2),
            "valid_from": applied.issued_at - timedelta(minutes=2),
            "valid_until": applied.issued_at - timedelta(minutes=1),
        }
    )
    git(repo, "update-ref", "refs/heads/dev", old, new)

    with pytest.raises(ValueError, match="git_effect_attestation_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(stale,))


def test_git_effect_replay_rejects_checkout_head_drift(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    git(repo, "checkout", "-q", "-b", "side")
    (repo / "SIDE.md").write_text("side\n", encoding="utf-8")
    git(repo, "add", "SIDE.md")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "move checkout head",
    )

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(applied,))


def test_git_effect_store_rejects_invalid_typed_evidence(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    forged = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"statement": applied.statement | {"repository": "git:other"}}
    )

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        git_effect_attestations(repo, effect, forged)


def test_git_effect_store_validates_the_exact_plan_carried_by_attestation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)
    carried_plan = _plan(repo, effect, policy={"name": "carried"})
    carried_inputs = {
        "commitment": carried_plan.inputs.commitment,
        "facts": carried_plan.inputs.facts,
        "prior_attestations": carried_plan.inputs.prior_attestations,
        "plan": carried_plan.digest,
        "policy": carried_plan.inputs.policy,
        "effect": effect.digest(),
    }
    carried_statement = applied.statement | {
        "plan": carried_plan.model_dump(mode="json"),
        "inputs": carried_inputs,
        "input_digest": canonical_json_digest(
            {"input": applied.statement["input"], "inputs": carried_inputs}
        ),
    }
    carried = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "commitment_digest": carried_plan.inputs.commitment,
            "facts_digest": carried_plan.inputs.facts,
            "plan_digest": carried_plan.digest,
            "policy_digest": carried_plan.inputs.policy,
            "statement": carried_statement,
        }
    )

    stored = git_effect_attestations(repo, effect, carried)

    assert stored == (carried,)
    assert git_effect_attestations(repo, effect) == stored
    assert mutable_json(stored[0].statement["plan"]) == carried_plan.model_dump(mode="json")


def test_git_effect_store_rejects_invalid_carried_plan_closure(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)
    carried = mutable_json(applied.statement["plan"])
    assert isinstance(carried, dict)
    carried["commitment"] = carried["commitment"] | {"intent": "forged"}
    forged = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"statement": applied.statement | {"plan": carried}}
    )

    with pytest.raises(ValueError, match="git_effect_attestation_plan_invalid"):
        git_effect_attestations(repo, effect, forged)


def test_git_effect_store_is_atomic_and_rejects_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)
    original_link = ethos.adapters.store.content_addressed.os.link
    original_fsync = ethos.adapters.store.content_addressed.os.fsync
    fsync_modes: list[bool] = []

    def record_fsync(descriptor: int) -> None:
        fsync_modes.append(
            S_ISDIR(ethos.adapters.store.content_addressed.os.fstat(descriptor).st_mode)
        )
        original_fsync(descriptor)

    def fail_link(source: str | Path, target: str | Path) -> None:
        if Path(target).name == f"{effect.digest()}.json":
            message = "link failed"
            raise OSError(message)
        original_link(source, target)

    monkeypatch.setattr(ethos.adapters.store.content_addressed.os, "link", fail_link)
    monkeypatch.setattr(ethos.adapters.store.content_addressed.os, "fsync", record_fsync)
    with pytest.raises(OSError, match="link failed"):
        git_effect_attestations(repo, effect, applied)

    store = repo / git(repo, "rev-parse", "--git-common-dir") / "ethos" / "git-effects"
    assert not (store / f"{effect.digest()}.json").exists()
    assert list(store.glob(f".{effect.digest()}.json-*")) == []

    monkeypatch.setattr(ethos.adapters.store.content_addressed.os, "link", original_link)
    stored = git_effect_attestations(repo, effect, applied)
    assert stored == (applied,)
    assert False in fsync_modes
    assert True in fsync_modes
    path = store / f"{effect.digest()}.json"
    path.write_text(
        Attestation.issue(
            applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
            | {"verifier": "agent:test:case:collision"}
        ).canonical_json(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="git_effect_attestation_collision"):
        git_effect_attestations(repo, effect, applied)


def test_content_addressed_store_rejects_existing_symlink(tmp_path: Path) -> None:
    payload = b"immutable"
    target = tmp_path / "target"
    target.write_bytes(payload)
    path = tmp_path / "store" / "item"
    path.parent.mkdir()
    path.symlink_to(target)

    with pytest.raises(ValueError, match="content_collision"):
        ethos.adapters.store.content_addressed.write_content_addressed(
            path, payload, collision="content_collision"
        )


@pytest.mark.parametrize("field", ["commitment", "facts", "policy", "effect"])
def test_git_effect_blocks_tampered_plan_bindings_before_mutation(
    tmp_path: Path, field: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    tampered = plan.model_copy(update={"inputs": plan.inputs.model_copy(update={field: "0" * 64})})

    with pytest.raises(ValueError, match="git_effect_plan_mismatch"):
        execute_git_effect(repo, tampered, issuer=_ISSUER)

    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") == old


def test_git_effect_blocks_stale_carried_prestate_before_mutation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    (repo / "DRIFT.md").write_text("drift\n", encoding="utf-8")
    git(repo, "add", "DRIFT.md")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "drift",
    )

    with pytest.raises(ValueError, match="git_effect_plan_prestate_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER)

    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") != new


def test_git_effect_blocks_stale_lease_generation_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    generation = {
        "branch": "work/test",
        "lease_id": "lease:test",
        "epoch": 1,
        "holder_ref": _ISSUER,
        "expected_head": old,
        "expected_tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "base_commitment_path": ".ethos/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "a" * 64,
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "b" * 64,
    }
    plan = _plan(repo, effect, facts_values={"lease_generation": generation})
    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects.leases_by_branch",
        lambda _root: {"work/test": generation | {"epoch": 2}},
    )

    with pytest.raises(ValueError, match="git_effect_lease_generation_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER)

    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") == old


@pytest.mark.parametrize(
    ("lease_state", "commitment_binding"),
    [("expired", "expired"), ("unknown", "unknown"), ("valid", "mismatch")],
)
def test_git_effect_requires_a_live_commitment_bound_lease_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lease_state: str,
    commitment_binding: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    generation = {
        "branch": "work/test",
        "lease_id": "lease:test",
        "epoch": 1,
        "holder_ref": _ISSUER,
        "expected_head": old,
        "expected_tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "base_commitment_path": ".ethos/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "a" * 64,
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "b" * 64,
    }
    plan = _plan(repo, effect, facts_values={"lease_generation": generation})
    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects.leases_by_branch",
        lambda _root: {
            "work/test": generation
            | {
                "subject": "work/test",
                "lease_state": lease_state,
                "commitment_binding": commitment_binding,
            }
        },
    )

    with pytest.raises(ValueError, match="git_effect_lease_generation_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER)

    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") == old


def test_git_effect_replay_blocks_binding_drift_unknown_verdict_and_duplicate(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    plan = _plan(repo, effect)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    stale_binding = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"facts_digest": "e" * 64}
    )

    with pytest.raises(
        ValueError,
        match="git_effect_attestation_binding_mismatch:facts_digest",
    ):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(stale_binding,))

    unknown = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"verdict": "unknown"}
    )
    with pytest.raises(ValueError, match="git_effect_attestation_verdict_unknown"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(unknown,))

    with pytest.raises(ValueError, match="git_effect_attestation_duplicate"):
        execute_git_effect(repo, plan, issuer=_ISSUER, attestations=(applied, applied))


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
        GitEffect(updates=updates, assertions=assertions)


def test_git_effect_rejects_noncanonical_ref_name() -> None:
    with pytest.raises(ValidationError, match="git_effect_permissions_invalid"):
        GitEffect(
            updates={
                "refs/heads/dev\nupdate refs/heads/main": GitRefUpdate(
                    expected="0" * 40,
                    desired="1" * 40,
                )
            },
        )

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
import ethos.adapters.store.content_addressed
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import GitEffectExecutionRequest
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import git_effect_attestations
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

_COMMITMENT_DIGEST = "c" * 64
_REPOSITORY_FACTS_DIGEST = "f" * 64
_POLICY_DIGEST = "d" * 64


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
    commitment_digest: str = _COMMITMENT_DIGEST,
    facts_digest: str = _REPOSITORY_FACTS_DIGEST,
    policy_digest: str = _POLICY_DIGEST,
) -> Attestation:
    return execute_git_effect(
        repo,
        effect,
        GitEffectExecutionRequest(
            issuer="agent:test:case:one",
            attestations=attestations,
            permissions=permissions,
            commitment_digest=commitment_digest,
            facts_digest=facts_digest,
            policy_digest=policy_digest,
        ),
    )


def test_git_effect_applies_exact_cas_and_replays_matching_attestation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    repository_id = _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    old_tree = git(repo, "rev-parse", "HEAD^{tree}")
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    git(repo, "add", "NEXT.md")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)

    applied = _execute(repo, effect)
    replayed = _execute(repo, effect, attestations=(applied,))

    assert git(repo, "rev-parse", "dev") == new
    assert applied.predicate == "effect:git-ref-update"
    assert applied.subject == effect.id
    assert applied.verdict == "pass"
    assert applied.plan_digest == effect.plan_digest
    assert applied.effect_digest == effect.digest()
    assert applied.commitment_digest == _COMMITMENT_DIGEST
    assert applied.facts_digest == _REPOSITORY_FACTS_DIGEST
    assert applied.policy_digest == _POLICY_DIGEST
    assert len(applied.id) == 64
    assert "state" not in applied.statement
    assert "updates" not in applied.statement
    assert applied.statement["claim"] == {
        "operation": "git.ref.compare-and-swap",
        "effect": effect.id,
    }
    assert applied.statement["repository"] == repository_id
    assert applied.statement["command"] == ("git", "update-ref", "--stdin", "-z")
    program = f"start\0update refs/heads/dev\0{new}\0{old}\0prepare\0commit\0"
    assert applied.statement["program_sha256"] == hashlib.sha256(program.encode()).hexdigest()
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
        "commitment": _COMMITMENT_DIGEST,
        "facts": _REPOSITORY_FACTS_DIGEST,
        "plan": effect.plan_digest,
        "policy": _POLICY_DIGEST,
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

    attestation = _execute(linked, _effect(old=old, new=new))

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

    attestation = _execute(repo, _effect(old=old, new=new))

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

    with pytest.raises(ValueError, match="git_effect_repository_identity_mismatch"):
        _execute(repo, _effect(old=old, new=new))

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

    with pytest.raises(ValueError, match="git_effect_repository_identity_mismatch"):
        _execute(repo, _effect(old=foreign_head, new=new))


def test_git_effect_program_is_canonical_across_mapping_order() -> None:
    first = GitEffect(
        id="effect:ordered",
        plan_digest="a" * 64,
        updates={
            "refs/heads/z": GitRefUpdate(expected="0" * 40, desired="1" * 40),
            "refs/heads/a": GitRefUpdate(expected="2" * 40, desired="3" * 40),
        },
        assertions={"refs/heads/y": "4" * 40, "refs/heads/b": "5" * 40},
    )
    reordered = GitEffect(
        id=first.id,
        plan_digest=first.plan_digest,
        updates=dict(reversed(tuple(first.updates.items()))),
        assertions=dict(reversed(tuple(first.assertions.items()))),
    )

    assert first.digest() == reordered.digest()
    assert ethos.adapters.repo.git_effect_attestation.transaction_program(
        first
    ) == ethos.adapters.repo.git_effect_attestation.transaction_program(reordered)
    assert ethos.adapters.repo.git_effect_attestation.program_digest(
        first
    ) == ethos.adapters.repo.git_effect_attestation.program_digest(reordered)


def test_git_effect_recovers_attestation_when_desired_state_already_holds(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    git(repo, "update-ref", "refs/heads/dev", new, old)

    recovered = _execute(repo, _effect(old=old, new=new))

    assert recovered.statement["result"]["state"] == "recovered"
    assert recovered.statement["result"]["executed"] is False


def test_git_effect_blocks_identity_collision_and_stale_cas(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    collision = Attestation.issue(
        {
            "predicate": "effect:git-ref-update",
            "verifier": "agent:test:case:one",
            "subject": effect.id,
            "issued_at": datetime(2026, 7, 25, tzinfo=UTC),
            "verdict": "pass",
            "statement": {"state": "applied", "updates": effect.model_dump(mode="json")["updates"]},
            "commitment_digest": _COMMITMENT_DIGEST,
            "facts_digest": _REPOSITORY_FACTS_DIGEST,
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
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        _execute(repo, _effect(old=old, new=new), permissions=())


def test_git_effect_blocks_assertion_drift_before_recovery(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
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
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
    git(repo, "update-ref", "refs/heads/dev", old, new)

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        _execute(repo, effect, attestations=(applied,))


def test_git_effect_replay_rejects_typed_evidence_drift(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)

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
            _execute(repo, effect, attestations=(forged,))


def test_git_effect_replay_rejects_invalid_validity_window(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
    stale = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "issued_at": applied.issued_at - timedelta(minutes=2),
            "valid_from": applied.issued_at - timedelta(minutes=2),
            "valid_until": applied.issued_at - timedelta(minutes=1),
        }
    )

    with pytest.raises(ValueError, match="git_effect_attestation_stale"):
        _execute(repo, effect, attestations=(stale,))


def test_git_effect_replay_binds_issue_time_to_post_observation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
    forged = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"issued_at": applied.issued_at + timedelta(seconds=1)}
    )

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        _execute(repo, effect, attestations=(forged,))


def test_git_effect_stale_evidence_is_classified_before_live_postcondition(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
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
        _execute(repo, effect, attestations=(stale,))


def test_git_effect_replay_rejects_checkout_head_drift(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
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
        _execute(repo, effect, attestations=(applied,))


def test_git_effect_store_rejects_invalid_typed_evidence(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
    forged = Attestation.issue(
        applied.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {"statement": applied.statement | {"repository": "git:other"}}
    )

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        git_effect_attestations(repo, effect, forged)


def test_git_effect_store_is_atomic_and_rejects_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)
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


@pytest.mark.parametrize(
    ("field", "error"),
    [
        ("commitment_digest", "git_effect_binding_missing:commitment_digest"),
        ("facts_digest", "git_effect_binding_missing:facts_digest"),
        ("policy_digest", "git_effect_binding_missing:policy_digest"),
    ],
)
def test_git_effect_blocks_before_mutation_when_required_binding_is_missing(
    tmp_path: Path, field: str, error: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    with pytest.raises(ValueError, match=error):
        _execute(
            repo,
            effect,
            commitment_digest=("" if field == "commitment_digest" else _COMMITMENT_DIGEST),
            facts_digest=("" if field == "facts_digest" else _REPOSITORY_FACTS_DIGEST),
            policy_digest="" if field == "policy_digest" else _POLICY_DIGEST,
        )
    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") == old


def test_git_effect_replay_blocks_stale_binding_unknown_verdict_and_duplicate(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = _effect(old=old, new=new)
    applied = _execute(repo, effect)

    with pytest.raises(
        ValueError,
        match="git_effect_attestation_binding_mismatch:facts_digest",
    ):
        _execute(
            repo,
            effect,
            attestations=(applied,),
            facts_digest="e" * 64,
        )

    unknown = Attestation.issue(
        {
            "predicate": "effect:git-ref-update",
            "verifier": applied.verifier,
            "subject": effect.id,
            "issued_at": applied.issued_at,
            "verdict": "unknown",
            "statement": applied.statement,
            "commitment_digest": applied.commitment_digest,
            "facts_digest": applied.facts_digest,
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

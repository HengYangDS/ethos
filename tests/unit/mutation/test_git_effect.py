from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effect_attestation
import ethos.adapters.repo.git_effects
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import records
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import execute_git_effect
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
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_ISSUER = "agent:test:case:one"


def test_commit_git_worktree_binds_an_explicit_ssh_public_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    public_key = repo / "signing-key.pub"
    public_key.write_text("ssh-ed25519 AAAATEST exact-signing-key\n", encoding="utf-8")
    git(repo, "config", "commit.gpgsign", "true")
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", public_key.as_posix())
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    git(repo, "add", "README.md")
    previous = git(repo, "rev-parse", "HEAD")
    calls: list[dict[str, str]] = []
    original = ethos.adapters.repo.git_effects.run_git

    def capture(_root: Path, *args: str, **kwargs: object) -> object:
        if args[:1] == ("config",):
            return original(_root, *args, **kwargs)
        assert args == ("commit", "-m", "fix: signed effect")
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        calls.append(environment)
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(ethos.adapters.repo.git_effects, "run_git", capture)

    result = commit_git_worktree(
        repo,
        previous=previous,
        message="fix: signed effect",
        environment={
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": "/exact/hooks",
        },
    )

    assert result["verdict"] == "pass"
    assert calls == [
        {
            "GIT_CONFIG_COUNT": "3",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": "/exact/hooks",
            "GIT_CONFIG_KEY_1": "gpg.format",
            "GIT_CONFIG_VALUE_1": "ssh",
            "GIT_CONFIG_KEY_2": "user.signingkey",
            "GIT_CONFIG_VALUE_2": "key::ssh-ed25519 AAAATEST exact-signing-key",
        }
    ]


def test_commit_git_worktree_binds_effective_ssh_signer_without_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    key = tmp_path / "signing-key"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        text=True,
    )
    public_key = key.with_suffix(".pub")
    signer_record = tmp_path / "signer-record"
    signer = tmp_path / "ssh-signer"
    signer.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "previous=''\n"
        'for argument in "$@"; do\n'
        '  if [ "$previous" = "-f" ]; then\n'
        '    printf "%s\\n" "$argument" > "$ETHOS_TEST_SIGNER_RECORD"\n'
        "  fi\n"
        '  previous="$argument"\n'
        "done\n"
        'exec /usr/bin/ssh-keygen "$@"\n',
        encoding="utf-8",
    )
    signer.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(
        f'[gpg "ssh"]\n\tprogram = {signer}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig"))
    monkeypatch.setenv("ETHOS_TEST_SIGNER_RECORD", str(signer_record))
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    git(repo, "config", "commit.gpgsign", "true")
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", str(public_key))
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    git(repo, "add", "README.md")
    previous = git(repo, "rev-parse", "HEAD")

    result = commit_git_worktree(repo, previous=previous, message="fix: signed effect")

    assert result == {"verdict": "pass", "error": ""}
    assert git(repo, "rev-parse", "HEAD") != previous
    assert signer_record.read_text(encoding="utf-8").strip() == str(public_key)


def _declare_repository(repo: Path, repository_id: str | None = None) -> str:
    repository_id = repository_id or f"repository:{repo.name}"
    commit_fixture_file(
        repo,
        ".ethos/commitment.toml",
        "schema_version = 1\n"
        f'id = "{repository_id}"\n'
        'intent = "Govern the fixture repository."\n'
        f'subjects = ["{repository_id}"]\n',
        "declare repository identity",
    )
    return repository_id


def _effect(*, old: str, new: str) -> GitEffect:
    return GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)})


def _fixture_effect(repo: Path) -> tuple[str, str, GitEffect]:
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    return old, new, _effect(old=old, new=new)


def _effect_fixture(
    tmp_path: Path, repository_id: str | None = None
) -> tuple[Path, str, str, GitEffect]:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo, repository_id)
    return (repo, *_fixture_effect(repo))


def _lease_generation(repo: Path, old: str, branch: str) -> dict[str, object]:
    return {
        "branch": branch,
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


def _plan(
    repo: Path,
    effect: GitEffect,
    *,
    permissions: tuple[str, ...] = ("git.ref.compare-and-swap",),
    facts_values: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
    prior_attestations: dict[str, object] | None = None,
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
        prior_attestations=prior_attestations or {},
        policy=policy or {"operation": "test.apply"},
        effect=effect,
    )


def _proof_bound_plan(
    repo: Path,
    effect: GitEffect,
) -> TransitionPlan:
    proof = Attestation.issue(
        {
            "predicate": "proof:execution",
            "verifier": _ISSUER,
            "subject": f"git:commit:{next(iter(effect.updates.values())).desired}",
            "issued_at": datetime(2026, 8, 1, tzinfo=UTC),
            "valid_from": datetime(2026, 8, 1, tzinfo=UTC),
            "verdict": "pass",
            "statement": {},
            "commitment_digest": "a" * 64,
            "policy_digest": canonical_json_digest({"operation": "candidate.integrate"}),
        }
    )
    return _plan(
        repo,
        effect,
        policy={"operation": "candidate.integrate"},
        prior_attestations={"proof": proof.model_dump(mode="json")},
    )


def _applied_fixture(
    tmp_path: Path,
) -> tuple[Path, str, str, GitEffect, TransitionPlan, Attestation]:
    repo, old, new, effect = _effect_fixture(tmp_path)
    plan = _plan(repo, effect)
    return repo, old, new, effect, plan, execute_git_effect(repo, plan, issuer=_ISSUER)


def _reissue(attestation: Attestation, **updates: object) -> Attestation:
    payload = attestation.model_dump(
        mode="python", exclude={"id", "schema_version", "statement_digest"}
    )
    return Attestation.issue(payload | updates)


def _lease_plan(
    repo: Path,
    old: str,
    effect: GitEffect,
    branch: str,
) -> tuple[dict[str, object], TransitionPlan]:
    generation = _lease_generation(repo, old, branch)
    return generation, _plan(repo, effect, facts_values={"lease_generation": generation})


def test_git_effect_applies_exact_cas_and_recognizes_matching_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, old, new, effect = _effect_fixture(tmp_path)
    plan = _plan(repo, effect)
    programs: list[tuple[object, object]] = []
    original = ethos.adapters.repo.git_effects.run_git

    def capture(root, *args, **kwargs):
        if args == ("update-ref", "--stdin", "-z"):
            programs.append((kwargs.get("stdin"), kwargs.get("text", True)))
        return original(root, *args, **kwargs)

    monkeypatch.setattr(ethos.adapters.repo.git_effects, "run_git", capture)
    applied = execute_git_effect(repo, plan, issuer=_ISSUER)
    recognized = execute_git_effect(repo, plan, issuer=_ISSUER)
    statement = mutable_json(applied.statement)
    assert isinstance(statement, dict)
    assert programs == [(effect.program(), False)]
    assert (applied.predicate, applied.subject, applied.verdict) == (
        "effect:git-ref-update",
        f"git-effect:{effect.digest()}",
        "pass",
    )
    assert (applied.plan_digest, applied.effect_digest) == (plan.digest, effect.digest())
    assert (applied.commitment_digest, applied.facts_digest, applied.policy_digest) == (
        plan.inputs.commitment,
        plan.inputs.facts,
        plan.inputs.policy,
    )
    assert statement["repository"] == "repository:repo"
    assert statement["command"] == ["git", "update-ref", "--stdin", "-z"]
    assert statement["program_sha256"] == effect.digest()
    assert statement["plan"] == plan.model_dump(mode="json")
    assert statement["effect"] == effect.model_dump(mode="json")
    assert statement["input"]["refs"] == {"refs/heads/dev": old}
    assert statement["result"] == {
        "state": "applied",
        "executed": True,
        "exit_code": 0,
        "refs": {"refs/heads/dev": new},
    }
    assert statement["output"]["refs"] == {"refs/heads/dev": new}
    assert statement["freshness"] == {
        "mode": "semantic_scope",
        "repository": "repository:repo",
        **statement["output"],
    }
    observed = statement["observed_at"]
    assert isinstance(observed, dict)
    assert observed["before"] <= observed["after"]
    assert applied.issued_at == datetime.fromisoformat(str(observed["after"]))
    assert applied.valid_from == applied.issued_at
    assert recognized == applied
    assert git(repo, "rev-parse", "dev") == new
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_git_effect_rejects_unbound_detached_lease_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _old, _new, effect = _effect_fixture(tmp_path)
    current_lease = {
        **_lease_generation(repo, _old, "work/example"),
        "lane_ref": "work/example",
        "lease_state": "valid",
        "commitment_binding": "bound",
    }
    plan = _plan(
        repo,
        effect,
        facts_values={"lease_generation": lease_generation(current_lease)},
        policy={"operation": "lane.refresh", "execution_branch": "work/example"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", _ISSUER)
    monkeypatch.setattr(
        ethos.adapters.repo.git_effects,
        "leases_by_branch",
        lambda *_args, **_kwargs: {"work/example": current_lease},
    )
    run_git = ethos.adapters.repo.git_effects.run_git

    def detached(root, *args, **kwargs):
        if args == ("branch", "--show-current"):
            return type("Result", (), {"stdout": "", "returncode": 0})()
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(
        ethos.adapters.repo.git_effects,
        "run_git",
        detached,
    )

    with pytest.raises(ValueError, match="git_effect_lease_branch_mismatch"):
        execute_git_effect(repo, plan, issuer=_ISSUER)


def test_git_effect_repository_identity_is_stable_across_worktrees(tmp_path: Path) -> None:
    repository_id = "repository:portable"
    repo, _old, _new, effect = _effect_fixture(tmp_path, repository_id)
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", linked.as_posix(), "dev")

    attestation = execute_git_effect(linked, _plan(linked, effect), issuer=_ISSUER)

    assert attestation.statement["repository"] == repository_id


def test_git_effect_repository_identity_ignores_dirty_carrier_edits(tmp_path: Path) -> None:
    repository_id = "repository:committed"
    repo, _old, _new, effect = _effect_fixture(tmp_path, repository_id)
    carrier = repo / ".ethos" / "commitment.toml"
    carrier.write_text(
        carrier.read_text(encoding="utf-8").replace(repository_id, "repository:dirty"),
        encoding="utf-8",
    )
    attestation = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)

    assert attestation.statement["repository"] == repository_id


def test_git_effect_blocks_repository_identity_change_before_ref_mutation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo, "repository:stable")
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "identity-change")
    carrier = repo / ".ethos" / "commitment.toml"
    new = commit_fixture_file(
        repo,
        ".ethos/commitment.toml",
        carrier.read_text(encoding="utf-8").replace("repository:stable", "repository:changed"),
        "change repository identity",
    )
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


def test_git_effect_recovers_attestation_when_desired_state_already_holds(
    tmp_path: Path,
) -> None:
    repo, old, new, effect = _effect_fixture(tmp_path)
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    git(repo, "add", "NEXT.md")
    plan = _proof_bound_plan(repo, effect)
    write_ref_intent(
        root=repo,
        ref_name="refs/heads/dev",
        update=effect.updates["refs/heads/dev"],
        operation="candidate.integrate",
        plan_digest=plan.digest,
    )
    claim_ref_intent(
        root=repo,
        ref_name="refs/heads/dev",
        update=effect.updates["refs/heads/dev"],
        operation="candidate.integrate",
        phase="prepared",
        plan_digest=plan.digest,
    )
    git(repo, "update-ref", "refs/heads/dev", new, old)

    recovered = execute_git_effect(repo, plan, issuer=_ISSUER)

    assert recovered.statement["result"]["state"] == "recovered"
    assert recovered.statement["result"]["executed"] is False


def test_git_effect_does_not_attest_an_unowned_preexisting_ref_move(
    tmp_path: Path,
) -> None:
    repo, old, new, effect = _effect_fixture(tmp_path)
    plan = _proof_bound_plan(repo, effect)
    git(repo, "update-ref", "refs/heads/dev", new, old)

    with pytest.raises(ValueError, match="git_effect_recovery_intent_missing"):
        execute_git_effect(repo, plan, issuer=_ISSUER)


def test_git_effect_normalizes_an_absent_ref_to_the_expected_zero_oid(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _declare_repository(repo)
    head = git(repo, "rev-parse", "HEAD")
    effect = GitEffect(
        updates={
            "refs/heads/work/new": GitRefUpdate(expected="0" * len(head), desired=head),
        }
    )

    attestation = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)

    assert git(repo, "rev-parse", "work/new") == head
    assert attestation.statement["input"]["refs"] == {"refs/heads/work/new": "0" * len(head)}


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
    repo, old, new, effect = _effect_fixture(tmp_path)
    generation, plan = _lease_plan(repo, old, effect, "dev")
    git(repo, "update-ref", "refs/heads/dev", new, old)
    monkeypatch.setenv("ETHOS_ACTOR", _ISSUER)
    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects.leases_by_branch",
        lambda _root, **_kwargs: {
            "dev": generation
            | {
                "lease_state": lease_state,
                "commitment_binding": commitment_binding,
            }
        },
    )

    with pytest.raises(ValueError, match="git_effect_lease_generation_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER)


def test_git_effect_blocks_stale_cas(tmp_path: Path) -> None:
    repo, old, new, _ = _effect_fixture(tmp_path)
    git(repo, "update-ref", "refs/heads/dev", new, old)
    stale_effect = _effect(old="0" * 40, new=old)
    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        execute_git_effect(repo, _plan(repo, stale_effect), issuer=_ISSUER)


def test_git_effect_requires_explicit_permission_admission(tmp_path: Path) -> None:
    repo, _old, _new, effect = _effect_fixture(tmp_path)

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        execute_git_effect(repo, _plan(repo, effect, permissions=()), issuer=_ISSUER)


def test_git_effect_blocks_assertion_drift_before_recovery(tmp_path: Path) -> None:
    repo, old, new, _ = _effect_fixture(tmp_path)
    git(repo, "branch", "candidate/dev", old)
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
        assertions={"refs/heads/candidate/dev": old},
    )
    git(repo, "update-ref", "refs/heads/candidate/dev", new, old)

    with pytest.raises(ValueError, match="git_effect_cas_mismatch"):
        execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)


def test_git_effect_revalidates_state_before_recognizing_attestation(tmp_path: Path) -> None:
    repo, old, new, effect = _effect_fixture(tmp_path)
    plan = _plan(repo, effect)
    execute_git_effect(repo, plan, issuer=_ISSUER)
    git(repo, "update-ref", "refs/heads/dev", old, new)

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        execute_git_effect(repo, plan, issuer=_ISSUER)


def test_git_effect_record_rejects_typed_evidence_drift(tmp_path: Path) -> None:
    repo, _old, _new, _effect_value, plan, applied = _applied_fixture(tmp_path)

    for field, value in (
        ("repository", "git:other"),
        ("command", ("git", "update-ref")),
        ("program_sha256", "0" * 64),
        ("result", applied.statement["result"] | {"exit_code": 7}),
        ("inputs", {}),
        ("output_digest", "0" * 64),
    ):
        forged = _reissue(applied, statement=applied.statement | {field: value})
        with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
            records(repo, plan, forged)


@pytest.mark.parametrize("state", ["current", "drifted"])
def test_git_effect_rejects_expired_attestation_before_live_state(
    tmp_path: Path, state: str
) -> None:
    repo, old, new, _effect_value, plan, applied = _applied_fixture(tmp_path)
    stale = _reissue(
        applied,
        issued_at=applied.issued_at - timedelta(minutes=2),
        valid_from=applied.issued_at - timedelta(minutes=2),
        valid_until=applied.issued_at - timedelta(minutes=1),
    )
    if state == "drifted":
        git(repo, "update-ref", "refs/heads/dev", old, new)
    with pytest.raises(ValueError, match="git_effect_attestation_stale"):
        records(repo, plan, stale)


def test_git_effect_binds_issue_time_to_post_observation(tmp_path: Path) -> None:
    repo, _old, _new, _effect_value, plan, applied = _applied_fixture(tmp_path)
    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        records(repo, plan, _reissue(applied, issued_at=applied.issued_at + timedelta(seconds=1)))


def test_git_effect_record_rejects_checkout_head_drift(tmp_path: Path) -> None:
    repo, _old, _new, _effect_value, plan, applied = _applied_fixture(tmp_path)
    git(repo, "checkout", "-q", "-b", "side")
    commit_fixture_file(repo, "SIDE.md", "side\n", "move checkout head")

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        records(repo, plan, applied)


def test_git_effect_store_validates_the_exact_plan_carried_by_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _old, _new, effect = _effect_fixture(tmp_path)
    monkeypatch.setattr(
        ethos.adapters.repo.git_effect_attestation,
        "records",
        lambda *_args, **_kwargs: (),
    )
    applied = execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)
    carried_plan = _plan(repo, effect, policy={"name": "carried"})
    inputs = {
        "commitment": carried_plan.inputs.commitment,
        "facts": carried_plan.inputs.facts,
        "prior_attestations": carried_plan.inputs.prior_attestations,
        "plan": carried_plan.digest,
        "policy": carried_plan.inputs.policy,
        "effect": effect.digest(),
    }
    carried_statement = applied.statement | {
        "plan": carried_plan.model_dump(mode="json"),
        "inputs": inputs,
        "input_digest": canonical_json_digest(
            {"input": applied.statement["input"], "inputs": inputs}
        ),
    }
    carried = _reissue(
        applied,
        commitment_digest=carried_plan.inputs.commitment,
        facts_digest=carried_plan.inputs.facts,
        plan_digest=carried_plan.digest,
        policy_digest=carried_plan.inputs.policy,
        statement=carried_statement,
    )

    assert records(repo, carried_plan, carried) == (carried,)
    assert records(repo, carried_plan) == (carried,)


def test_git_effect_store_rejects_identity_collision(tmp_path: Path) -> None:
    repo, _old, _new, _effect, plan, applied = _applied_fixture(tmp_path)
    path = (
        repo
        / git(repo, "rev-parse", "--git-common-dir")
        / "ethos"
        / "git-effects"
        / f"{plan.digest}.json"
    )
    path.write_text(
        _reissue(applied, verifier="agent:test:case:collision").canonical_json(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="git_effect_attestation_collision"):
        records(repo, plan, applied)


@pytest.mark.parametrize("field", ["commitment", "facts", "policy", "effect"])
def test_git_effect_blocks_tampered_plan_bindings_before_mutation(
    tmp_path: Path, field: str
) -> None:
    repo, old, _new, effect = _effect_fixture(tmp_path)
    plan = _plan(repo, effect)
    tampered = plan.model_copy(update={"inputs": plan.inputs.model_copy(update={field: "0" * 64})})

    with pytest.raises(ValueError, match="git_effect_plan_mismatch"):
        execute_git_effect(repo, tampered, issuer=_ISSUER)

    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") == old


def test_git_effect_blocks_stale_carried_prestate_before_mutation(tmp_path: Path) -> None:
    repo, _old, new, effect = _effect_fixture(tmp_path)
    plan = _plan(repo, effect)
    commit_fixture_file(repo, "DRIFT.md", "drift\n", "drift")

    with pytest.raises(ValueError, match="git_effect_plan_prestate_stale"):
        execute_git_effect(repo, plan, issuer=_ISSUER)

    assert git_stdout(repo, "rev-parse", "--verify", "refs/heads/dev") != new


def test_git_effect_blocks_stale_lease_generation_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, old, _new, effect = _effect_fixture(tmp_path)
    generation, plan = _lease_plan(repo, old, effect, "work/test")
    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects.leases_by_branch",
        lambda _root, **_kwargs: {"work/test": generation | {"epoch": 2}},
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
    repo, old, _new, effect = _effect_fixture(tmp_path)
    generation, plan = _lease_plan(repo, old, effect, "work/test")
    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects.leases_by_branch",
        lambda _root, **_kwargs: {
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


def test_git_effect_record_blocks_binding_drift_and_unknown_verdict(
    tmp_path: Path,
) -> None:
    repo, _old, _new, _effect_value, plan, applied = _applied_fixture(tmp_path)
    stale_binding = _reissue(applied, facts_digest="e" * 64)

    with pytest.raises(
        ValueError,
        match="git_effect_attestation_binding_mismatch:facts_digest",
    ):
        records(repo, plan, stale_binding)

    unknown = _reissue(applied, verdict="unknown")
    with pytest.raises(ValueError, match="git_effect_attestation_verdict_unknown"):
        records(repo, plan, unknown)


def test_git_effect_owns_proof_bound_multiref_cas_attestation_and_intent_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, old, new, _ = _effect_fixture(tmp_path)
    git(repo, "branch", "candidate/dev", old)
    effect = GitEffect(
        updates={
            "refs/heads/candidate/dev": GitRefUpdate(expected=old, desired=new),
            "refs/heads/dev": GitRefUpdate(expected=old, desired=new),
        }
    )
    plan = _proof_bound_plan(repo, effect)
    persisted: list[Attestation] = []

    monkeypatch.setattr(
        ethos.adapters.repo.git_effect_attestation,
        "records",
        lambda _root, _effect, record=None: (
            persisted.append(record) if record is not None else tuple(persisted)
        ),
    )

    attestation = execute_git_effect(repo, plan, issuer=_ISSUER)

    assert {git(repo, "rev-parse", ref) for ref in ("dev", "candidate/dev")} == {new}
    assert persisted == [attestation]
    assert attestation.statement["result"]["state"] == "applied"
    assert attestation.statement["output"]["refs"] == {
        "refs/heads/candidate/dev": new,
        "refs/heads/dev": new,
    }
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_git_effect_cleans_every_intent_when_multiref_prepare_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, old, new, _ = _effect_fixture(tmp_path)
    effect = GitEffect(
        updates={
            "refs/heads/a": GitRefUpdate(expected="0" * len(old), desired=new),
            "refs/heads/b": GitRefUpdate(expected="0" * len(old), desired=new),
        }
    )
    claim = ethos.adapters.repo.git_effects.claim_ref_intent

    def fail_second_prepare(**kwargs):
        if kwargs["ref_name"] == "refs/heads/b" and kwargs["phase"] == "prepared":
            return {"gap": "forced_prepare_failure"}
        return claim(**kwargs)

    monkeypatch.setattr(
        ethos.adapters.repo.git_effects,
        "claim_ref_intent",
        fail_second_prepare,
    )

    with pytest.raises(ValueError, match="git_effect_ref_intent_prepared_forced_prepare_failure"):
        execute_git_effect(repo, _plan(repo, effect), issuer=_ISSUER)

    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_git_effect_recovers_after_attestation_persistence_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _old, new, effect = _effect_fixture(tmp_path)
    plan = _proof_bound_plan(repo, effect)
    persisted: list[Attestation] = []
    fail_once = True

    def persist(_root, _effect, record=None):
        nonlocal fail_once
        if record is not None and fail_once:
            fail_once = False
            msg = "storage unavailable"
            raise OSError(msg)
        if record is not None:
            persisted.append(record)
        return tuple(persisted)

    monkeypatch.setattr(ethos.adapters.repo.git_effect_attestation, "records", persist)

    with pytest.raises(OSError, match="storage unavailable"):
        execute_git_effect(repo, plan, issuer=_ISSUER)
    recovered = execute_git_effect(repo, plan, issuer=_ISSUER)

    assert git(repo, "rev-parse", "dev") == new
    assert recovered.statement["result"]["state"] == "recovered"
    assert persisted == [recovered]


def test_git_effect_recognition_retries_projection_before_clearing_intent(
    tmp_path: Path,
) -> None:
    repo, _old, _new, effect = _effect_fixture(tmp_path)
    plan = _proof_bound_plan(repo, effect)
    projected: list[str] = []
    fail_once = True

    def project() -> None:
        nonlocal fail_once
        if fail_once:
            fail_once = False
            msg = "projection unavailable"
            raise OSError(msg)
        projected.append("complete")

    with pytest.raises(OSError, match="projection unavailable"):
        execute_git_effect(repo, plan, issuer=_ISSUER, projection=project)

    assert list(ref_intent_dir(repo).glob("*.json"))
    attestation = execute_git_effect(repo, plan, issuer=_ISSUER, projection=project)

    assert attestation.statement["result"]["state"] == "applied"
    assert projected == ["complete"]
    assert not list(ref_intent_dir(repo).glob("*.json"))

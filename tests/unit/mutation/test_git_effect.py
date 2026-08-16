from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any

import pytest
import tomli_w

import ethos.adapters.repo.attestation_set as attestation_set
import ethos.adapters.repo.git_effect_admission as admission
import ethos.adapters.repo.git_effect_attestation as attest
import ethos.adapters.repo.git_effects as runtime
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import records
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import create_git_commit
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.literal_cases import literal_case
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from pathlib import Path

ISSUER = "agent:test:case:one"


def _staged_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    git(repo, "add", "README.md")
    return repo, git(repo, "rev-parse", "HEAD")


def test_commit_git_worktree_rejects_unarmed_repository_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, previous = _staged_repo(tmp_path)
    monkeypatch.setattr(
        runtime,
        "hook_runtime_binding",
        lambda _root: {"required_gaps": ["write_admission_not_armed:runtime_manifest"]},
    )

    with pytest.raises(ValueError, match="write_admission_not_armed:runtime_manifest"):
        commit_git_worktree(repo, previous=previous, message="fix: governed commit")


def test_commit_git_worktree_rejects_undeclared_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, previous = _staged_repo(tmp_path)
    monkeypatch.setattr(runtime, "hook_runtime_binding", lambda _root: {"required_gaps": []})

    for environment in (
        {"GIT_DIR": "/tmp/foreign"},
        {"ETHOS_FAKE_TRANSITION": "{}"},
    ):
        with pytest.raises(ValueError, match="git_effect_commit_environment_forbidden"):
            commit_git_worktree(
                repo,
                previous=previous,
                message="fix: governed commit",
                environment=environment,
            )


def test_commit_git_worktree_does_not_inherit_transition_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    previous = "a" * 40
    monkeypatch.setattr(runtime, "current_tracked_head", lambda _root: previous)
    monkeypatch.setattr(runtime, "hook_runtime_binding", lambda _root: {"required_gaps": []})
    monkeypatch.setattr(runtime, "commit_environment", lambda *_args: None)
    monkeypatch.setenv("ETHOS_ARCHIVE_TRANSITION", "forged")
    environments: list[dict[str, str]] = []

    def capture_commit(*_args: object, **kwargs: object) -> object:
        environments.append(dict(kwargs["env"]))
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr("ethos.adapters.repo.git._execute", capture_commit)

    commit_git_worktree(repo, previous=previous, message="fix: governed commit")

    assert "ETHOS_ARCHIVE_TRANSITION" not in environments[0]


def test_commit_git_worktree_binds_an_explicit_ssh_public_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, previous = _staged_repo(tmp_path)
    public_key = repo / "signing-key.pub"
    public_key.write_text("ssh-ed25519 AAAATEST exact-signing-key\n", encoding="utf-8")
    git(repo, "config", "commit.gpgsign", "true")
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", public_key.as_posix())
    monkeypatch.setattr(runtime, "hook_runtime_binding", lambda _root: {"required_gaps": []})
    calls: list[dict[str, str]] = []

    def capture_commit(_root: Path, *args: str, **kwargs: object) -> object:
        assert args == ("commit", "-m", "fix: signed effect")
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        calls.append(environment)
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(runtime, "run_git", capture_commit)

    result = commit_git_worktree(
        repo,
        previous=previous,
        message="fix: signed effect",
    )

    assert result["verdict"] == "pass"
    assert calls == [
        {
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "gpg.format",
            "GIT_CONFIG_VALUE_0": "ssh",
            "GIT_CONFIG_KEY_1": "user.signingkey",
            "GIT_CONFIG_VALUE_1": "key::ssh-ed25519 AAAATEST exact-signing-key",
        }
    ]


def test_commit_git_worktree_binds_effective_ssh_signer_without_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, previous = _staged_repo(tmp_path)
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
    monkeypatch.setattr(runtime, "hook_runtime_binding", lambda _root: {"required_gaps": []})

    result = commit_git_worktree(repo, previous=previous, message="fix: signed effect")

    assert result == {"verdict": "pass", "error": ""}
    assert git(repo, "rev-parse", "HEAD") != previous
    assert signer_record.read_text(encoding="utf-8").strip() == str(public_key)


def test_create_git_commit_inherits_effective_signing_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, previous = _staged_repo(tmp_path)
    public_key = repo / "signing-key.pub"
    public_key.write_text("ssh-ed25519 AAAATEST exact-signing-key\n", encoding="utf-8")
    git(repo, "config", "commit.gpgsign", "true")
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", public_key.as_posix())
    monkeypatch.setattr(
        runtime,
        "verify_commit_trust",
        lambda _root, revision: {
            "verdict": "pass",
            "revision": revision,
            "required_gaps": [],
        },
    )
    calls: list[dict[str, str]] = []

    def capture_commit(_root: Path, *args: str, **kwargs: object) -> object:
        assert args == (
            "commit-tree",
            "-S",
            git(repo, "write-tree"),
            "-p",
            previous,
            "-m",
            "bootstrap Commitment v2",
        )
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        calls.append(environment)
        return type("Result", (), {"returncode": 0, "stdout": "b" * 40, "stderr": ""})()

    create_git_commit(
        repo,
        tree=git(repo, "write-tree"),
        parent=previous,
        message="bootstrap Commitment v2",
        runner=capture_commit,
    )

    assert calls == [
        {
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "gpg.format",
            "GIT_CONFIG_VALUE_0": "ssh",
            "GIT_CONFIG_KEY_1": "user.signingkey",
            "GIT_CONFIG_VALUE_1": "key::ssh-ed25519 AAAATEST exact-signing-key",
        }
    ]


def test_create_git_commit_allows_unsigned_policy(tmp_path: Path) -> None:
    repo, previous = _staged_repo(tmp_path)

    completed = create_git_commit(
        repo,
        tree=git(repo, "write-tree"),
        parent=previous,
        message="bootstrap Commitment v2",
    )

    assert completed.returncode == 0
    assert "gpgsig " not in git(repo, "cat-file", "commit", completed.stdout.strip())


def test_create_git_commit_preserves_exact_multiline_message(tmp_path: Path) -> None:
    repo, previous = _staged_repo(tmp_path)
    message = "subject\n\nbody line\n"

    completed = create_git_commit(
        repo,
        tree=git(repo, "write-tree"),
        parent=previous,
        message=message,
        preserve_message=True,
    )

    raw = subprocess.run(
        ("git", "cat-file", "commit", completed.stdout.strip()),
        cwd=repo,
        capture_output=True,
        check=True,
    ).stdout
    assert raw.partition(b"\n\n")[2] == message.encode()


def test_create_git_commit_rejects_untrusted_signed_object(tmp_path: Path) -> None:
    repo, previous = _staged_repo(tmp_path)
    signing_key = tmp_path / "untrusted-signing-key"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(signing_key)),
        check=True,
        capture_output=True,
        text=True,
    )
    empty_anchor = tmp_path / "allowed-signers"
    empty_anchor.write_text("", encoding="utf-8")
    empty_anchor.chmod(0o600)
    git(repo, "config", "commit.gpgsign", "true")
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "gpg.ssh.program", "/usr/bin/ssh-keygen")
    git(repo, "config", "gpg.ssh.allowedSignersFile", empty_anchor.as_posix())
    git(repo, "config", "user.signingkey", signing_key.with_suffix(".pub").as_posix())

    completed = create_git_commit(
        repo,
        tree=git(repo, "write-tree"),
        parent=previous,
        message="bootstrap Commitment v2",
    )

    assert completed.returncode == 1
    assert completed.stderr == "commit_signature_untrusted"
    assert git(repo, "rev-parse", "HEAD") == previous


ZERO_OID, ZERO_DIGEST = "0" * 40, "0" * 64


def fixture(root: Path, identity: str = "repository:repo") -> SimpleNamespace:
    repo = init_git_repo(root / "repo")
    carrier = tomli_w.dumps(
        commitment_v2(
            id=identity,
            intent="Govern.",
            subjects=(identity,),
        ).model_dump(mode="python")
    )
    commit_fixture_file(repo, ".ethos/commitment.toml", carrier, "declare identity")
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
    authority = commitment_v2(
        id="authority:test:git-effect",
        intent="Apply CAS.",
        subjects=(identity,),
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


def generation(case: Any, branch: str) -> dict[str, object]:
    return {
        "branch": branch,
        "lease_id": "lease:test",
        "epoch": 1,
        "holder_ref": ISSUER,
        "expected_head": case.old,
        "expected_tree": git(case.repo, "rev-parse", "HEAD^{tree}"),
        "base_commitment_path": ".ethos/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "a" * 64,
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "b" * 64,
    }


def reissue(value: Attestation, **updates: object) -> Attestation:
    body = updates.pop("body", None)
    payload = value.model_dump(mode="python", exclude={"id"})
    if body is not None:
        payload["payload"] = {"kind": value.payload.kind, "body": body}
    return Attestation.issue(payload | updates)


def reject(error: str, call: Any) -> None:
    with pytest.raises((OSError, ValueError), match=error):
        call()


def test_exact_multiref_cas_attestation_recognition_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    git(case.repo, "branch", "candidate/dev", case.old)
    value = GitEffect(
        updates={
            ref: GitRefUpdate(expected=case.old, desired=case.new)
            for ref in ("refs/heads/candidate/dev", "refs/heads/dev")
        }
    )
    persisted: list[Attestation] = []
    programs: list[tuple[object, object]] = []
    original = runtime.run_git

    def capture(root: Path, *args: str, **kwargs: object) -> object:
        if args == ("update-ref", "--stdin", "-z"):
            programs.append((kwargs.get("stdin"), kwargs.get("text", True)))
        return original(root, *args, **kwargs)

    monkeypatch.setattr(runtime, "run_git", capture)
    monkeypatch.setattr(
        attest,
        "records",
        lambda _root, _plan, record=None, **_kwargs: (
            persisted.append(record) if record else tuple(persisted)
        ),
    )
    carried = proof_plan(case, value)
    applied = execute_git_effect(case.repo, carried, issuer=ISSUER)
    statement = applied.payload.body
    assert programs == [(value.program(), False)]
    assert (applied.predicate, applied.subject, applied.verdict) == (
        "effect:git-ref-update",
        f"git-effect:{value.digest()}",
        "pass",
    )
    assert (applied.plan_digest, applied.effect_digest) == (carried.digest, value.digest())
    assert statement["command"] == ("git", "update-ref", "--stdin", "-z")
    assert statement["program_sha256"] == value.digest()
    assert mutable_json(statement["plan"]) == carried.model_dump(mode="json")
    assert mutable_json(statement["effect"]) == value.model_dump(mode="json")
    assert statement["input"]["refs"] == dict.fromkeys(value.updates, case.old)
    assert (
        statement["result"]["refs"]
        == statement["output"]["refs"]
        == dict.fromkeys(value.updates, case.new)
    )
    assert (statement["result"]["state"], statement["result"]["executed"]) == ("applied", True)
    assert persisted == [applied]
    assert execute_git_effect(case.repo, carried, issuer=ISSUER) == applied
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


def test_empty_effect_issuer_is_rejected_before_ref_mutation(tmp_path: Path) -> None:
    case = fixture(tmp_path)

    reject(
        "git_effect_issuer_invalid",
        lambda: execute_git_effect(case.repo, plan(case.repo, case.effect), issuer=""),
    )

    assert git(case.repo, "rev-parse", "dev") == case.old
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


@pytest.mark.parametrize("kind", ["linked", "dirty", "changed", "foreign"])
def test_repository_worktree_identity_matrix(tmp_path: Path, kind: str) -> None:
    identity, case = "repository:portable", fixture(tmp_path, "repository:portable")
    root = case.repo
    if kind == "linked":
        root = tmp_path / "linked"
        git(case.repo, "worktree", "add", "--detach", str(root), "dev")
    elif kind == "dirty":
        carrier = root / ".ethos/commitment.toml"
        carrier.write_text(carrier.read_text().replace(identity, "repository:dirty"))
    elif kind == "changed":
        git(root, "checkout", "-q", "-b", "change")
        carrier = root / ".ethos/commitment.toml"
        case.new = commit_fixture_file(
            root,
            str(carrier.relative_to(root)),
            carrier.read_text().replace(identity, "repository:changed"),
            "change",
        )
        git(root, "checkout", "-q", "dev")
        case.effect = effect(case.old, case.new)
    elif kind == "foreign":
        other = fixture(tmp_path / "foreign", "repository:foreign")
        git(root, "fetch", str(other.repo), f"{other.old}:refs/heads/foreign")
        case.effect = effect(other.old, case.new)
    if kind in {"changed", "foreign"}:
        reject(
            "git_effect_repository_identity_mismatch",
            lambda: execute_git_effect(root, plan(root, case.effect), issuer=ISSUER),
        )
        assert git_stdout(case.repo, "rev-parse", "--verify", "refs/heads/dev") == case.old
    else:
        assert (
            execute_git_effect(root, plan(root, case.effect), issuer=ISSUER).payload.body[
                "repository"
            ]
            == identity
        )


@pytest.mark.parametrize("kind", ["zero", "owned", "unowned", "stale", "assertion"])
def test_ref_recovery_and_cas_failure_matrix(tmp_path: Path, kind: str) -> None:
    case = fixture(tmp_path)
    if kind == "zero":
        value = effect(ZERO_OID, case.old, "refs/heads/work/new")
        record = execute_git_effect(case.repo, plan(case.repo, value), issuer=ISSUER)
        assert (
            git(case.repo, "rev-parse", "work/new"),
            record.payload.body["input"]["refs"],
        ) == (
            case.old,
            {"refs/heads/work/new": ZERO_OID},
        )
        return
    if kind in {"owned", "unowned"}:
        carried, update = proof_plan(case), case.effect.updates["refs/heads/dev"]
        if kind == "owned":
            options = {
                "root": case.repo,
                "ref_name": "refs/heads/dev",
                "update": update,
                "operation": "git.ref.compare-and-swap",
                "plan_digest": carried.digest,
            }
            write_ref_intent(**options)
            claim_ref_intent(**options, phase="prepared")
        git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
        if kind == "owned":
            result = execute_git_effect(case.repo, carried, issuer=ISSUER).payload.body["result"]
            assert (result["state"], result["executed"]) == ("recovered", False)
        else:
            reject(
                "git_effect_recovery_intent_missing",
                lambda: execute_git_effect(case.repo, carried, issuer=ISSUER),
            )
        return
    if kind == "stale":
        git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
        value, carried = effect(ZERO_OID, case.old), None
    else:
        git(case.repo, "branch", "candidate/dev", case.old)
        value = GitEffect(
            updates=case.effect.updates, assertions={"refs/heads/candidate/dev": case.old}
        )
        carried = plan(case.repo, value)
        git(case.repo, "update-ref", "refs/heads/candidate/dev", case.new, case.old)
    reject(
        "git_effect_cas_mismatch",
        lambda: execute_git_effect(case.repo, carried or plan(case.repo, value), issuer=ISSUER),
    )


@pytest.mark.parametrize(
    ("state", "binding", "epoch", "recover", "detached"),
    [
        (a, b, 1, r, 0)
        for a, b in [("expired", "expired"), ("unknown", "unknown"), ("valid", "mismatch")]
        for r in (0, 1)
    ]
    + [("valid", "bound", 2, 0, 0), ("valid", "bound", 1, 0, 1)],
)
def test_stale_lease_recovery_and_detached_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    binding: str,
    epoch: int,
    recover: int,
    detached: int,
) -> None:
    case = fixture(tmp_path)
    branch = "work/example" if detached else "dev"
    recorded = generation(case, branch)
    current = recorded | {
        "epoch": epoch,
        "lane_ref": branch,
        "lease_state": state,
        "commitment_binding": binding,
    }
    carried = plan(case.repo, case.effect, values={"lease_generation": recorded})
    monkeypatch.setenv("ETHOS_ACTOR", ISSUER)
    monkeypatch.setattr(admission, "leases_by_branch", lambda *_args, **_kwargs: {branch: current})
    if recover:
        git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
    if detached:
        carried = plan(
            case.repo,
            case.effect,
            values={"lease_generation": lease_generation(current)},
            policy={
                "operation": "git.ref.compare-and-swap",
                "effect_digest": case.effect.digest(),
                "execution_branch": branch,
            },
        )
        original = admission.run_git
        monkeypatch.setattr(
            admission,
            "run_git",
            lambda root, *args, **kwargs: (
                type("R", (), {"stdout": "", "returncode": 0})()
                if args == ("branch", "--show-current")
                else original(root, *args, **kwargs)
            ),
        )
    error = "git_effect_lease_branch_mismatch" if detached else "git_effect_lease_generation_stale"
    reject(error, lambda: execute_git_effect(case.repo, carried, issuer=ISSUER))
    assert git_stdout(case.repo, "rev-parse", "--verify", "refs/heads/dev") == (
        case.new if recover else case.old
    )


def test_only_exact_effect_authority_is_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    monkeypatch.setattr(runtime, "_admit_git_effect", lambda *_args, **_kwargs: None)
    admit_git_effect(case.repo, plan(case.repo, case.effect))
    reject(
        "git_effect_permission_denied",
        lambda: execute_git_effect(
            case.repo,
            plan(case.repo, case.effect, policy={"operation": "test.apply"}),
            issuer=ISSUER,
        ),
    )


@pytest.mark.parametrize("kind", ["commitment", "facts", "policy", "effect", "prestate"])
def test_plan_binding_and_stale_prestate_matrix(tmp_path: Path, kind: str) -> None:
    case = fixture(tmp_path)
    carried = plan(case.repo, case.effect)
    if kind == "prestate":
        commit_fixture_file(case.repo, "DRIFT.md", "drift\n", "drift")
        error = "git_effect_plan_prestate_stale"
    else:
        carried = carried.model_copy(
            update={"inputs": carried.inputs.model_copy(update={kind: ZERO_DIGEST})}
        )
        error = "git_effect_plan_mismatch"
    reject(error, lambda: execute_git_effect(case.repo, carried, issuer=ISSUER))
    assert git_stdout(case.repo, "rev-parse", "--verify", "refs/heads/dev") != case.new


@pytest.mark.parametrize(
    "kind",
    literal_case("mutation.test_git_effect:parametrize:test_attestation_negative_claim_matrix:0"),
)
def test_attestation_negative_claim_matrix(tmp_path: Path, kind: str) -> None:
    case = fixture(tmp_path)
    carried = plan(case.repo, case.effect)
    record = execute_git_effect(case.repo, carried, issuer=ISSUER)
    error = "git_effect_attestation_content_mismatch"
    if kind == "live":
        git(case.repo, "update-ref", "refs/heads/dev", case.old, case.new)
        reject(error, lambda: execute_git_effect(case.repo, carried, issuer=ISSUER))
        return
    if kind.startswith("expired"):
        record = reissue(
            record,
            issued_at=record.issued_at - timedelta(minutes=2),
            valid_from=record.issued_at - timedelta(minutes=2),
            valid_until=record.issued_at - timedelta(minutes=1),
        )
        error = "git_effect_attestation_stale"
        if kind.endswith("drift"):
            git(case.repo, "update-ref", "refs/heads/dev", case.old, case.new)
    elif kind == "checkout":
        git(case.repo, "checkout", "-q", "-b", "side")
        commit_fixture_file(case.repo, "SIDE", "x", "side")
    elif kind == "facts_digest":
        record, error = (
            reissue(record, facts_digest="e" * 64),
            "git_effect_attestation_binding_mismatch:facts_digest",
        )
    elif kind == "unknown":
        record, error = reissue(record, verdict="unknown"), "git_effect_attestation_verdict_unknown"
    elif kind == "issued_at":
        record = reissue(record, issued_at=record.issued_at + timedelta(seconds=1))
    else:
        replacements = {
            "repository": "git:other",
            "command": ("git", "update-ref"),
            "program_sha256": ZERO_DIGEST,
            "result": record.payload.body["result"] | {"exit_code": 7},
            "inputs": {},
            "output_digest": ZERO_DIGEST,
        }
        record = reissue(record, body=record.payload.body | {kind: replacements[kind]})
    reject(error, lambda: records(case.repo, carried, record))


def _effect_failure_runner(
    case: Any,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    saved: list[Attestation],
    first: list[bool],
) -> Any:
    carried = proof_plan(case)

    def fail(record: Attestation | None = None) -> object:
        if first[0] and (failure == "projection" or record is not None):
            first[0] = False
            message = f"{failure} unavailable"
            raise OSError(message)
        if record:
            saved.append(record)
        return tuple(saved)

    if failure == "attestation":
        issue = attest.issue

        def issue_once(*args: object, **kwargs: object) -> Attestation:
            if first[0]:
                first[0] = False
                message = "attestation unavailable"
                raise ValueError(message)
            return issue(*args, **kwargs)

        monkeypatch.setattr(attest, "issue", issue_once)
        return lambda: execute_git_effect(case.repo, carried, issuer=ISSUER)
    if failure == "persistence":
        monkeypatch.setattr(
            attest,
            "records",
            lambda _root, _plan, record=None, **_kwargs: fail(record),
        )
        return lambda: execute_git_effect(case.repo, carried, issuer=ISSUER)
    return lambda: execute_git_effect(case.repo, carried, issuer=ISSUER, projection=fail)


def _inject_postcondition_failure(case: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    observe, failed = runtime.observe_git_effect, [False]

    def stale_once(*args: object, **kwargs: object) -> dict[str, object]:
        result = observe(*args, **kwargs)
        desired = {name: update.desired for name, update in case.effect.updates.items()}
        if not failed[0] and result["refs"] == desired:
            failed[0] = True
            result = {
                **result,
                "refs": {name: update.expected for name, update in case.effect.updates.items()},
            }
        return result

    monkeypatch.setattr(runtime, "observe_git_effect", stale_once)


@pytest.mark.parametrize("failure", ["attestation", "persistence", "projection", "postcondition"])
def test_atomic_compensation_and_retry_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    case = fixture(tmp_path)
    saved, first = [], [True]
    if failure == "postcondition":
        _inject_postcondition_failure(case, monkeypatch)

        def run() -> Any:
            return execute_git_effect(case.repo, proof_plan(case), issuer=ISSUER)

    else:
        run = _effect_failure_runner(case, monkeypatch, failure, saved, first)

    error = (
        "git_effect_postcondition_failed"
        if failure == "postcondition"
        else f"{failure} unavailable"
    )
    reject(error, run)
    assert git(case.repo, "rev-parse", "dev") == case.old
    assert not list(ref_intent_dir(case.repo).glob("*.json"))
    recovered = run()
    assert git(case.repo, "rev-parse", "dev") == case.new
    assert recovered.payload.body["result"]["state"] == "applied"
    assert (saved == [recovered]) if failure == "persistence" else (not saved)
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


def test_execute_ignores_legacy_plan_receipt_when_attestation_set_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = fixture(tmp_path)
    carried = proof_plan(case)
    legacy = attest.issue(
        case.effect,
        plan=carried,
        issuer=ISSUER,
        evidence=(
            f"repository:{case.repo.name}",
            "applied",
            {
                "head": case.old,
                "tree": git(case.repo, "rev-parse", "HEAD^{tree}"),
                "refs": {"refs/heads/dev": case.old},
                "assertions": {},
                "observed_at": "2026-08-01T00:00:00+00:00",
            },
            {
                "head": case.new,
                "tree": git(case.repo, "rev-parse", "HEAD^{tree}"),
                "refs": {"refs/heads/dev": case.new},
                "observed_at": "2026-08-01T00:00:01+00:00",
            },
        ),
    )
    legacy_path = ref_intent_dir(case.repo).parent / "git-effects" / f"{carried.digest}.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(legacy.canonical_json(), encoding="utf-8")
    git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
    monkeypatch.setattr(
        runtime,
        "_apply_git_ref_transaction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy receipt reused")),
    )
    reject(
        "git_effect_recovery_intent_missing",
        lambda: execute_git_effect(case.repo, carried, issuer=ISSUER),
    )


@pytest.mark.parametrize("failure", ["corrupt", "collision"])
def test_attestation_store_public_failure_matrix(tmp_path: Path, failure: str) -> None:
    case = fixture(tmp_path)
    carried = plan(case.repo, case.effect)
    record = execute_git_effect(case.repo, carried, issuer=ISSUER)

    if failure == "corrupt":
        root = git(case.repo, "show-ref", "--verify", "--hash", attestation_set.ATTESTATION_SET_REF)
        git(
            case.repo,
            "update-ref",
            attestation_set.ATTESTATION_SET_REF,
            git(case.repo, "rev-parse", "HEAD"),
            root,
        )
        reject("git_effect_attestation_invalid", lambda: records(case.repo, carried))
    else:
        other = reissue(record, verifier="agent:test:case:other", subject="git-effect:other")
        reject(
            "git_effect_identity_collision",
            lambda: records(case.repo, carried, other),
        )


def test_prepare_failure_aborts_every_claimed_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    value = GitEffect(
        updates={
            ref: GitRefUpdate(expected=ZERO_OID, desired=case.new)
            for ref in ("refs/heads/a", "refs/heads/b")
        }
    )
    claim = runtime.claim_ref_intent
    monkeypatch.setattr(
        runtime,
        "claim_ref_intent",
        lambda **kwargs: (
            {"gap": "forced_prepare_failure"}
            if kwargs["ref_name"] == "refs/heads/b" and kwargs["phase"] == "prepared"
            else claim(**kwargs)
        ),
    )

    reject(
        "git_effect_ref_intent_prepared_forced_prepare_failure",
        lambda: execute_git_effect(case.repo, plan(case.repo, value), issuer=ISSUER),
    )

    assert all(not git_stdout(case.repo, "rev-parse", "--verify", ref) for ref in value.updates)
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


def test_compensation_failure_preserves_exact_recovery_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    carried = proof_plan(case)
    original_run_git = runtime.run_git
    updates = 0

    def fail_reverse(root: Path, *args: str, **kwargs: object) -> object:
        nonlocal updates
        if args == ("update-ref", "--stdin", "-z"):
            updates += 1
            if updates == 2:
                return subprocess.CompletedProcess(args, 1, b"", b"reverse rejected")
        return original_run_git(root, *args, **kwargs)

    monkeypatch.setattr(runtime, "run_git", fail_reverse)
    monkeypatch.setattr(
        attest,
        "issue",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("attestation unavailable")),
    )

    reject(
        "git_effect_partial_effect_uncompensated:refs/heads/dev"
        f":expected={case.old}:observed={case.new}",
        lambda: execute_git_effect(case.repo, carried, issuer=ISSUER),
    )

    assert git(case.repo, "rev-parse", "dev") == case.new
    intents = list(ref_intent_dir(case.repo).glob("*.json"))
    assert len(intents) == 1
    assert '"phase":"committed"' in intents[0].read_text(encoding="utf-8")

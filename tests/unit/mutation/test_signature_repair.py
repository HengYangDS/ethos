"""Native signature-repair admission, recovery and selected-ref invariants."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock

import ethos.adapters.mutation.accepted.signature as repair
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.ref_move_policy import signature_repair_ref_report
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit.signature import signature_plan
from ethos.adapters.repo.git_object import commit_payload
from ethos.adapters.repo.git_object import verify_commit_trust
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import render_branch_policy
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path, *, coupled: bool = False) -> tuple[Path, str, Path]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "signature-fixture"\n')
    (repo / ".ethos/workspace.toml").write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="accepted_ff" if coupled else "independent",
        )
        + '\n[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        + 'signing_required = true\nsigning_format = "ssh"\n'
    )
    git(repo, "add", ".ethos")
    git(repo, "commit", "-m", "fix: accepted signing policy")
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate/dev", old)
    git(repo, "branch", "main", old)
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", str(candidate), "candidate/dev")
    executable = shutil.which("ssh-keygen")
    assert executable is not None
    key = tmp_path / "signer"
    subprocess.run(
        (executable, "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    trust = tmp_path / "trust"
    trust.mkdir(mode=0o700)
    anchor = trust / "allowed-signers"
    public = key.with_suffix(".pub").read_text()
    anchor.write_text(f'test@example.invalid namespaces="git" {public}')
    anchor.chmod(0o600)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", executable),
        ("user.signingkey", str(key.with_suffix(".pub"))),
        ("gpg.ssh.allowedSignersFile", str(anchor)),
    ):
        git(repo, "config", name, value)
    return repo, old, candidate


@pytest.mark.parametrize("coupled", [False, True])
def test_repair_has_readonly_readiness_and_exact_selected_effects(tmp_path, monkeypatch, coupled):
    repo, old, candidate = _repository(tmp_path, coupled=coupled)
    before = git(repo, "show-ref"), read_attestation_set(repo), (repo / ".git/index").read_bytes()
    ready = repair.repair_signature(root=repo, expect_head=old)
    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_repair")
    assert (
        git(repo, "show-ref"),
        read_attestation_set(repo),
        (repo / ".git/index").read_bytes(),
    ) == before

    applied = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)

    assert (applied["verdict"], applied["state"]) == ("pass", "signature_repaired")
    new = applied["head"]
    assert isinstance(new, str)
    assert new != old
    assert commit_payload(repo, old) == commit_payload(repo, new)
    assert verify_commit_trust(repo, new)["verdict"] == "pass"
    assert git(repo, "rev-parse", "dev") == git(candidate, "rev-parse", "HEAD") == new
    assert git(repo, "rev-parse", "main") == (new if coupled else old)
    assert str(applied["next_action"]).endswith(f"--expect-head {new} --json")
    monkeypatch.setattr(
        repair, "create_signed_replacement", lambda *_a: pytest.fail("must not repeat signing")
    )
    replay = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert replay["state"] == "signature_repaired"
    assert replay["head"] == new


@pytest.mark.parametrize("case", ["unauthorized", "dirty", "wrong-head", "wrong-actor"])
def test_repair_rejects_before_signing(tmp_path, monkeypatch, case):
    repo, old, _candidate = _repository(tmp_path)
    if case == "dirty":
        (repo / "README.md").write_text("unaccepted\n")
    if case == "wrong-actor":
        monkeypatch.delenv("ETHOS_ACTOR")
    monkeypatch.setattr(repair, "create_signed_replacement", lambda *_a: pytest.fail("signed"))
    result = repair.repair_signature(
        root=repo,
        expect_head="0" * 40 if case == "wrong-head" else old,
        apply=True,
        authorized=case != "unauthorized",
    )
    assert result["verdict"] == "block"
    assert git(repo, "rev-parse", "dev") == old


def test_repair_passes_installed_hooks_without_candidate_at_replacement(tmp_path):
    repo, old, candidate = _repository(tmp_path, coupled=True)
    install_fixture_hook_runtime(repo)
    result = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert (result["verdict"], result["state"]) == ("pass", "signature_repaired"), result
    assert git(repo, "rev-parse", "dev") == git(candidate, "rev-parse", "HEAD") == result["head"]


def test_repair_keeps_unrelated_candidate_and_independent_release(tmp_path):
    repo, old, candidate = _repository(tmp_path)
    (candidate / "README.md").write_text("candidate work\n")
    git(candidate, "add", "README.md")
    git(candidate, "commit", "-m", "fix: independent candidate")
    other = git(candidate, "rev-parse", "HEAD")
    result = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert result["state"] == "signature_repaired"
    assert git(candidate, "rev-parse", "HEAD") == other
    assert git(repo, "rev-parse", "main") == old


@pytest.mark.parametrize("accepted_branch", ["dev", "integration"])
def test_repair_supports_local_only_without_candidate_or_release_refs(tmp_path, accepted_branch):
    repo, old, candidate = _repository(tmp_path)
    git(repo, "worktree", "remove", str(candidate))
    git(repo, "branch", "-D", "candidate/dev", "main")
    if accepted_branch != "dev":
        policy = repo / ".ethos/workspace.toml"
        policy.write_text(
            policy.read_text().replace('accepted_branch = "dev"', 'accepted_branch = "integration"')
        )
        git(repo, "add", ".ethos/workspace.toml")
        git(repo, "commit", "-m", "fix: declare integration role")
        git(repo, "branch", "-m", "integration")
        old = git(repo, "rev-parse", "HEAD")
    result = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert result["state"] == "signature_repaired", result
    assert git(repo, "for-each-ref", "--format=%(refname)", "refs/heads") == (
        f"refs/heads/{accepted_branch}"
    )
    assert git(repo, "remote") == ""


def test_repair_rejects_unsolicited_replacement_before_any_attempt(tmp_path):
    repo, old, _candidate = _repository(tmp_path)
    new = repair.create_signed_replacement(repo, old)
    before = git(repo, "show-ref")
    ready = repair.repair_signature(root=repo, expect_head=old, replacement=new)
    applied = repair.repair_signature(
        root=repo,
        expect_head=old,
        replacement=new,
        apply=True,
        authorized=True,
    )
    for observed in (ready, applied):
        assert observed["verdict"] == "block", observed
        assert observed["required_gaps"] == ["signature_repair_replacement_without_attempt"]
    assert git(repo, "show-ref") == before


@pytest.mark.parametrize("failure", ["result-write", "after-cas", "worktree-observation"])
def test_repair_recovers_observed_results_without_repeating_effects(tmp_path, monkeypatch, failure):
    repo, old, _candidate = _repository(tmp_path)
    signed = []
    native_sign = repair.create_signed_replacement

    def sign(*args):
        signed.append(native_sign(*args))
        return signed[-1]

    monkeypatch.setattr(repair, "create_signed_replacement", sign)
    target = (
        "record_attestations"
        if failure == "result-write"
        else ("execute_git_effect" if failure == "after-cas" else "sync_ref_worktrees")
    )
    native = getattr(repair, target)
    failed = False

    def interrupt(*args, **kwargs):
        nonlocal failed
        if failed:
            return native(*args, **kwargs)
        if failure == "after-cas":
            native(*args, **kwargs)
        failed = True
        error = "injected acknowledgement loss"
        raise OSError(error)

    monkeypatch.setattr(repair, target, interrupt)
    first = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert first["verdict"] != "pass"
    assert len(signed) == 1
    assert first["replacement"] == signed[0]
    effects = first["effects"]
    assert isinstance(effects, dict)
    assert effects["signed_object"] == "observed"
    assert effects["selected_refs"] == ("pending" if failure == "result-write" else "observed")
    assert all(
        item["state"] == ("pending" if failure == "result-write" else "observed")
        for item in effects["worktrees"]
    )
    monkeypatch.setattr(repair, target, native)
    result = repair.repair_signature(
        root=repo,
        expect_head=old,
        apply=True,
        authorized=True,
        replacement=signed[0] if failure == "result-write" else "",
    )
    assert (result["verdict"], result["state"]) == ("pass", "signature_repaired")
    assert len(signed) == 1


def test_public_signature_repair_has_exact_apply_and_reproof_commands(tmp_path):
    repo, old, _candidate = _repository(tmp_path)
    ready = run_ethos("lane", "repair-signature", "--expect-head", old, "--json", cwd=repo)
    assert ready["state"] == "ready_to_repair"
    denied = run_ethos_blocked(
        "lane", "repair-signature", "--expect-head", old, "--apply", "--json", cwd=repo
    )
    assert denied["required_gaps"] == ["authorization_required"]
    done = run_ethos(
        "lane",
        "repair-signature",
        "--expect-head",
        old,
        "--apply",
        "--authorize",
        "--json",
        cwd=repo,
    )
    assert done["state"] == "signature_repaired"
    assert git(repo, "rev-parse", "HEAD") in done["next_action"]


def _interrupted_signature(repo, old, monkeypatch):
    """Stop at the real effect boundary after durable signing evidence exists."""

    def interrupt(*_args, **_kwargs):
        error = "injected before ref CAS"
        raise OSError(error)

    with monkeypatch.context() as scope:
        scope.setattr(repair, "execute_git_effect", interrupt)
        observed = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert observed["verdict"] != "pass"
    _, records = read_attestation_set(repo)
    return records


def test_signature_plan_is_stable_after_canonical_record_roundtrip(tmp_path):
    repo, old, _candidate = _repository(tmp_path)
    ready = repair.repair_signature(root=repo, expect_head=old)
    new = repair.create_signed_replacement(repo, old)
    coordinates = ready["coordinates"]
    assert isinstance(coordinates, dict)
    original = signature_plan(repo, coordinates, new)
    recovered = signature_plan(repo, json.loads(json.dumps(coordinates, sort_keys=True)), new)
    assert original.model_dump(mode="json") == recovered.model_dump(mode="json")


@pytest.mark.parametrize("boundary", ["public", "hook"])
@pytest.mark.parametrize("field", ["repository", "policy_sha256", "payload_sha256", "plan"])
def test_repair_rejects_reissued_evidence_at_both_effect_boundaries(
    tmp_path, monkeypatch, boundary, field
):
    repo, old, _candidate = _repository(tmp_path)
    records = _interrupted_signature(repo, old, monkeypatch)
    altered = []
    for item in records:
        value = item.model_dump(mode="json", exclude={"id"})
        body = value["payload"]["body"]
        if field == "plan":
            if item.predicate == "effect:commit-signature":
                body["plan"]["facts"]["head"] = "0" * 40
        else:
            body["coordinates"][field] = "0" * 64
            digest = canonical_json_digest(body["coordinates"])
            value.update(subject=f"signature-repair:{digest}", facts_digest=digest)
            value["policy_digest"] = body["coordinates"]["policy_sha256"]
        altered.append(Attestation.issue(value))
    # Corrupt only this isolated native repository's selected evidence, not production state.
    git(repo, "update-ref", "-d", ATTESTATION_SET_REF)
    record_attestations(repo, tuple(altered))
    before = git(repo, "show-ref"), (repo / ".git/index").read_bytes()
    if boundary == "public":
        observed = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    else:
        result = next(item for item in altered if item.predicate == "effect:commit-signature")
        new = result.payload.body["replacement"]
        assert result.plan_digest is not None
        write_ref_intent(
            root=repo,
            ref_name="refs/heads/dev",
            update=GitRefUpdate(expected=old, desired=new),
            operation="commit.identity-replace",
            plan_digest=result.plan_digest,
        )
        observed = signature_repair_ref_report(repo, "refs/heads/dev", old, new)
    assert observed is not None
    assert observed["verdict"] == "block", observed
    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes()) == before


def test_repair_unknown_signing_is_observable_and_cannot_restart_with_another_actor(
    tmp_path, monkeypatch
):
    repo, old, _candidate = _repository(tmp_path)

    def interrupt(*_args, **_kwargs):
        error = "injected signing result loss"
        raise OSError(error)

    with monkeypatch.context() as scope:
        scope.setattr(repair, "create_signed_replacement", interrupt)
        first = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert first["verdict"] == "unknown"
    before = git(repo, "show-ref")
    ready = repair.repair_signature(root=repo, expect_head=old)
    assert ready["verdict"] == "unknown", ready
    assert ready["required_gaps"] == ["signature_repair_signing_outcome_unknown"]
    monkeypatch.setenv("ETHOS_ACTOR", "another-authorized-maintainer")
    denied = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert denied["verdict"] == "block", denied
    assert denied["required_gaps"] == ["signature_repair_actor_mismatch"]
    assert git(repo, "show-ref") == before


@pytest.mark.parametrize("coordinates", [None, "malformed", [], {"root": "missing-fields"}])
def test_repair_malformed_evidence_is_a_structured_rejection(tmp_path, monkeypatch, coordinates):
    repo, old, _candidate = _repository(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "fixture")
    now = datetime.now(UTC)
    record_attestations(
        repo,
        (
            Attestation.issue(
                {
                    "schema_version": 2,
                    "predicate": "observation:signature-repair-attempt",
                    "verifier": "fixture",
                    "subject": "signature-repair:malformed",
                    "issued_at": now,
                    "valid_from": now,
                    "valid_until": None,
                    "verdict": "pass",
                    "payload": {
                        "kind": "observation:signature-repair-attempt",
                        "body": {
                            "coordinates": coordinates,
                        },
                    },
                    "relations": (),
                    "advisories": (),
                    "evidence_refs": (),
                    "commitment_digest": None,
                    "facts_digest": "0" * 64,
                    "plan_digest": None,
                    "policy_digest": None,
                    "effect_digest": None,
                    "mints_authority": False,
                }
            ),
        ),
    )
    observed = repair.repair_signature(root=repo, expect_head=old)
    assert observed["verdict"] == "block", observed
    assert observed["required_gaps"] == ["signature_repair_evidence_invalid"]


@pytest.mark.parametrize("boundary", ["public", "hook"])
@pytest.mark.parametrize("change", ["dirty-worktree", "omitted-worktree", "unselected-ref"])
def test_repair_rejects_fresh_worktree_or_recompiled_scope_drift(
    tmp_path, monkeypatch, boundary, change
):
    repo, old, candidate = _repository(tmp_path)
    records = _interrupted_signature(repo, old, monkeypatch)
    if change == "dirty-worktree":
        (candidate / "README.md").write_text("unaccepted change\n")
    else:
        altered = []
        for item in records:
            value = item.model_dump(mode="json", exclude={"id"})
            body = value["payload"]["body"]
            if change == "omitted-worktree":
                body["coordinates"]["worktrees"] = []
            else:
                body["coordinates"]["refs"]["refs/heads/main"] = old
            digest = canonical_json_digest(body["coordinates"])
            value.update(subject=f"signature-repair:{digest}", facts_digest=digest)
            if item.predicate == "effect:commit-signature":
                plan = signature_plan(repo, body["coordinates"], body["replacement"])
                body.update(plan=plan.model_dump(mode="json"), plan_digest=plan.digest)
                value["plan_digest"] = plan.digest
            altered.append(Attestation.issue(value))
        git(repo, "update-ref", "-d", ATTESTATION_SET_REF)
        record_attestations(repo, tuple(altered))
        records = tuple(altered)
    before = git(repo, "show-ref"), (candidate / "README.md").read_bytes()
    if boundary == "public":
        observed = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    else:
        result = next(item for item in records if item.predicate == "effect:commit-signature")
        assert result.plan_digest is not None
        new = result.payload.body["replacement"]
        write_ref_intent(
            root=repo,
            ref_name="refs/heads/dev",
            update=GitRefUpdate(expected=old, desired=new),
            operation="commit.identity-replace",
            plan_digest=result.plan_digest,
        )
        observed = signature_repair_ref_report(repo, "refs/heads/dev", old, new)
    assert observed is not None
    assert observed["verdict"] == "block", observed
    assert (git(repo, "show-ref"), (candidate / "README.md").read_bytes()) == before


def test_repair_lock_contention_is_waiting_not_an_unknown_effect(tmp_path):
    repo, old, _candidate = _repository(tmp_path)
    lock = local_state_root(repo) / "signature-repair.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    before = git(repo, "show-ref")
    with FileLock(str(lock)):
        result = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert result["verdict"] == "block"
    assert result["state"] == "waiting"
    assert result["required_gaps"] == ["signature_repair_in_progress"]
    assert git(repo, "show-ref") == before


def test_repair_known_invalid_signer_is_blocked_and_preserves_created_object(tmp_path):
    repo, old, _candidate = _repository(tmp_path)
    (tmp_path / "trust/allowed-signers").write_text("")
    result = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert result["verdict"] == "block", result
    assert result["required_gaps"] == ["commit_signature_untrusted"]
    effects = result["effects"]
    assert isinstance(effects, dict)
    assert effects["signed_object"] == "observed"
    assert effects["selected_refs"] == "pending"
    assert git(repo, "rev-parse", "HEAD") == old
    assert git(repo, "cat-file", "-t", str(result["replacement"])) == "commit"


@pytest.mark.parametrize("boundary", ["signing", "cas"])
def test_repair_recovers_after_actual_child_exit_without_resigning(tmp_path, monkeypatch, boundary):
    repo, old, _candidate = _repository(tmp_path)
    code = """
import os, sys
from pathlib import Path
import ethos.adapters.mutation.accepted.signature as repair
boundary = sys.argv[3]
target = "create_signed_replacement" if boundary == "signing" else "execute_git_effect"
native = getattr(repair, target)
def exit_after_native(*args, **kwargs):
    result = native(*args, **kwargs)
    if boundary == "signing":
        print(result, flush=True)
    os._exit(79)
setattr(repair, target, exit_after_native)
repair.repair_signature(
    root=Path(sys.argv[1]), expect_head=sys.argv[2], apply=True, authorized=True,
)
"""
    child = subprocess.run(
        [sys.executable, "-B", "-c", code, str(repo), old, boundary],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert child.returncode == 79, child.stderr
    replacement = child.stdout.strip() if boundary == "signing" else ""
    if boundary == "signing":
        observed = repair.repair_signature(root=repo, expect_head=old)
        assert observed["verdict"] == "unknown"
        assert git(repo, "rev-parse", "dev") == old
    else:
        assert git(repo, "rev-parse", "dev") != old
    monkeypatch.setattr(repair, "create_signed_replacement", lambda *_a: pytest.fail("resigned"))
    result = repair.repair_signature(
        root=repo,
        expect_head=old,
        replacement=replacement,
        apply=True,
        authorized=True,
    )
    assert result["state"] == "signature_repaired", result
    assert commit_payload(repo, old) == commit_payload(repo, str(result["head"]))

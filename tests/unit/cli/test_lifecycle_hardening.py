from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.mutation.lane_lifecycle.identity_repair as identity_repair
import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as work_lane_refresh
import ethos.adapters.openspec.profile as openspec_profile
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.openspec.start_effect import CurrentGenerationScope
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import issue_conformant_proof
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_work_lane


def test_work_lane_commitment_never_falls_back_from_an_invalid_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_lease(*_args: object, **_kwargs: object) -> None:
        message = "lease_expected_tree_mismatch"
        raise ValueError(message)

    monkeypatch.setattr(openspec_profile, "load_lease_bound_commitment", invalid_lease)
    monkeypatch.setattr(
        openspec_profile,
        "load_profile_commitment",
        lambda *_args, **_kwargs: pytest.fail("invalid Lease must stop carrier selection"),
    )

    with pytest.raises(ValueError, match="lease_expected_tree_mismatch"):
        openspec_profile.load_work_lane_commitment(tmp_path, lease={})


def _diverged_candidate_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    old_candidate_head = commit_fixture_file(
        candidate, "CANDIDATE.md", "# CANDIDATE.md\n", "advance candidate"
    )
    accepted_head = commit_fixture_file(repo, "ACCEPTED.md", "# ACCEPTED.md\n", "advance accepted")
    return repo, candidate, accepted_head, old_candidate_head


def _refresh_arguments(head: str) -> tuple[str, ...]:
    return (
        "lane",
        "candidate",
        "--refresh-from-accepted",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
    )


def _fail_once(monkeypatch, target, name: str, message: str):
    original = getattr(target, name)
    failed = False

    def injected(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError(message)
        return original(*args, **kwargs)

    monkeypatch.setattr(target, name, injected)


@pytest.mark.parametrize(
    ("target", "name", "message", "effect_persisted"),
    [
        (candidate_projection, "sync_ref_worktrees", "injected post-CAS failure", False),
        (git_effects, "_clear_claimed_intents", "injected post-projection failure", True),
    ],
)
def test_lane_candidate_refresh_recovers_after_interrupted_projection(
    tmp_path: Path, monkeypatch, target, name: str, message: str, effect_persisted
) -> None:
    repo, candidate, accepted_head, old_candidate_head = _diverged_candidate_repo(tmp_path)
    _fail_once(monkeypatch, target, name, message)
    arguments = _refresh_arguments(accepted_head)
    failed_report = run_ethos_blocked(*arguments, cwd=repo)
    assert bool(list(ref_intent_dir(repo).glob("*.json"))) is effect_persisted
    assert git(repo, "rev-parse", "candidate/dev") == (
        accepted_head if effect_persisted else old_candidate_head
    )
    recovered = run_ethos(*arguments, cwd=repo)
    assert failed_report["required_gaps"] == ["candidate_refresh_from_accepted_failed"]
    assert failed_report["data"]["previous_head"] == old_candidate_head
    assert recovered["state"] == "refreshed_from_accepted"
    assert git(candidate, "rev-parse", "HEAD") == accepted_head
    assert git(candidate, "status", "--short") == ""
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_lane_candidate_bootstrap_recovers_after_worktree_creation_precedes_intent_clear(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    candidate = tmp_path / "repo-candidate-dev"
    arguments = (
        "lane",
        "candidate",
        "--apply",
        "--path",
        candidate.as_posix(),
        "--expect-head",
        head,
        "--json",
    )
    _fail_once(monkeypatch, git_effects, "_clear_claimed_intents", "injected intent clear failure")

    assert run_ethos_blocked(*arguments, cwd=repo)["required_gaps"] == [
        "candidate_worktree_add_failed"
    ]
    recovered = run_ethos(*arguments, cwd=repo)

    assert recovered["state"] == "present"
    assert hook_runtime_binding(candidate)["required_gaps"] == []
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_lane_refresh_recovers_after_ref_cas_precedes_branch_attachment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    previous = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    failed = False
    branch_was_advanced = False

    original = work_lane_refresh.attach_worktree

    def fail_first_attachment(root, path, *, branch, head):
        nonlocal branch_was_advanced, failed
        if branch == "work/feature" and not failed:
            failed = True
            branch_was_advanced = git(root, "rev-parse", "work/feature") == git(
                root, "rev-parse", "HEAD"
            )
            msg = "injected post-CAS attachment failure"
            raise OSError(msg)
        return original(root, path, branch=branch, head=head)

    monkeypatch.setattr(work_lane_refresh, "attach_worktree", fail_first_attachment)
    arguments = (
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous,
        "--json",
    )

    blocked = run_ethos_blocked(*arguments, cwd=worktree)
    recovered = run_ethos(*arguments, cwd=worktree)
    assert branch_was_advanced
    assert blocked["required_gaps"] == ["refresh_base_worktree_attach_failed"]
    assert recovered["state"] == "base_refreshed"
    assert git(worktree, "branch", "--show-current") == "work/feature"
    assert not list(ref_intent_dir(worktree).glob("*.json"))


def test_lane_refresh_restores_original_branch_when_ref_cas_is_rejected_after_rebase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    previous = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    def reject_effect(*_args: object, **_kwargs: object) -> None:
        message = "git_effect_lease_generation_stale"
        raise ValueError(message)

    monkeypatch.setattr(work_lane_refresh, "execute_git_effect", reject_effect)

    payload = run_ethos_blocked(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous,
        "--json",
        cwd=worktree,
    )

    assert payload["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]
    assert payload["data"]["stderr"] == "git_effect_lease_generation_stale"
    assert git(worktree, "branch", "--show-current") == "work/feature"
    assert git(worktree, "rev-parse", "HEAD") == previous
    assert git(worktree, "rev-parse", "work/feature") == previous
    assert git(worktree, "status", "--short") == ""


def test_repair_identity_derives_and_applies_existing_equivalent_oid_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    git(candidate, "reset", "--hard", old)
    git(repo, "reset", "--hard", old)
    git(repo, "update-ref", "refs/heads/main", old)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    new = _replace_commit_signature(worktree, old)
    scope = CurrentGenerationScope(("FEATURE.md",), {})
    plan = proof_plan(worktree, head=new, generation_scope=scope)
    persist_proof_attestation(worktree, issue_conformant_proof(worktree, new, plan=plan))
    monkeypatch.setattr(identity_repair, "verify_commit_trust", _trusted_commit)

    derived = identity_repair.derive_identity_repair_suffix(
        root=worktree,
        base_commit=old,
    )
    assert derived["verdict"] == "pass", derived
    commits = derived["request"]["commits"]
    assert len(commits) == 1
    assert commits[0] | {
        "message_sha256": "ignored",
        "author_name": "ignored",
        "author_email": "ignored",
        "author_date": "ignored",
        "committer_name": "ignored",
        "committer_email": "ignored",
        "committer_date": "ignored",
    } == {
        "old_commit": old,
        "new_commit": new,
        "old_parent": git(worktree, "rev-parse", f"{old}^"),
        "new_parent": git(worktree, "rev-parse", f"{new}^"),
        "tree": git(worktree, "rev-parse", f"{old}^{{tree}}"),
        "message_sha256": "ignored",
        "author_name": "ignored",
        "author_email": "ignored",
        "author_date": "ignored",
        "committer_name": "ignored",
        "committer_email": "ignored",
        "committer_date": "ignored",
    }
    receipt = derived["receipt"]
    applied = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert applied["state"] == "identity_repaired"
    assert git(candidate, "rev-parse", "HEAD") == new
    assert git(repo, "rev-parse", "HEAD") == new
    assert git(candidate, "status", "--short") == git(repo, "status", "--short") == ""


def test_repair_identity_derives_one_exact_linear_suffix_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, candidate, worktree, base, accepted, head = _identity_repair_suffix_fixture(
        tmp_path, monkeypatch
    )
    del repo, candidate

    report = identity_repair.derive_identity_repair_suffix(
        root=worktree,
        base_commit=base,
    )

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "derived",
        [],
    )
    assert [item["old_commit"] for item in report["request"]["commits"]] == [
        accepted,
        head,
    ]
    assert report["request"]["refs"] == {
        "refs/heads/candidate/dev": {
            "expected": accepted,
            "desired": report["request"]["commits"][0]["new_commit"],
        },
        "refs/heads/dev": {
            "expected": accepted,
            "desired": report["request"]["commits"][0]["new_commit"],
        },
        "refs/heads/main": {
            "expected": accepted,
            "desired": report["request"]["commits"][0]["new_commit"],
        },
        "refs/heads/work/feature": {
            "expected": head,
            "desired": report["request"]["commits"][1]["new_commit"],
        },
    }
    assert report["receipt"]["path"].endswith(".json")
    assert report["next_action"].startswith("ethos lane repair-identity --receipt ")


def test_repair_identity_applies_one_exact_linear_suffix_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, candidate, worktree, base, _accepted, _head = _identity_repair_suffix_fixture(
        tmp_path, monkeypatch
    )
    derived = identity_repair.derive_identity_repair_suffix(
        root=worktree,
        base_commit=base,
    )

    report = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(derived["receipt"]["path"]),
        receipt_sha256=str(derived["receipt"]["sha256"]),
        apply=True,
        authorized=True,
    )

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "identity_repaired",
        [],
    )
    expected = derived["request"]["refs"]
    assert {ref: git(repo, "rev-parse", ref) for ref in expected} == {
        ref: update["desired"] for ref, update in expected.items()
    }
    assert git(candidate, "status", "--short") == git(worktree, "status", "--short") == ""
    assert all(
        git(repo, "verify-commit", item["new_commit"]) == ""
        for item in derived["request"]["commits"]
    )


def test_repair_identity_resumes_same_suffix_receipt_after_worktree_sync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, candidate, worktree, base, _accepted, _head = _identity_repair_suffix_fixture(
        tmp_path, monkeypatch
    )
    derived = identity_repair.derive_identity_repair_suffix(
        root=worktree,
        base_commit=base,
    )
    receipt = derived["receipt"]
    expected = derived["request"]["refs"]
    original = identity_repair.sync_ref_worktrees
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"worktree_sync": "failed", "worktrees": []}
        return original(*args, **kwargs)

    monkeypatch.setattr(identity_repair, "sync_ref_worktrees", fail_once)

    first = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert first["required_gaps"] == ["identity_repair_worktree_sync_failed"]
    assert {ref: git(repo, "rev-parse", ref) for ref in expected} == {
        ref: update["desired"] for ref, update in expected.items()
    }

    resumed = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert (resumed["verdict"], resumed["state"], resumed["required_gaps"]) == (
        "pass",
        "identity_repaired",
        [],
    ), resumed
    assert git(candidate, "status", "--short") == git(worktree, "status", "--short") == ""


def test_repair_identity_suffix_receipt_rejects_actor_ref_and_trust_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _candidate, worktree, base, accepted, _head = _identity_repair_suffix_fixture(
        tmp_path, monkeypatch
    )
    derived = identity_repair.derive_identity_repair_suffix(root=worktree, base_commit=base)
    receipt = derived["receipt"]

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    actor = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )
    assert actor["required_gaps"] == ["identity_repair_actor_mismatch"]

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    git(repo, "-c", "core.hooksPath=/dev/null", "update-ref", "refs/heads/main", base, accepted)
    stale_ref = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )
    assert any(
        gap.startswith("identity_repair_ref_stale:refs/heads/main:")
        for gap in stale_ref["required_gaps"]
    )

    git(repo, "-c", "core.hooksPath=/dev/null", "update-ref", "refs/heads/main", accepted, base)
    git(repo, "config", "gpg.ssh.allowedSignersFile", (tmp_path / "missing-anchor").as_posix())
    untrusted = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )
    assert any(
        gap.endswith(f"trust_drift:{item['old_commit']}")
        for gap in untrusted["required_gaps"]
        for item in derived["request"]["commits"]
    )


def test_repair_identity_suffix_receipt_rejects_tampered_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo, _candidate, worktree, base, _accepted, _head = _identity_repair_suffix_fixture(
        tmp_path, monkeypatch
    )
    derived = identity_repair.derive_identity_repair_suffix(root=worktree, base_commit=base)
    receipt = derived["receipt"]
    path = Path(str(receipt["path"]))
    path.write_bytes(path.read_bytes() + b"\n")

    report = identity_repair.execute_identity_repair_suffix(
        root=worktree,
        receipt_path=path.as_posix(),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert report["required_gaps"] == ["identity_repair_receipt_sha256_mismatch"]


def test_repair_identity_suffix_rejects_merge_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    base = git(repo, "rev-parse", "HEAD")
    left = git(repo, "commit-tree", "HEAD^{tree}", "-p", base, "-m", "left")
    right = git(repo, "commit-tree", "HEAD^{tree}", "-p", base, "-m", "right")
    merge = git(repo, "commit-tree", "HEAD^{tree}", "-p", left, "-p", right, "-m", "merge")
    owner = "agent:test:case:owner"
    tree = git(repo, "rev-parse", f"{merge}^{{tree}}")
    monkeypatch.setenv("ETHOS_ACTOR", owner)
    monkeypatch.setattr(
        identity_repair,
        "workspace_status",
        lambda *_args, **_kwargs: {
            "role": "work_lane",
            "dirty": False,
            "branch": "work/test",
        },
    )
    monkeypatch.setattr(identity_repair, "current_tracked_head", lambda _root: merge)
    monkeypatch.setattr(
        identity_repair,
        "leases_by_branch",
        lambda _root: {
            "work/test": {
                "lease_state": "valid",
                "holder_ref": owner,
                "expected_head": merge,
                "expected_tree": tree,
            }
        },
    )
    monkeypatch.setattr(identity_repair, "proof_attestation", lambda *_args: object())

    report = identity_repair.derive_identity_repair_suffix(root=repo, base_commit=base)

    assert any(
        gap.startswith("identity_repair_suffix_not_linear:") for gap in report["required_gaps"]
    )


def test_repair_identity_public_cli_derives_and_applies_suffix_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _candidate, worktree, base, _accepted, _head = _identity_repair_suffix_fixture(
        tmp_path, monkeypatch
    )

    derived = run_ethos(
        "lane",
        "repair-identity",
        "derive",
        "--base-commit",
        base,
        "--json",
        cwd=worktree,
    )
    receipt = derived["data"]["receipt"]
    applied = run_ethos(
        "lane",
        "repair-identity",
        "--receipt",
        receipt["path"],
        "--receipt-sha256",
        receipt["sha256"],
        "--apply",
        "--authorize",
        "--json",
        cwd=worktree,
    )

    assert applied["state"] == "identity_repaired"
    assert git(repo, "rev-parse", "work/feature") == applied["data"]["new_head"]


def _identity_repair_suffix_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, str, str, str]:
    repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    base = git(worktree, "rev-parse", "HEAD")
    accepted = commit_fixture_file(worktree, "FIRST.md", "first\n", "feat: first unsigned")
    head = commit_fixture_file(worktree, "SECOND.md", "second\n", "feat: second unsigned")
    git(candidate, "reset", "--hard", accepted)
    git(repo, "reset", "--hard", accepted)
    git(repo, "update-ref", "refs/heads/main", accepted)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    signing_key = tmp_path / "suffix-signing-key"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(signing_key)),
        check=True,
        capture_output=True,
        text=True,
    )
    public_key = signing_key.with_suffix(".pub")
    anchor = tmp_path / "suffix-allowed-signers"
    anchor.write_text(
        f'test@example.com namespaces="git" {public_key.read_text(encoding="utf-8").strip()}\n',
        encoding="utf-8",
    )
    anchor.chmod(0o600)
    git(repo, "config", "commit.gpgsign", "true")
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "gpg.ssh.program", "/usr/bin/ssh-keygen")
    git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    git(repo, "config", "user.signingkey", public_key.as_posix())
    scope = CurrentGenerationScope(("FIRST.md", "SECOND.md"), {})
    plan = proof_plan(worktree, head=head, generation_scope=scope)
    persist_proof_attestation(worktree, issue_conformant_proof(worktree, head, plan=plan))
    return repo, candidate, worktree, base, accepted, head


def _trusted_commit(_root: Path, revision: str) -> dict[str, object]:
    return {
        "verdict": "pass",
        "revision": revision,
        "anchor": "/protected/allowed-signers",
        "required_gaps": [],
    }


def _replace_commit_signature(worktree: Path, old: str) -> str:
    raw = git(worktree, "cat-file", "commit", old)
    signed = raw.replace(
        "\n\nfeature work",
        "\ngpgsig -----BEGIN SSH SIGNATURE-----\n synthetic\n "
        "-----END SSH SIGNATURE-----\n\nfeature work",
    )
    new = subprocess.run(
        ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
        cwd=worktree,
        input=f"{signed}\n",
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    git(worktree, "update-ref", "refs/heads/work/feature", new, old)
    git(worktree, "reset", "--hard", new)
    report = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name="refs/heads/work/feature",
        old_value=old,
        new_value=new,
    )
    assert report["state"] == "lease_ref_advanced"
    return new


def test_land_closeout_reports_actionable_candidate_divergence(tmp_path: Path) -> None:
    repo, _candidate, accepted_head, _old_candidate_head = _diverged_candidate_repo(tmp_path)
    seed_executed_proof(repo, accepted_head)

    payload = run_ethos_blocked(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["required_gaps"] == ["candidate_diverged_from_accepted"]
    assert payload["next_action"] == (
        "ethos lane candidate --refresh-from-accepted --apply --authorize "
        f"--expect-head {accepted_head} --json"
    )
    assert payload["continuation"] == "await-user"
    assert payload["user_decision_required"] is True

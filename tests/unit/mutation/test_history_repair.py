"""Public native history-repair integration preserves originals and rejects drift."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC
from datetime import datetime

import pytest

import ethos.adapters.mutation.accepted.signature as repair
import ethos.adapters.repo.commit.history as history
from ethos.adapters.admission.publication import ref_update_admission_report
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.commit.signature import signature_coordinates
from ethos.adapters.repo.commit.signature import signature_plan
from ethos.adapters.repo.git_effect_attestation import issue as issue_git_effect
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.semantic import canonical_utc_time
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.proof import seed_executed_proof
from tests.support.signature import configure_signer
from tests.support.signature import signature_repository


def test_public_repair_corrects_selected_history_with_originals_and_replay(tmp_path):
    repo, _initial, candidate = signature_repository(tmp_path, coupled=True)
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    initial = git(repo, "rev-parse", "HEAD")
    wrong = subprocess.run(
        ("git", "commit-tree", tree, "-p", initial, "-m", "fix: wrong attribution"),
        cwd=repo,
        env={**os.environ, "GIT_AUTHOR_NAME": "Wrong"},
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    old = git(repo, "commit-tree", tree, "-p", wrong, "-m", "fix: descendant")
    for branch in ("dev", "candidate/dev", "main"):
        git(repo, "update-ref", f"refs/heads/{branch}", old)
    bundle = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(bundle), "refs/heads/dev")
    corrections = {
        wrong: {
            "author": {
                "expected": {"name": "Wrong", "email": "test@example.invalid"},
                "replacement": {"name": "ETHOS Test", "email": "test@example.invalid"},
            }
        }
    }
    original = git(repo, "show-ref")
    ready = repair.repair_signature(
        root=repo,
        expect_head=old,
        corrections=corrections,
        reason="Correct wrong attribution",
        backup=bundle,
    )
    assert ready["verdict"] == "pass", ready
    assert git(repo, "show-ref") == original
    request = tmp_path / "corrections.json"
    request.write_text(json.dumps(corrections))
    cli = run_ethos(
        "lane",
        "repair-signature",
        "--root",
        str(repo),
        "--expect-head",
        old,
        "--corrections",
        str(request),
        "--reason",
        "Correct wrong attribution",
        "--backup",
        str(bundle),
        "--json",
        cwd=repo,
    )
    assert cli["verdict"] == "pass", cli
    assert "--corrections-sha256" in cli["next_action"]
    result = repair.repair_signature(
        root=repo,
        expect_head=old,
        corrections=corrections,
        reason="Correct wrong attribution",
        backup=bundle,
        apply=True,
        authorized=True,
    )
    assert result["verdict"] == "pass", result
    assert result["head"] != old
    assert git(repo, "rev-parse", "dev") == git(candidate, "rev-parse", "HEAD") == result["head"]
    replay = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert replay["head"] == result["head"], replay


def test_completed_repair_provenance_requires_actual_ref_effect(tmp_path, monkeypatch):
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    bundle = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(bundle), "refs/heads/dev")
    native = repair.execute_git_effect

    def interrupt(*_args, **_kwargs):
        message = "before CAS"
        raise OSError(message)

    monkeypatch.setattr(repair, "execute_git_effect", interrupt)
    result = repair.repair_signature(
        root=repo,
        expect_head=old,
        corrections={old: {"resign": True}},
        reason="Repair signature",
        backup=bundle,
        apply=True,
        authorized=True,
    )
    new = result["replacement"]
    assert isinstance(new, str)
    assert completed_signature_repair(repo, new=new) is None
    monkeypatch.setattr(repair, "execute_git_effect", native)
    applied = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert applied["verdict"] == "pass", applied
    observed = completed_signature_repair(repo, new=new)
    assert observed is not None
    assert observed["old"] == old
    assert observed["new"] == new
    mapping = observed["mapping"]
    assert isinstance(mapping, dict)
    assert mapping[old] == new


def test_archive_resolution_follows_only_completed_repair_provenance(tmp_path):
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    configure_signer(fixture.repository, tmp_path)
    workspace = root / ".ethos/workspace.toml"
    workspace.write_text(
        workspace.read_text() + '\n[commit_policy]\nsubject_pattern = ".+"\n'
        'signing_required = true\nsigning_format = "ssh"\n'
    )
    (root / "openspec/changes/fixture-change/tasks.md").write_text(
        "- [x] Complete native change.\n"
    )
    head = commit_fixture(root, "complete source")
    seed_executed_proof(root, head)
    archived = run_ethos(
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=root,
    )
    assert archived["verdict"] == "pass", archived
    old = git(root, "rev-parse", "HEAD")
    expected = load_openspec_commitment(root, tree_ref=old)
    seed_executed_proof(root, old)
    initial = git(fixture.repository, "rev-parse", "HEAD")
    run_ethos("land", "--apply", "--authorize", "--expect-head", old, "--json", cwd=root)
    run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        initial,
        "--candidate-head",
        old,
        "--json",
        cwd=fixture.repository,
    )
    repo = fixture.repository
    bundle = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(bundle), "refs/heads/dev")
    result = repair.repair_signature(
        root=repo,
        expect_head=old,
        corrections={head: {"resign": True}},
        reason="Repair signature",
        backup=bundle,
        apply=True,
        authorized=True,
    )
    assert result["verdict"] == "pass", json.dumps(result, indent=2)
    assert isinstance(result["head"], str)
    restored = load_openspec_commitment(
        repo,
        tree_ref=result["head"],
        expected_digest=expected.digest(),
    )
    assert restored == expected


def test_history_repair_ref_observation_uses_exact_completed_effect(tmp_path):
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    bundle = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(bundle), "refs/heads/dev")
    result = repair.repair_signature(
        root=repo,
        expect_head=old,
        corrections={old: {"resign": True}},
        reason="Repair signature",
        backup=bundle,
        apply=True,
        authorized=True,
    )
    assert result["verdict"] == "pass", result
    new = result["head"]
    assert isinstance(new, str)
    observed = ref_update_admission_report(
        repo,
        target_ref="refs/heads/dev",
        proposed_head=new,
        remote_head=old,
        remote_name="origin",
    )
    assert observed["verdict"] == "pass", observed
    admission = observed["commit_policy_admission"]
    assert isinstance(admission, dict)
    assert admission["state"] == "repaired_history"
    assert admission["repair_attestation"]


@pytest.mark.parametrize("case", ["duplicate", "backup_symlink"])
def test_public_history_request_does_not_erase_ambiguous_inputs(tmp_path, case):
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    backup = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(backup), "refs/heads/dev")
    request = tmp_path / "request.json"
    request.write_text(json.dumps({old: {"resign": True}}))
    if case == "duplicate":
        request.write_text('{"' + old + '": {"resign": false, "resign": true}}')
    else:
        alias = tmp_path / "alias.bundle"
        alias.symlink_to(backup)
        backup = alias
    before = git(repo, "show-ref")
    report = run_ethos(
        "lane",
        "repair-signature",
        "--root",
        str(repo),
        "--expect-head",
        old,
        "--corrections",
        str(request),
        "--reason",
        "Repair",
        "--backup",
        str(backup),
        "--json",
        cwd=repo,
    )
    assert report["verdict"] == "block", report
    assert git(repo, "show-ref") == before


def test_interrupted_history_repair_recovers_native_objects_without_resigning(
    tmp_path, monkeypatch
):
    repo, first, _candidate = signature_repository(tmp_path, coupled=True)
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    old = git(repo, "commit-tree", tree, "-p", first, "-m", "fix: descendant")
    for ref in ("dev", "main", "candidate/dev"):
        git(repo, "update-ref", f"refs/heads/{ref}", old)
    backup = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(backup), "refs/heads/dev")
    native = history.create_signed_payload
    signed_payloads = []

    def interrupt(root, payload):
        if signed_payloads:
            message = "signer interrupted"
            raise OSError(message)
        signed_payloads.append(payload)
        return native(root, payload)

    monkeypatch.setattr(history, "create_signed_payload", interrupt)
    interrupted = repair.repair_signature(
        root=repo,
        expect_head=old,
        corrections={first: {"resign": True}},
        reason="Restore valid signatures",
        backup=backup,
        apply=True,
        authorized=True,
    )
    assert interrupted["verdict"] == "unknown", interrupted
    assert git(repo, "rev-parse", "refs/heads/dev") == old

    def resume(root, payload):
        assert payload not in signed_payloads, "completed object must not be signed again"
        signed_payloads.append(payload)
        return native(root, payload)

    monkeypatch.setattr(history, "create_signed_payload", resume)
    observed = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert observed["verdict"] == "pass", observed
    assert len(signed_payloads) == 2


@pytest.mark.parametrize("field", ["repository", "policy_sha256", "payload_sha256", "refs"])
def test_completed_provenance_cannot_reissue_invented_source_coordinates(tmp_path, field):
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    backup = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(backup), "refs/heads/dev")
    corrections = {old: {"resign": True}}
    coordinates = signature_coordinates(
        repo,
        old,
        os.environ["ETHOS_ACTOR"],
        history=history.history_repair_coordinates(
            repo, old, corrections=corrections, reason="Repair signature", backup=backup
        ),
    )
    new = history.prepare_history_repair(repo, old, corrections=corrections)["replacement"]
    refs = coordinates["refs"]
    assert isinstance(refs, dict)
    if field == "refs":
        refs["refs/heads/unrelated"] = old
    else:
        coordinates[field] = "0" * 64
    plan = signature_plan(repo, coordinates, new)
    now = datetime.now(UTC)
    digest = canonical_json_digest(coordinates)
    result = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": repair.RESULT,
            "verifier": coordinates["actor"],
            "subject": f"signature-repair:{digest}",
            "issued_at": now,
            "valid_from": now,
            "valid_until": None,
            "verdict": "pass",
            "mints_authority": False,
            "payload": {
                "kind": repair.RESULT,
                "body": {
                    "coordinates": coordinates,
                    "replacement": new,
                    "plan": plan.model_dump(mode="json"),
                    "plan_digest": plan.digest,
                },
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (f"git:{old}",),
            "commitment_digest": None,
            "facts_digest": digest,
            "plan_digest": plan.digest,
            "policy_digest": coordinates["policy_sha256"],
            "effect_digest": None,
        }
    )
    effect = git_effect_from_plan(plan)
    before = observe_git_effect(repo, effect)
    before["refs"] = dict(refs)
    after = before | {
        "observed_at": canonical_utc_time(datetime.now(UTC)),
        "head": new,
        "refs": dict.fromkeys(refs, new),
    }
    observed = issue_git_effect(
        effect,
        plan=plan,
        issuer=os.environ["ETHOS_ACTOR"],
        evidence=(plan.facts["repository"], "applied", before, after),
    )
    with pytest.raises(ValueError, match="signature_repair_"):
        completed_signature_repair(repo, new=new, attestations=(result, observed))

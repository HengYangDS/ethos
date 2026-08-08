from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.lane_lifecycle.change_rollover import start_change
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import attestation_store_dir
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.semantic import Attestation
from ethos.surface.cli.root.proof import resolve_generation_scope
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    import pytest


def _advance_current_generation(worktree: Path, overlay: Path) -> None:
    started_head = git(worktree, "rev-parse", "HEAD")
    overlay.write_text("forward fix, committed now\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(worktree, "commit", "-m", "implement forward fix")
    implemented_head = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=started_head,
        new_value=implemented_head,
    )
    assert advanced["state"] == "lease_ref_advanced"


def test_plan_admits_the_exact_post_archive_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(
        tmp_path,
        scope=("openspec/changes/fixture-change/**",),
    )
    worktree = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "complete fixture change")
    completed = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=completed,
    )
    assert advanced["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    archived = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed,
        apply=True,
    )
    assert archived["verdict"] == "pass", json.dumps(archived, indent=2, default=str)

    payload = run_ethos("plan", "--changed", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["verdict"] == "pass", payload
    authority = payload["data"]["transition_plan"]["prior_attestations"]["openspec_archive"]
    assert authority["predicate"] == "effect:openspec-archive"


def test_skip_specs_archive_binds_current_generation_to_the_exact_archive_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(
        tmp_path,
        scope=(
            "openspec/changes/fixture-change/**",
            "openspec/specs/contracts/spec.md",
        ),
    )
    worktree = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    metadata = worktree / "openspec/changes/fixture-change/.openspec.yaml"
    metadata.write_text(
        "schema: spec-driven\ncreated: 2026-08-08\nskip_specs: true\n", encoding="utf-8"
    )
    delta_specs = worktree / "openspec/changes/fixture-change/specs"
    git(worktree, "rm", "-r", delta_specs.relative_to(worktree).as_posix())
    git(worktree, "add", metadata.relative_to(worktree).as_posix())
    metadata_previous = git(worktree, "rev-parse", "HEAD")
    git(worktree, "commit", "-m", "declare formatting-only fixture change")
    metadata_head = git(worktree, "rev-parse", "HEAD")
    metadata_advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=metadata_previous,
        new_value=metadata_head,
    )
    assert metadata_advanced["state"] == "lease_ref_advanced"
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "complete formatting-only fixture change")
    completed = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=completed,
    )
    assert advanced["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    archived = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed,
        apply=True,
    )
    assert archived["verdict"] == "pass", json.dumps(archived, indent=2, default=str)
    assert archived["no_op"] is True
    archived_head = str(archived["head"])
    archive_paths = tuple(str(path) for path in archived["changed_paths"])

    scope = current_generation_scope(
        worktree,
        head=archived_head,
        repository_id=load_repository_commitment(worktree).id,
        commitment=load_commitment(
            worktree,
            carrier=str(leases_by_branch(worktree)["work/feature"]["base_commitment_path"]),
            change_id="fixture-change",
            tree_ref=archived_head,
        ),
        lease=leases_by_branch(worktree)["work/feature"],
        fallback_paths=("openspec/specs/contracts/spec.md", *archive_paths),
    )

    assert scope.paths == archive_paths
    assert scope.archive_authority["predicate"] == "effect:openspec-archive"
    plan = proof_plan(
        worktree,
        head=archived_head,
        change_id="fixture-change",
        changed_paths=scope.paths,
        generation_scope=scope,
    )
    assert plan.verdict == "pass"

    unrelated = proof_plan(
        worktree,
        head=archived_head,
        change_id="fixture-change",
        changed_paths=(*scope.paths, "README.md"),
        generation_scope=scope.__class__(
            paths=(*scope.paths, "README.md"),
            start_authority=scope.start_authority,
            archive_authority=scope.archive_authority,
        ),
    )
    assert unrelated.required_gaps == ("change_scope_exceeded",)

    receipt_path = attestation_store_dir(worktree) / f"{archived['attestation']['id']}.json"
    receipt = Attestation.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    forged = Attestation.issue(
        receipt.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "statement": receipt.statement
            | {
                "output": receipt.statement["output"]
                | {"changed_paths": [*archive_paths, "README.md"]}
            }
        }
    )
    receipt_path.unlink()
    (attestation_store_dir(worktree) / f"{forged.id}.json").write_text(
        forged.canonical_json(), encoding="utf-8"
    )
    tampered = current_generation_scope(
        worktree,
        head=archived_head,
        repository_id=load_repository_commitment(worktree).id,
        commitment=load_commitment(
            worktree,
            carrier=str(leases_by_branch(worktree)["work/feature"]["base_commitment_path"]),
            change_id="fixture-change",
            tree_ref=archived_head,
        ),
        lease=leases_by_branch(worktree)["work/feature"],
        fallback_paths=("README.md", *archive_paths),
    )
    assert tampered.archive_authority == {}
    assert tampered.paths == ()
    assert tampered.gaps == ("change_generation_authority_missing",)
    assert {item.state for item in tampered.attributions} == {"unknown"}


def test_clean_accepted_root_without_active_change_uses_repository_proof(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, _candidate = start_adopted_candidate(tmp_path)
    monkeypatch.setattr(
        "ethos.adapters.openspec.cli.openspec_base_command",
        lambda: ("openspec",),
    )

    def run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]):
        payload = (
            {"root": {"healthy": True}}
            if args[0] == "doctor"
            else {"changes": []}
            if args[0] == "list"
            else {"items": [], "summary": {}}
        )
        return {
            "command": [*_base, *args],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr("ethos.adapters.openspec.cli.run_json", run_json)

    plan = run_ethos("plan", "--changed", "--root", repository.as_posix(), "--json", cwd=repository)
    proof = run_ethos("prove", "--root", repository.as_posix(), "--json", cwd=repository)

    assert plan["verdict"] == "pass", plan
    assert plan["data"]["changed_paths"] == []
    assert "openspec_active_change_missing" not in plan["required_gaps"]
    assert proof["verdict"] == "pass", proof
    assert "openspec_active_change_missing" not in proof["required_gaps"]


def _start_forward_fix_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, str, object]:
    """Archive the fixture and start one exact successor generation."""
    fixture = start_adopted_work_lane(tmp_path, scope=("openspec/changes/fixture-change/**",))
    worktree = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "complete fixture change")
    completed = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=completed,
    )
    assert advanced["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    archived = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed,
        apply=True,
    )
    assert archived["verdict"] == "pass", archived
    overlay = worktree / "README.md"
    overlay.write_text("forward fix\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    started = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair the current generation without reopening archived work.",
        scope=("README.md",),
        expect_head=git(worktree, "rev-parse", "HEAD"),
        expected_overlay_digest=dirty_content_sha256(worktree),
        apply=True,
    )
    assert started["verdict"] == "pass", started
    carrier = "openspec/changes/hosted-verification-fix/commitment.toml"
    before_commitment = load_commitment(
        worktree, carrier=carrier, change_id="hosted-verification-fix"
    )
    _advance_current_generation(worktree, overlay)
    overlay.write_text("forward fix, dirty now\n", encoding="utf-8")
    commitment = worktree / carrier
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace("risks = []", 'risks = ["overlay"]'),
        encoding="utf-8",
    )
    after_commitment = load_commitment(
        worktree, carrier=carrier, change_id="hosted-verification-fix"
    )
    assert after_commitment.digest() != before_commitment.digest()
    return worktree, carrier, after_commitment


def test_plan_and_prove_bind_only_the_current_post_start_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worktree, carrier, after_commitment = _start_forward_fix_generation(monkeypatch, tmp_path)
    expected = {
        "README.md",
        "openspec/changes/hosted-verification-fix/.openspec.yaml",
        "openspec/changes/hosted-verification-fix/commitment.toml",
    }
    plan_payload = run_ethos(
        "plan", "--changed", "--root", worktree.as_posix(), "--json", cwd=worktree
    )
    assert plan_payload["verdict"] == "block", json.dumps(plan_payload, indent=2)
    assert "change_scope_exceeded" not in plan_payload["required_gaps"], plan_payload
    assert not any("archive/" in gap for gap in plan_payload["required_gaps"]), plan_payload
    detail = plan_payload
    if reference := plan_payload["data"].get("artifact_reference"):
        detail = json.loads(Path(reference["path"]).read_text(encoding="utf-8"))
    assert set(detail["data"]["changed_paths"]) == expected
    assert detail["data"]["selected_carrier"] == carrier
    attributions = {item["path"]: item for item in detail["data"]["path_attributions"]}
    assert set(expected) <= set(attributions)
    assert {item["state"] for path, item in attributions.items() if path in expected} == {
        "authorized"
    }
    assert any(
        item["state"] == "historical" and "/archive/" in item["path"]
        for item in attributions.values()
    )
    plan = detail["data"]["transition_plan"]
    assert set(plan["facts"]["values"]["changed_paths"]) == expected
    assert plan["facts"]["values"]["selected_carrier"] == carrier
    assert plan["facts"]["values"]["path_attributions"] == list(attributions.values())
    prior = plan["prior_attestations"]
    assert prior["openspec_change_start"]["predicate"] == "effect:openspec-change-start"

    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    wrong_generation = dict(lease) | {"lease_id": "lease:other-generation"}
    rejected = current_generation_scope(
        worktree,
        head=git(worktree, "rev-parse", "HEAD"),
        repository_id=load_repository_commitment(worktree).id,
        commitment=after_commitment,
        lease=wrong_generation,
        fallback_paths=("archive-history",),
    )
    assert rejected.paths == ()
    assert rejected.start_authority == {}
    assert rejected.gaps == ("change_generation_authority_missing",)
    assert rejected.attributions[0].state == "unknown"

    scope = resolve_generation_scope(worktree)
    proof = proof_plan(
        worktree,
        head=git(worktree, "rev-parse", "HEAD"),
        gate_ids=("sample-tests",),
        changed_paths=scope.paths,
        generation_scope=scope,
    )
    assert set(proof.facts["values"]["changed_paths"]) == expected
    assert proof.prior_attestations["openspec_change_start"]["predicate"] == (
        "effect:openspec-change-start"
    )

    outside = worktree / "outside-current-scope.txt"
    outside.write_text("uncovered\n", encoding="utf-8")
    status_payload = run_ethos("status", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert status_payload["verdict"] == "block"
    assert status_payload["required_gaps"][0] == "change_scope_exceeded"
    assert status_payload["data"]["selected_carrier"] == carrier
    assert status_payload["next_action"] == (
        "repair the selected Commitment scope for the uncovered current-generation paths"
    )
    blocked = run_ethos_raw("prove", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert blocked.returncode == 1
    assert blocked.stderr == ""
    blocked_payload = json.loads(blocked.stdout)
    assert blocked_payload["verdict"] == "block"
    assert blocked_payload["required_gaps"][0] == "change_scope_exceeded"

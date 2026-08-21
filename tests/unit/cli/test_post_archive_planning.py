from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.lane_lifecycle.change_rollover import start_change
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.semantic import Attestation
from ethos.surface.cli.root.proof import resolve_generation_scope
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.openspec_lifecycle import completed_lifecycle

if TYPE_CHECKING:
    import pytest

    from ethos.adapters.openspec.start_effect import CurrentGenerationScope


def _clear_selected_attestations(root: Path) -> None:
    existing = run_git(root, "show-ref", "--verify", "--hash", ATTESTATION_SET_REF, check=False)
    if existing.returncode == 0:
        run_git(root, "update-ref", "-d", ATTESTATION_SET_REF)
    assert read_attestation_set(root) == ("", ())


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


def _generation_scope(
    worktree: Path,
    *,
    head: str,
    fallback_paths: tuple[str, ...],
    lease: dict[str, object] | None = None,
    change: str = "fixture-change",
) -> CurrentGenerationScope:
    bound_lease = lease or next(iter(leases_by_branch(worktree).values()))
    carrier = str(bound_lease["base_commitment_path"])
    return current_generation_scope(
        worktree,
        head=head,
        repository_id=load_repository_commitment(worktree).id,
        commitment=load_commitment(worktree, carrier=carrier, change_id=change, tree_ref=head),
        lease=bound_lease,
        fallback_paths=fallback_paths,
    )


def _archive_skip_specs_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, str, tuple[str, ...], Attestation]:
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
    archive_paths = tuple(str(path) for path in cast("list[object]", archived["changed_paths"]))
    _clear_selected_attestations(worktree)
    return (
        worktree,
        archived_head,
        archive_paths,
        Attestation.model_validate(archived["attestation"]),
    )


def test_skip_specs_archive_binds_current_generation_to_the_exact_archive_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worktree, archived_head, archive_paths, receipt = _archive_skip_specs_fixture(
        monkeypatch, tmp_path
    )

    scope = _generation_scope(
        worktree,
        head=archived_head,
        fallback_paths=("openspec/specs/contracts/spec.md", *archive_paths),
    )

    assert scope.archive_authority == {}
    assert scope.paths == ()
    assert {item.state for item in scope.attributions} == {"unknown"}
    record_attestations(worktree, (receipt,))
    selected = _generation_scope(
        worktree,
        head=archived_head,
        fallback_paths=("openspec/specs/contracts/spec.md", *archive_paths),
    )

    assert selected.paths == archive_paths
    assert selected.archive_authority["predicate"] == "effect:openspec-archive"
    assert {item.path for item in selected.attributions} == set(archive_paths) | {
        "openspec/specs/contracts/spec.md"
    }
    assert {item.state for item in selected.attributions if item.path in set(archive_paths)} == {
        "authorized"
    }
    assert {item.source for item in selected.attributions if item.path in set(archive_paths)} == {
        "archive_effect"
    }
    status_payload = run_ethos("status", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert status_payload["verdict"] == "pass", json.dumps(status_payload, indent=2)
    assert "change_scope_exceeded" not in status_payload["required_gaps"]
    assert {
        item["path"]
        for item in status_payload["data"]["path_attributions"]
        if item["state"] == "authorized"
    } == set(archive_paths)
    payload = receipt.model_dump(mode="python", exclude={"id"})
    payload["payload"]["body"]["output"]["changed_paths"] = [*archive_paths, "README.md"]
    forged = Attestation.issue(payload)
    poison = proof_artifact_root(worktree) / f"{forged.id}.json"
    poison.parent.mkdir(parents=True, exist_ok=True)
    poison.write_text(forged.canonical_json(), encoding="utf-8")
    tampered = _generation_scope(
        worktree,
        head=archived_head,
        fallback_paths=("README.md", *archive_paths),
    )
    assert tampered.archive_authority["attestation_id"] == receipt.id
    assert tampered.paths == archive_paths
    assert tampered.gaps == ()
    assert {item.state for item in tampered.attributions if item.path in set(archive_paths)} == {
        "authorized"
    }


def _start_forward_fix_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, str]:
    """Archive the fixture and start one exact successor generation."""
    lifecycle = completed_lifecycle(
        tmp_path, monkeypatch, scope=("openspec/changes/fixture-change/**",)
    )
    worktree = lifecycle.worktree
    lifecycle.archive()
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
    _clear_selected_attestations(worktree)
    start_attestation = Attestation.model_validate(started["attestation"])
    record_attestations(worktree, (start_attestation,))
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
    return worktree, carrier


def test_plan_and_prove_bind_only_the_current_post_start_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worktree, carrier = _start_forward_fix_generation(monkeypatch, tmp_path)
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
    rejected = _generation_scope(
        worktree,
        head=git(worktree, "rev-parse", "HEAD"),
        lease=wrong_generation,
        fallback_paths=("archive-history",),
        change="hosted-verification-fix",
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

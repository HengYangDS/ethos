from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import attestation_store_dir
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import archive_transition_environment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.schema import state_database
from ethos.cli import main
from ethos.contracts.semantic import Attestation
from ethos.normalization.coercion import repository_path_matches
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def test_scope_glob_matches_archive_directory_descendants() -> None:
    assert repository_path_matches(
        "openspec/changes/archive/2026-08-05-fixture-change/tasks.md",
        "openspec/changes/archive/*-fixture-change/**",
    )


def test_archive_change_owns_official_archive_commit_and_lease_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(
        tmp_path,
        scope=("openspec/changes/fixture-change/**",),
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: [] if head == completed_head else ["proof_not_proven"],
    )

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
        apply=True,
    )

    archived_head = git(worktree, "rev-parse", "HEAD")
    assert report["verdict"] == "pass", json.dumps(report, indent=2, default=str)
    assert report["state"] == "archived"
    assert report["previous_head"] == completed_head
    assert report["head"] == archived_head
    assert report["archive_path"].endswith("-fixture-change")
    assert report["tool_version"] == "1.8.0"
    assert report["required_gaps"] == []
    assert not (worktree / "openspec/changes/fixture-change").exists()
    assert (worktree / report["archive_path"] / "commitment.toml").is_file()
    assert git(worktree, "status", "--short") == ""
    assert openspec_governance_report(worktree, lifecycle=True)["verdict"] == "pass"
    changed_paths = change_scope_paths_from_status(worktree, workspace_status(worktree))
    changed_plan = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=changed_paths,
        require_workspace=False,
    )
    assert changed_plan["verdict"] == "pass", changed_plan
    assert changed_plan["required_gaps"] == []
    assert changed_plan["lifecycle"]["scope_binding"]["state"] == "post_archive_closeout"
    plan = proof_plan(
        worktree,
        head=archived_head,
        changed_paths=changed_paths,
    )
    assert plan.verdict == "pass"
    assert plan.facts["values"]["change_id"] == "fixture-change"
    assert plan.prior_attestations["openspec_archive"]["predicate"] == ("effect:openspec-archive")

    unrelated = proof_plan(
        worktree,
        head=archived_head,
        changed_paths=(*changed_paths, "README.md"),
    )
    assert unrelated.required_gaps == ("change_scope_exceeded",)

    store = attestation_store_dir(worktree)
    receipt_path = store / f"{report['attestation']['id']}.json"
    receipt = Attestation.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    forged = Attestation.issue(
        receipt.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "statement": receipt.statement
            | {
                "output": receipt.statement["output"]
                | {"changed_paths": [*report["changed_paths"], "README.md"]}
            }
        }
    )
    receipt_path.unlink()
    (store / f"{forged.id}.json").write_text(forged.canonical_json(), encoding="utf-8")

    tampered = proof_plan(
        worktree,
        head=archived_head,
        changed_paths=changed_paths,
    )
    assert tampered.required_gaps == ("change_scope_exceeded",)


def test_archive_commit_uses_the_initiating_runtime_not_poisoned_hooks_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: [] if head == completed_head else ["proof_not_proven"],
    )
    installed = install_hook_launchers(worktree)
    poisoned = tmp_path / "stale-checkout-hooks"
    poisoned.mkdir()
    (poisoned / "pre-commit").write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
    (poisoned / "pre-commit").chmod(0o755)
    git(worktree, "config", "--worktree", "core.hooksPath", poisoned.as_posix())
    assert git(worktree, "config", "--worktree", "--get", "core.hooksPath") == (poisoned.as_posix())

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
        apply=True,
    )

    assert report["verdict"] == "pass", json.dumps(report, indent=2, default=str)
    assert report["state"] == "archived"
    assert installed["required_gaps"] == []
    assert git(worktree, "status", "--short") == ""


def test_archive_change_is_exposed_through_installed_cli_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ethos",
            "lane",
            "archive-change",
            "--change",
            "fixture-change",
            "--expect-head",
            completed_head,
            "--root",
            worktree.as_posix(),
            "--json",
        ],
    )

    with pytest.raises(SystemExit, match="0"):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "lane archive-change"
    assert payload["verdict"] == "pass"
    assert payload["state"] == "ready_to_archive"


def test_archive_change_rejects_stale_head_without_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head="f" * 40,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["expect_head_mismatch"]
    assert git(worktree, "rev-parse", "HEAD") == completed_head
    assert (worktree / "openspec/changes/fixture-change").is_dir()


def test_archive_change_requires_local_state_migration_before_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    current = state_database(repo)
    legacy = repo / ".ethos" / "state" / "state.sqlite"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    current.replace(legacy)
    current.touch()

    dry_run = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
    )
    applied = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
        apply=True,
    )

    assert dry_run["state"] == "ready_to_archive"
    assert applied["verdict"] == "block"
    assert applied["required_gaps"] == ["local_state_migration_required"]
    assert str(applied["next_action"]).startswith(
        f"ethos migrate-local-state --root {worktree} --apply --authorize "
        f"--expect-head {completed_head} --expect-plan-digest "
    )
    assert git(worktree, "rev-parse", "HEAD") == completed_head
    assert git(worktree, "status", "--short") == ""
    assert (worktree / "openspec/changes/fixture-change").is_dir()


def test_archive_change_is_not_replayable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    first = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
        apply=True,
    )

    replay = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=str(first["head"]),
        apply=True,
    )

    assert replay["verdict"] == "block"
    assert "openspec_active_change_missing:fixture-change" in replay["required_gaps"]


def test_archive_change_preserves_a_conflicting_immutable_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    active = worktree / "openspec/changes/fixture-change"
    archive_date = datetime.now().astimezone().date().isoformat()
    collision = worktree / f"openspec/changes/archive/{archive_date}-fixture-change"
    collision.parent.mkdir(parents=True)
    shutil.copytree(active, collision)
    historical = collision / "commitment.toml"
    historical.write_text(
        historical.read_text(encoding="utf-8").replace(
            "Exercise the governed fixture lifecycle.",
            "Preserve the earlier immutable archive generation.",
        ),
        encoding="utf-8",
    )
    git(worktree, "add", collision.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "retain earlier fixture archive generation")
    collision_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=collision_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    historical_tree = git(
        worktree, "rev-parse", f"{collision_head}:{collision.relative_to(worktree)}"
    )
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: [] if head == collision_head else ["proof_not_proven"],
    )

    dry_run = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=collision_head,
    )
    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=collision_head,
        apply=True,
    )

    assert report["verdict"] == "pass", json.dumps(report, indent=2, default=str)
    preserved_path = str(report["preserved_archive_path"])
    assert dry_run["state"] == "ready_to_archive"
    assert dry_run["archive_collision"]["path"] == collision.relative_to(worktree).as_posix()
    assert dry_run["archive_collision"]["tree"] == historical_tree
    assert report["state"] == "archived"
    assert preserved_path.startswith(f"{collision.relative_to(worktree).as_posix()}-")
    assert git(worktree, "rev-parse", f"HEAD:{preserved_path}") == historical_tree
    assert (worktree / report["archive_path"] / "commitment.toml").is_file()
    assert not active.exists()
    assert git(worktree, "status", "--short") == ""


def test_archive_change_collision_rejects_stale_head_without_moving_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    active = worktree / "openspec/changes/fixture-change"
    archive_date = datetime.now().astimezone().date().isoformat()
    collision = worktree / f"openspec/changes/archive/{archive_date}-fixture-change"
    collision.parent.mkdir(parents=True)
    shutil.copytree(active, collision)
    git(worktree, "add", collision.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "retain colliding archive")
    collision_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=collision_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    before = git(worktree, "rev-parse", f"HEAD:{collision.relative_to(worktree)}")

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head="f" * 40,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["expect_head_mismatch"]
    assert git(worktree, "rev-parse", f"HEAD:{collision.relative_to(worktree)}") == before
    assert active.is_dir()


def test_archive_change_collision_rolls_back_an_invalid_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    active = worktree / "openspec/changes/fixture-change"
    archive_date = datetime.now().astimezone().date().isoformat()
    collision = worktree / f"openspec/changes/archive/{archive_date}-fixture-change"
    collision.parent.mkdir(parents=True)
    shutil.copytree(active, collision)
    git(worktree, "add", collision.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "retain colliding archive before invalid delta")
    collision_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=collision_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    historical_tree = git(worktree, "rev-parse", f"HEAD:{collision.relative_to(worktree)}")
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.lease_bound_archive_scope_report",
        lambda *_args, **_kwargs: None,
    )

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=collision_head,
        apply=True,
    )

    assert report["required_gaps"] == ["openspec_archive_delta_invalid"]
    assert git(worktree, "rev-parse", "HEAD") == collision_head
    assert git(worktree, "rev-parse", f"HEAD:{collision.relative_to(worktree)}") == historical_tree
    assert active.is_dir()
    assert git(worktree, "status", "--short") == ""


def test_archive_change_rebuilds_one_exact_historical_archive_through_normal_hooks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "historical archive without governed owner")
    historical_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=historical_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: (
            [] if head in {completed_head, historical_head} else ["proof_not_proven"]
        ),
    )

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=completed_head,
        apply=True,
    )

    rebuilt_head = git(worktree, "rev-parse", "HEAD")
    assert report["verdict"] == "pass", report
    assert report["state"] == "archived"
    assert report["replaced_head"] == historical_head
    assert report["previous_head"] == completed_head
    assert rebuilt_head != historical_head
    assert git(worktree, "rev-parse", f"{rebuilt_head}^") == completed_head
    assert git(worktree, "status", "--short") == ""


def test_archive_change_rebuild_rejects_a_non_parent_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "historical archive without governed owner")
    historical_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=historical_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=git(worktree, "rev-list", "--max-parents=0", "HEAD"),
        apply=True,
    )

    assert report["verdict"] == "block"
    assert "openspec_archive_rebuild_parent_mismatch" in report["required_gaps"]
    assert git(worktree, "rev-parse", "HEAD") == historical_head
    assert git(worktree, "status", "--short") == ""


def test_archive_change_rebuild_rejects_a_different_holder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "historical archive without governed owner")
    historical_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=historical_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:different")

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=completed_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert "lease_actor_mismatch" in report["required_gaps"]
    assert git(worktree, "rev-parse", "HEAD") == historical_head


def test_archive_change_rebuild_is_not_replayable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "historical archive without governed owner")
    historical_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=historical_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: (
            [] if head in {completed_head, historical_head} else ["proof_not_proven"]
        ),
    )
    first = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=completed_head,
        apply=True,
    )

    replay = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=str(first["head"]),
        rebuild_from=completed_head,
        apply=True,
    )

    assert first["verdict"] == "pass"
    assert replay["verdict"] == "block"
    assert "openspec_archive_rebuild_already_governed" in replay["required_gaps"]


def test_archive_change_rejects_different_holder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:different")
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_actor_mismatch"]
    assert (worktree / "openspec/changes/fixture-change").is_dir()


def test_archive_change_restores_tree_when_official_output_is_tampered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    completed_head = _complete_change(worktree)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    original = openspec_cli.run_json

    def tampered(root: Path, command: tuple[str, ...], args: tuple[str, ...]):
        result = original(root, command, args)
        if args[0] == "archive" and result["exit_code"] == 0:
            result["json"]["archive"]["change"] = "other-change"
        return result

    monkeypatch.setattr(openspec_cli, "run_json", tampered)

    report = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_archive_result_invalid"]
    assert git(worktree, "rev-parse", "HEAD") == completed_head
    assert git(worktree, "status", "--short") == ""
    assert (worktree / "openspec/changes/fixture-change").is_dir()


def _complete_change(worktree: Path) -> str:
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "complete fixture change",
    )
    head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=head,
    )
    assert transition["state"] == "lease_ref_advanced"
    return head


def test_governance_allows_lease_bound_post_archive_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    completed_head = git(worktree, "rev-parse", "HEAD")
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "archive fixture change")
    archived_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=archived_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "post_archive_closeout"


def test_governance_allows_post_archive_closeout_descendant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    completed_head = git(worktree, "rev-parse", "HEAD")
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "archive fixture change")
    archived_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=archived_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    commit_fixture_file(
        worktree,
        "README.md",
        "# Fixture\n\nPost-archive closeout repair.\n",
        "repair post-archive closeout",
    )
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "post_archive_closeout"


def test_governance_allows_current_lease_staged_completion_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    tasks = worktree / "openspec" / "changes" / "fixture-change" / "tasks.md"
    tasks.write_text("- [x] Exercise fixture lifecycle\n", encoding="utf-8")
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    _stub_official_archive_state(monkeypatch, completed=True)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(tasks.relative_to(worktree).as_posix(),),
        require_workspace=False,
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "completion_transition"
    prewrite = prewrite_guard(
        root=worktree,
        paths=[tasks],
        editor_root=worktree,
        require_editor_root=True,
    )
    assert prewrite["verdict"] == "pass", prewrite
    assert prewrite["required_gaps"] == []


def test_governance_allows_custom_schema_completion_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    verification = worktree / "openspec" / "changes" / "fixture-change" / "verification.md"
    verification.write_text("# Verification\n\nComplete.\n", encoding="utf-8")
    git(worktree, "add", verification.relative_to(worktree).as_posix())
    _stub_official_archive_state(
        monkeypatch,
        completed=True,
        completion_artifact="verification.md",
    )

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(verification.relative_to(worktree).as_posix(),),
        require_workspace=False,
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["lifecycle"]["scope_binding"]["state"] == "completion_transition"


@pytest.mark.parametrize("extra_path", ["README.md", "tests/extra.py"])
def test_governance_rejects_completion_transition_with_extra_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra_path: str
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    tasks = worktree / "openspec" / "changes" / "fixture-change" / "tasks.md"
    tasks.write_text("- [x] Exercise fixture lifecycle\n", encoding="utf-8")
    extra = worktree / extra_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("extra mutation\n", encoding="utf-8")
    git(worktree, "add", tasks.relative_to(worktree).as_posix(), extra_path)
    _stub_official_archive_state(monkeypatch, completed=True)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(tasks.relative_to(worktree).as_posix(), extra_path),
        require_workspace=False,
    )

    assert report["verdict"] == "block"
    assert "openspec_active_change_missing" in report["required_gaps"]


def test_governance_rejects_staged_archive_without_archive_owner_intent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    changed_paths = _stage_archive(worktree)
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=changed_paths,
        require_workspace=False,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_active_change_missing"]
    prewrite = prewrite_guard(
        root=worktree,
        paths=[worktree / path for path in changed_paths],
        editor_root=worktree,
        require_editor_root=True,
    )
    assert prewrite["verdict"] == "block", prewrite
    assert prewrite["required_gaps"] == [
        (
            "openspec_material_path_uncovered:"
            "openspec/changes/archive/2026-08-04-fixture-change/commitment.toml"
        )
    ]


def test_governance_rejects_a_stale_archive_owner_intent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    head = git(worktree, "rev-parse", "HEAD")
    changed_paths = _stage_archive(worktree)
    monkeypatch.setenv(
        "ETHOS_ARCHIVE_TRANSITION",
        archive_transition_environment(
            worktree,
            change="fixture-change",
            head=head,
            changed_paths=changed_paths,
            official_change_complete=True,
            completion_artifacts=("openspec/changes/fixture-change/tasks.md",),
        )["ETHOS_ARCHIVE_TRANSITION"],
    )
    extra = worktree / "README.md"
    extra.write_text("# Drift\n", encoding="utf-8")
    git(worktree, "add", "README.md")

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(*changed_paths, "README.md"),
        require_workspace=False,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_active_change_missing"]


@pytest.mark.parametrize(
    "defect",
    ["missing_lease", "stale_head", "wrong_identity", "digest_drift"],
)
def test_governance_rejects_unbound_archive_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    _stage_archive(
        worktree,
        archive_change="other-change" if defect == "wrong_identity" else "fixture-change",
        complete=True,
        drift=defect == "digest_drift",
    )
    if defect == "stale_head":
        git(worktree, "commit", "-m", "archive without Lease advance")
    elif defect == "missing_lease":
        monkeypatch.setattr(
            "ethos.adapters.openspec.lifecycle.archive_transition.leases_by_branch",
            lambda _root: {},
        )
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_active_change_missing"]


def _stage_archive(
    worktree: Path,
    *,
    archive_change: str = "fixture-change",
    complete: bool = True,
    drift: bool = False,
) -> tuple[str, ...]:
    active = worktree / "openspec" / "changes" / "fixture-change"
    archive = worktree / "openspec" / "changes" / "archive" / f"2026-08-04-{archive_change}"
    archive.parent.mkdir(parents=True)
    active.rename(archive)
    (archive / "tasks.md").write_text(
        f"- [{'x' if complete else ' '}] Exercise fixture lifecycle\n",
        encoding="utf-8",
    )
    if drift:
        commitment = archive / "commitment.toml"
        commitment.write_text(
            commitment.read_text(encoding="utf-8").replace(
                "Exercise the governed fixture lifecycle.",
                "Drift from the Lease-bound intent.",
            ),
            encoding="utf-8",
        )
    git(worktree, "add", ".")
    return tuple(
        git(worktree, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD").splitlines()
    )


def _stub_official_archive_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    completed: bool = False,
    completion_artifact: str = "tasks.md",
) -> None:
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))

    def run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]):
        payload = (
            {"root": {"healthy": True}}
            if args[0] == "doctor"
            else {
                "changes": [
                    {
                        "name": "fixture-change",
                        "completedTasks": 1,
                        "totalTasks": 1,
                        "status": "complete",
                    }
                ]
                if completed
                else []
            }
            if args[0] == "list"
            else {
                "changeName": "fixture-change",
                "artifactPaths": {
                    "completion": {
                        "existingOutputPaths": [
                            str(_root / "openspec/changes/fixture-change" / completion_artifact)
                        ]
                    }
                },
            }
            if args[0] == "status"
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

    monkeypatch.setattr(openspec_cli, "run_json", run_json)

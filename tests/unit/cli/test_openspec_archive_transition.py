from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

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
from tests.support.openspec_lifecycle import OpenSpecLifecycle
from tests.support.openspec_lifecycle import add_archive_collision
from tests.support.openspec_lifecycle import advance_lease
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.openspec_lifecycle import stage_archive
from tests.support.openspec_lifecycle import stub_official_archive_state


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
    new_delta = worktree / "openspec/changes/fixture-change/specs/projected-text/spec.md"
    new_delta.parent.mkdir(parents=True)
    new_delta.write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Project canonical text\n\n"
        "The archive effect SHALL project repository-canonical text.\n\n"
        "#### Scenario: New canonical spec is projected\n\n"
        "- **WHEN** the completed Change is archived\n"
        "- **THEN** the projected spec has one terminal newline\n",
        encoding="utf-8",
    )
    git(worktree, "add", new_delta.relative_to(worktree).as_posix())
    previous_head = git(worktree, "rev-parse", "HEAD")
    git(worktree, "commit", "-m", "declare new projected capability")
    declared_head = git(worktree, "rev-parse", "HEAD")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous_head,
        new_value=declared_head,
    )
    assert transition["state"] == "lease_ref_advanced"
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
    for projected_spec in (
        worktree / "openspec/specs/contracts/spec.md",
        worktree / "openspec/specs/projected-text/spec.md",
    ):
        projected_bytes = projected_spec.read_bytes()
        assert projected_bytes.endswith(b"\n")
        assert not projected_bytes.endswith(b"\n\n")
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
    shutil.rmtree(Path(str(installed["runtime_manifest_path"])).parent)
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

@pytest.mark.parametrize(
    ("defect", "expected_gap"),
    [
        pytest.param("stale_head", "expect_head_mismatch", id="stale-head"),
        pytest.param("wrong_holder", "lease_actor_mismatch", id="wrong-holder"),
    ],
)
def test_archive_change_rejects_invalid_coordinates_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    defect: str,
    expected_gap: str,
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    expect_head = lifecycle.completed_head
    if defect == "stale_head":
        expect_head = "f" * 40
    else:
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:different")

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=expect_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [expected_gap]
    assert lifecycle.head == lifecycle.completed_head
    assert lifecycle.active.is_dir()


def test_archive_change_is_not_replayable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    first = lifecycle.apply_archive()

    replay = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=str(first["head"]),
        apply=True,
    )

    assert replay["verdict"] == "block"
    assert "openspec_active_change_missing:fixture-change" in replay["required_gaps"]


@pytest.mark.parametrize(
    "failure",
    [pytest.param("stale_head", id="stale-head"), pytest.param("invalid_delta", id="compensate")],
)
def test_archive_collision_failures_preserve_history_and_active_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    collision, collision_head, historical_tree = add_archive_collision(lifecycle)
    if failure == "invalid_delta":
        monkeypatch.setattr(
            "ethos.adapters.mutation.lane_lifecycle.archive_change.lease_bound_archive_scope_report",
            lambda *_args, **_kwargs: None,
        )
    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head="f" * 40 if failure == "stale_head" else collision_head,
        apply=True,
    )

    assert report["required_gaps"] == [
        "expect_head_mismatch" if failure == "stale_head" else "openspec_archive_delta_invalid"
    ]
    assert lifecycle.head == collision_head
    assert git(
        lifecycle.worktree,
        "rev-parse",
        f"HEAD:{collision.relative_to(lifecycle.worktree)}",
    ) == historical_tree
    assert lifecycle.active.is_dir()
    assert git(lifecycle.worktree, "status", "--short") == ""


def test_archive_change_preserves_a_conflicting_immutable_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    collision, collision_head, historical_tree = add_archive_collision(lifecycle, distinct=True)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: [] if head == collision_head else ["proof_not_proven"],
    )

    dry_run = archive_change(
        root=lifecycle.worktree, change="fixture-change", expect_head=collision_head
    )
    report = lifecycle.apply_archive()

    preserved = str(report["preserved_archive_path"])
    collision_path = collision.relative_to(lifecycle.worktree).as_posix()
    assert dry_run["archive_collision"] == {"path": collision_path, "tree": historical_tree}
    assert report["verdict"] == "pass"
    assert preserved.startswith(f"{collision_path}-")
    assert git(lifecycle.worktree, "rev-parse", f"HEAD:{preserved}") == historical_tree
    assert not lifecycle.active.exists()
    assert git(lifecycle.worktree, "status", "--short") == ""


def _historical_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> OpenSpecLifecycle:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    stage_archive(lifecycle.worktree)
    git(lifecycle.worktree, "commit", "-m", "historical archive without governed owner")
    advance_lease(lifecycle.worktree, lifecycle.completed_head)
    return lifecycle


def test_archive_change_rebuilds_one_exact_historical_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = _historical_archive(tmp_path, monkeypatch)
    historical_head = lifecycle.head
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: (
            [] if head in {lifecycle.completed_head, historical_head} else ["proof_not_proven"]
        ),
    )

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=lifecycle.completed_head,
        apply=True,
    )

    assert report["verdict"] == "pass"
    assert report["state"] == "archived"
    assert report["replaced_head"] == historical_head
    assert git(lifecycle.worktree, "rev-parse", "HEAD^") == lifecycle.completed_head
    assert git(lifecycle.worktree, "status", "--short") == ""


@pytest.mark.parametrize(
    ("defect", "expected_gap"),
    [
        ("non_parent", "openspec_archive_rebuild_parent_mismatch"),
        ("wrong_holder", "lease_actor_mismatch"),
    ],
)
def test_archive_rebuild_rejects_invalid_authority_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    defect: str,
    expected_gap: str,
) -> None:
    lifecycle = _historical_archive(tmp_path, monkeypatch)
    historical_head = lifecycle.head
    rebuild_from = lifecycle.completed_head
    if defect == "non_parent":
        rebuild_from = git(lifecycle.worktree, "rev-list", "--max-parents=0", "HEAD")
    else:
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:different")
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=rebuild_from,
        apply=True,
    )

    assert expected_gap in report["required_gaps"]
    assert lifecycle.head == historical_head
    assert git(lifecycle.worktree, "status", "--short") == ""


def test_archive_rebuild_is_not_replayable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = _historical_archive(tmp_path, monkeypatch)
    historical_head = lifecycle.head
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: (
            [] if head in {lifecycle.completed_head, historical_head} else ["proof_not_proven"]
        ),
    )
    first = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=historical_head,
        rebuild_from=lifecycle.completed_head,
        apply=True,
    )
    replay = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=str(first["head"]),
        rebuild_from=lifecycle.completed_head,
        apply=True,
    )

    assert first["verdict"] == "pass"
    assert "openspec_archive_rebuild_already_governed" in replay["required_gaps"]


def test_archive_change_restores_tree_when_official_output_is_tampered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    original = openspec_cli.run_json

    def tampered(root: Path, command: tuple[str, ...], args: tuple[str, ...]):
        result = original(root, command, args)
        if args[0] == "archive" and result["exit_code"] == 0:
            result["json"]["archive"]["change"] = "other-change"
        return result

    monkeypatch.setattr(openspec_cli, "run_json", tampered)
    report = lifecycle.apply_archive()

    assert report["required_gaps"] == ["openspec_archive_result_invalid"]
    assert lifecycle.head == lifecycle.completed_head
    assert lifecycle.active.is_dir()
    assert git(lifecycle.worktree, "status", "--short") == ""


def _complete_change(worktree: Path) -> str:
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    return commit_fixture_file(
        worktree,
        tasks.relative_to(worktree).as_posix(),
        tasks.read_text(encoding="utf-8").replace("- [ ]", "- [x]"),
        "complete fixture change",
    )


@pytest.mark.parametrize("mode", ["exact", "descendant"])
def test_governance_allows_lease_bound_post_archive_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    worktree = fixture.worktree
    previous = git(worktree, "rev-parse", "HEAD")
    stage_archive(worktree)
    git(worktree, "commit", "-m", "archive fixture change")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    advance_lease(worktree, previous)
    if mode == "descendant":
        commit_fixture_file(
            worktree,
            "README.md",
            "# Fixture\n\nPost-archive closeout repair.\n",
            "repair post-archive closeout",
        )
    stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "post_archive_closeout"


@pytest.mark.parametrize(
    ("artifact", "path"),
    [("tasks.md", "tasks.md"), ("verification.md", "verification.md")],
)
def test_governance_allows_current_lease_completion_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    artifact: str,
    path: str,
) -> None:
    worktree = start_adopted_work_lane(tmp_path).worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    target = worktree / "openspec/changes/fixture-change" / path
    target.write_text(
        "- [x] Exercise fixture lifecycle\n" if path == "tasks.md" else "# Complete\n",
        encoding="utf-8",
    )
    git(worktree, "add", target.relative_to(worktree).as_posix())
    stub_official_archive_state(monkeypatch, completed=True, completion_artifact=artifact)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(target.relative_to(worktree).as_posix(),),
        require_workspace=False,
    )

    assert report["verdict"] == "pass"
    assert report["lifecycle"]["scope_binding"]["state"] == "completion_transition"
    assert prewrite_guard(
        root=worktree,
        paths=[target],
        editor_root=worktree,
        require_editor_root=True,
    )["verdict"] == "pass"


@pytest.mark.parametrize("extra_path", ["README.md", "tests/extra.py"])
def test_governance_rejects_completion_transition_with_extra_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra_path: str
) -> None:
    worktree = start_adopted_work_lane(tmp_path).worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text("- [x] Exercise fixture lifecycle\n", encoding="utf-8")
    extra = worktree / extra_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("extra mutation\n", encoding="utf-8")
    git(worktree, "add", tasks.relative_to(worktree).as_posix(), extra_path)
    stub_official_archive_state(monkeypatch, completed=True)

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
    worktree = start_adopted_work_lane(tmp_path).worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    changed_paths = stage_archive(worktree)
    stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(
        worktree, lifecycle=True, changed_paths=changed_paths, require_workspace=False
    )

    assert report["required_gaps"] == ["openspec_active_change_missing"]
    assert prewrite_guard(
        root=worktree,
        paths=[worktree / path for path in changed_paths],
        editor_root=worktree,
        require_editor_root=True,
    )["verdict"] == "block"


def test_governance_rejects_a_stale_archive_owner_intent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worktree = start_adopted_work_lane(tmp_path).worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    head = git(worktree, "rev-parse", "HEAD")
    changed_paths = stage_archive(worktree)
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
    (worktree / "README.md").write_text("# Drift\n", encoding="utf-8")
    git(worktree, "add", "README.md")

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(*changed_paths, "README.md"),
        require_workspace=False,
    )

    assert report["required_gaps"] == ["openspec_active_change_missing"]


@pytest.mark.parametrize(
    "defect", ["missing_lease", "stale_head", "wrong_identity", "digest_drift"]
)
def test_governance_rejects_unbound_archive_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str
) -> None:
    worktree = start_adopted_work_lane(tmp_path).worktree
    stage_archive(
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
    stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["required_gaps"] == ["openspec_active_change_missing"]

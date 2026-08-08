from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import archive_transition_environment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.status.workspace import workspace_status
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.openspec_lifecycle import OpenSpecLifecycle
from tests.support.openspec_lifecycle import add_archive_collision
from tests.support.openspec_lifecycle import advance_lease
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.openspec_lifecycle import stage_archive

if TYPE_CHECKING:
    from pathlib import Path


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
    assert plan.prior_attestations["openspec_archive"]["predicate"] == ("effect:openspec-archive")


def test_archive_change_is_not_replayable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: [] if head == collision_head else ["proof_not_proven"],
    )
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
    assert (
        git(
            lifecycle.worktree,
            "rev-parse",
            f"HEAD:{collision.relative_to(lifecycle.worktree)}",
        )
        == historical_tree
    )
    assert lifecycle.active.is_dir()
    assert git(lifecycle.worktree, "status", "--short") == ""


def _historical_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OpenSpecLifecycle:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    stage_archive(lifecycle.worktree)
    git(lifecycle.worktree, "commit", "-m", "historical archive without governed owner")
    advance_lease(lifecycle.worktree, lifecycle.completed_head)
    return lifecycle


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

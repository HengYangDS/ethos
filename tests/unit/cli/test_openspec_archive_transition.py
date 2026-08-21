from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from io import StringIO
from typing import TYPE_CHECKING
from typing import cast

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive_change as archive_owner
import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.lifecycle.archive_effect as archive_effect
from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_effect import archive_transition_environment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.admission import HookAdmissionRequest
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.openspec_lifecycle import OpenSpecLifecycle
from tests.support.openspec_lifecycle import add_archive_collision
from tests.support.openspec_lifecycle import advance_lease
from tests.support.openspec_lifecycle import assert_lifecycle_outcome
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.openspec_lifecycle import stage_archive

if TYPE_CHECKING:
    from pathlib import Path


def _attested_effect_identity(report: dict[str, object]) -> str:
    """Read the typed effect identity from one archive Attestation projection."""
    attestation = cast("dict[str, object]", report["attestation"])
    payload = cast("dict[str, object]", attestation["payload"])
    body = cast("dict[str, object]", payload["body"])
    inputs = cast("dict[str, object]", body["input"])
    return cast("str", inputs["effect_identity"])


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
    prepared_effect_identities: list[str] = []
    native_environment = archive_owner.archive_transition_environment

    def capture_prepared_effect(
        root: Path,
        *,
        change: str,
        head: str,
        changed_paths: tuple[str, ...],
        official_change_complete: bool,
        completion_artifacts: tuple[str, ...],
    ) -> dict[str, str]:
        environment = native_environment(
            root,
            change=change,
            head=head,
            changed_paths=changed_paths,
            official_change_complete=official_change_complete,
            completion_artifacts=completion_artifacts,
        )
        payload = json.loads(environment["ETHOS_ARCHIVE_TRANSITION"])
        prepared_effect_identities.append(str(payload["effect_identity"]))
        return environment

    monkeypatch.setattr(archive_owner, "archive_transition_environment", capture_prepared_effect)

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
    archive_path = cast("str", report["archive_path"])
    assert archive_path.endswith("-fixture-change")
    assert report["tool_version"] == "1.9.0"
    assert report["required_gaps"] == []
    assert_lifecycle_outcome(report, "committed", "not_required", "absent")
    assert len(prepared_effect_identities) == 1
    assert _attested_effect_identity(report) == prepared_effect_identities[0]
    assert not (worktree / "openspec/changes/fixture-change").exists()
    assert (worktree / archive_path / "commitment.toml").is_file()
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
    assert (
        plan.prior_attestations["openspec_archive"]["effect_identity"]
        == (prepared_effect_identities[0])
    )


@pytest.mark.parametrize(
    ("ownerless", "ready_state"),
    [(False, "ready_to_finalize_archive"), (True, "ready_to_finalize_ownerless_archive")],
)
def test_archive_change_finalizes_an_exact_official_postimage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    ownerless: bool,
    ready_state: str,
) -> None:
    """One exact official post-image resumes with or without its live Lease."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archive_path = lifecycle.stage_official_archive()
    if ownerless:
        with closing(sqlite3.connect(state_database(lifecycle.worktree))) as connection, connection:
            connection.execute("delete from leases where subject = ?", (lifecycle.branch,))
    assert not lifecycle.active.exists()
    assert (lifecycle.worktree / archive_path / "commitment.toml").is_file()
    assert (lifecycle.branch in leases_by_branch(lifecycle.worktree)) is not ownerless
    status = git(lifecycle.worktree, "status", "--short")
    index_tree = git(lifecycle.worktree, "write-tree")
    invocations: list[tuple[str, ...]] = []
    native_run_json = openspec_cli.run_json

    def observe_run_json(
        root: Path, base: tuple[str, ...], args: tuple[str, ...]
    ) -> dict[str, object]:
        invocations.append(args)
        return native_run_json(root, base, args)

    monkeypatch.setattr(openspec_cli, "run_json", observe_run_json)

    planned = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
    )

    assert planned["verdict"] == "pass", json.dumps(planned, indent=2, default=str)
    assert planned["state"] == ready_state
    assert planned["required_gaps"] == []
    assert_lifecycle_outcome(
        planned,
        "zero_effect",
        "not_required",
        "absent",
        (
            "ethos lane archive-change --change fixture-change "
            f"--expect-head {lifecycle.completed_head} --apply --json"
        ),
    )
    assert git(lifecycle.worktree, "status", "--short") == status
    assert git(lifecycle.worktree, "write-tree") == index_tree

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
        apply=True,
    )

    assert report["verdict"] == "pass", json.dumps(report, indent=2, default=str)
    assert report["state"] == "archived"
    assert report["previous_head"] == lifecycle.completed_head
    assert report["archive_path"] == archive_path
    if ownerless:
        assert report["lease"] == {}
        attestation = cast("dict[str, object]", report["attestation"])
        assert attestation["predicate"] == "effect:openspec-archive"
    assert_lifecycle_outcome(report, "committed", "not_required", "absent")
    assert (lifecycle.branch in leases_by_branch(lifecycle.worktree)) is not ownerless
    assert git(lifecycle.worktree, "status", "--short") == ""
    assert not any(args and args[0] == "archive" for args in invocations)


def test_ownerless_archive_postimage_blocks_bare_commit_with_exact_recovery_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A materialized archive without its Lease names one governed continuation."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    lifecycle.stage_official_archive()
    with closing(sqlite3.connect(state_database(lifecycle.worktree))) as connection, connection:
        connection.execute("delete from leases where subject = ?", (lifecycle.branch,))
    changed_paths = change_scope_paths_from_status(
        lifecycle.worktree, workspace_status(lifecycle.worktree)
    )

    report = prewrite_guard(
        root=lifecycle.worktree,
        paths=[lifecycle.worktree / path for path in changed_paths],
        editor_root=lifecycle.worktree,
        require_editor_root=True,
    )

    assert report["verdict"] == "block"
    gaps = cast("list[object]", report["required_gaps"])
    assert f"work_lane_missing_lease:{lifecycle.branch}" in gaps
    assert report["next_action"] == (
        "ethos lane archive-change --change fixture-change "
        f"--expect-head {lifecycle.completed_head} --apply --json"
    )
    hook = hook_admission_report(
        HookAdmissionRequest(
            root=lifecycle.worktree.as_posix(),
            layer="pre-tool",
            paths=tuple((lifecycle.worktree / path).as_posix() for path in changed_paths),
            editor_root=lifecycle.worktree.as_posix(),
            expected_root=lifecycle.worktree.as_posix(),
            require_editor_root=True,
            command="git commit",
        )
    )
    assert hook["verdict"] == "block"
    assert hook["next_action"] == report["next_action"]
    git(lifecycle.worktree, "add", "--all")
    assert (
        execute_hook(
            lifecycle.worktree,
            "pre-commit",
            (),
            stdin=StringIO(""),
        )
        == 1
    )
    hook_error = json.loads(capsys.readouterr().err)
    assert hook_error["next_action"] == report["next_action"]


def test_archive_change_rejects_unrelated_overlay_beside_official_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Only the exact official post-image can consume archive finalization authority."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    lifecycle.stage_official_archive()
    (lifecycle.worktree / "README.md").write_text("unrelated\n", encoding="utf-8")

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_archive_delta_invalid"]


def test_archive_finalization_commit_failure_restores_only_the_real_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archive_path = lifecycle.stage_official_archive()
    index_tree = git(lifecycle.worktree, "write-tree")
    status = git(lifecycle.worktree, "status", "--short")
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.commit_git_worktree",
        lambda *_args, **_kwargs: {"verdict": "block", "error": "hook rejected"},
    )

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
        apply=True,
    )

    assert report["required_gaps"] == ["openspec_archive_commit_failed"]
    assert git(lifecycle.worktree, "write-tree") == index_tree
    assert git(lifecycle.worktree, "status", "--short") == status
    assert (lifecycle.worktree / archive_path / "commitment.toml").is_file()


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
            archive_effect,
            "archive_postimage_scope_report",
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
            "HEAD:"
            f"{report.get('preserved_archive_path') or collision.relative_to(lifecycle.worktree)}",
        )
        == historical_tree
    )
    assert lifecycle.active.is_dir()
    assert git(lifecycle.worktree, "status", "--short") == ""


def test_archive_collision_preserves_history_and_commits_the_new_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    collision, collision_head, historical_tree = add_archive_collision(lifecycle)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, head: [] if head == collision_head else ["proof_not_proven"],
    )

    report = archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=collision_head,
        apply=True,
    )

    assert report["verdict"] == "pass", json.dumps(report, indent=2, default=str)
    preservation = str(report["preserved_archive_path"])
    assert preservation != collision.relative_to(lifecycle.worktree).as_posix()
    assert git(lifecycle.worktree, "rev-parse", f"HEAD:{preservation}") == historical_tree
    archive_path = cast("str", report["archive_path"])
    lease = cast("dict[str, object]", report["lease"])
    assert git(lifecycle.worktree, "rev-parse", f"HEAD:{archive_path}")
    assert lease["base_commitment_path"] == f"{archive_path}/commitment.toml"
    assert not lifecycle.active.exists()
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

    gaps = report["required_gaps"]
    assert gaps
    assert "openspec_active_change_missing" not in gaps
    assert all(str(gap).startswith("openspec_material_path_uncovered:") for gap in gaps)
    assert "openspec_material_path_uncovered:README.md" in gaps

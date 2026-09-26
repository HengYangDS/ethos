"""Distinguish final OpenSpec task completion from archive content tampering."""

from __future__ import annotations

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive_command
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.governed_repository import prepared_work_lane
from tests.support.openspec_lifecycle import HOLDER
from tests.support.openspec_lifecycle import OpenSpecLifecycle

CHANGE = "task-completion"
ACTIVE = f"openspec/changes/{CHANGE}"
ARCHIVE = f"openspec/changes/archive/2026-09-26-{CHANGE}"
TASKS = "- [x] 1.1 Prepare\n- [ ] 1.2 Review exact source\n- [ ] 1.3 Confirm result\n"


@pytest.mark.parametrize(
    "transition",
    ["complete", "partial", "unchanged-incomplete", "body-change", "extra-task", "other-document"],
)
def test_archive_postimage_admits_only_complete_monotonic_task_progress(
    tmp_path, transition: str
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    for relative, content in {
        f"{ACTIVE}/.openspec.yaml": "schema: spec-driven\n",
        f"{ACTIVE}/proposal.md": "## Why\n\nPreserve an exact review.\n",
        f"{ACTIVE}/design.md": "## Context\n\nArchive the selected intent.\n",
        f"{ACTIVE}/tasks.md": TASKS,
        f"{ACTIVE}/specs/contracts/spec.md": "## ADDED Requirements\n",
    }.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    head = commit_fixture(repo, "declare exact review before archive")
    target = repo / ARCHIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    (repo / ACTIVE).rename(target)
    tasks = target / "tasks.md"
    completed = TASKS.replace("- [ ]", "- [x]")
    if transition == "partial":
        completed = TASKS.replace("- [ ] 1.2", "- [x] 1.2")
    elif transition == "unchanged-incomplete":
        completed = TASKS
    elif transition == "body-change":
        completed = completed.replace("Review exact source", "Rewrite source")
    elif transition == "extra-task":
        completed += "- [x] 1.4 Insert unreviewed work\n"
    tasks.write_text(completed, encoding="utf-8")
    if transition == "other-document":
        (target / "proposal.md").write_text("## Why\n\nRewrite the reviewed intent.\n")
    before = (git(repo, "status", "--porcelain"), (repo / ".git/index").read_bytes())

    if transition == "complete":
        result = archive_postimage(repo, head=head, change=CHANGE)
        assert result is not None
        assert result.scope is not None
        assert result.scope["verdict"] == "pass"
        assert result.scope["archive_path"] == ARCHIVE
    else:
        reason = {
            "partial": "archive_reference_task_incomplete",
            "unchanged-incomplete": "archive_reference_task_incomplete",
            "body-change": "archive_reference_task_transition_invalid",
            "extra-task": "archive_reference_task_transition_invalid",
            "other-document": "archive_reference_content_changed",
        }[transition]
        with pytest.raises(ValueError, match=reason):
            archive_postimage(repo, head=head, change=CHANGE)

    assert (git(repo, "status", "--porcelain"), (repo / ".git/index").read_bytes()) == before
    assert git(repo, "rev-parse", "HEAD") == head


def test_public_archive_preview_recognizes_final_task_check_in_official_stage(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = prepared_work_lane(tmp_path, docs_only=True)
    root = fixture.worktree
    head = git(root, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)
    tasks = root / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
    lifecycle = OpenSpecLifecycle(*fixture, head)
    archive_path = lifecycle.stage_official_archive()
    git(root, "add", "-A")
    monkeypatch.setattr(
        archive_command,
        "proof_gaps",
        lambda _root, candidate, **_kwargs: [] if candidate == head else ["proof_not_proven"],
    )
    monkeypatch.setattr(archive_effect, "proof_gaps", lambda *_args, **_kwargs: [])

    preview = archive_command.archive_change(
        root=root, change="fixture-change", expect_head=head, apply=False
    )

    assert preview["verdict"] == "pass", preview
    assert preview["state"] == "ready_to_finalize_archive"
    assert preview["archive_path"] == archive_path
    changed_paths = preview["changed_paths"]
    assert isinstance(changed_paths, list)
    assert f"{archive_path}/tasks.md" in changed_paths
    assert git(root, "rev-parse", "HEAD") == head

    applied = archive_command.archive_change(
        root=root, change="fixture-change", expect_head=head, apply=True
    )
    assert applied["verdict"] == "pass", applied
    assert git(root, "rev-parse", "HEAD") != head
    assert not lifecycle.active.exists()
    assert (root / archive_path / "tasks.md").is_file()


def test_public_archive_preview_reports_the_actual_invalid_task_delta(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = prepared_work_lane(tmp_path, docs_only=True)
    root = fixture.worktree
    head = git(root, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)
    tasks = root / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
    archive_path = OpenSpecLifecycle(*fixture, head).stage_official_archive()
    archived_tasks = root / archive_path / "tasks.md"
    archived_tasks.write_text(
        archived_tasks.read_text(encoding="utf-8").replace(
            "Exercise fixture lifecycle", "Rewrite fixture lifecycle"
        ),
        encoding="utf-8",
    )
    git(root, "add", "-A")
    before = (git(root, "show-ref"), git(root, "status", "--porcelain"))

    preview = archive_command.archive_change(
        root=root, change="fixture-change", expect_head=head, apply=False
    )

    assert preview["verdict"] == "block"
    assert preview["state"] == "repair_required"
    gaps = preview["required_gaps"]
    assert isinstance(gaps, list)
    assert any(gap.startswith("archive_reference_task_transition_invalid:") for gap in gaps)
    assert (git(root, "show-ref"), git(root, "status", "--porcelain")) == before

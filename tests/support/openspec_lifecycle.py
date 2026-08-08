"""Semantic fixtures for OpenSpec lifecycle state-transition tests."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

HOLDER = "agent:test:case:agent-test"


@dataclass(frozen=True)
class OpenSpecLifecycle:
    """One completed, Lease-bound OpenSpec generation."""

    repository: Path
    candidate: Path
    source: Path
    worktree: Path
    completed_head: str

    @property
    def branch(self) -> str:
        return git(self.worktree, "branch", "--show-current")

    @property
    def active(self) -> Path:
        return self.worktree / "openspec/changes/fixture-change"

    @property
    def head(self) -> str:
        return git(self.worktree, "rev-parse", "HEAD")

    @property
    def lease(self) -> dict[str, object]:
        return leases_by_branch(self.worktree)[self.branch]

    def apply_archive(self, **updates: object) -> dict[str, object]:
        return archive_change(
            root=self.worktree,
            change="fixture-change",
            expect_head=self.head,
            apply=True,
            **updates,
        )

    def archive(self) -> dict[str, object]:
        """Apply the exact archive and require its terminal success contract."""
        report = self.apply_archive()
        assert report["verdict"] == "pass", report
        return report


def completed_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    scope: tuple[str, ...] = ("**",),
    holder: str = HOLDER,
) -> OpenSpecLifecycle:
    """Create one completed lane and admit its exact HEAD for archive proof."""
    fixture = start_adopted_work_lane(tmp_path, holder_ref=holder, scope=scope)
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    tasks = fixture.worktree / "openspec/changes/fixture-change/tasks.md"
    completed = tasks.read_text(encoding="utf-8").replace("- [ ]", "- [x]")
    head = commit_fixture_file(
        fixture.worktree,
        tasks.relative_to(fixture.worktree).as_posix(),
        completed,
        "complete fixture change",
    )
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, candidate: [] if candidate == head else ["proof_not_proven"],
    )
    return OpenSpecLifecycle(*fixture, head)


def advance_lease(worktree: Path, old_head: str) -> str:
    """Bind the current Lease to the worktree's current committed HEAD."""
    head = git(worktree, "rev-parse", "HEAD")
    report = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=old_head,
        new_value=head,
    )
    assert report["state"] == "lease_ref_advanced"
    return head


def add_archive_collision(
    lifecycle: OpenSpecLifecycle,
    *,
    distinct: bool = False,
) -> tuple[Path, str, str]:
    """Commit one immutable archive at the official target path."""
    archive_date = datetime.now().astimezone().date().isoformat()
    collision = lifecycle.worktree / f"openspec/changes/archive/{archive_date}-fixture-change"
    collision.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(lifecycle.active, collision)
    if distinct:
        commitment = collision / "commitment.toml"
        commitment.write_text(
            commitment.read_text(encoding="utf-8").replace(
                "Exercise the governed fixture lifecycle.",
                "Preserve the earlier immutable archive generation.",
            ),
            encoding="utf-8",
        )
    git(lifecycle.worktree, "add", collision.relative_to(lifecycle.worktree).as_posix())
    git(lifecycle.worktree, "commit", "-m", "retain colliding archive")
    head = advance_lease(lifecycle.worktree, lifecycle.completed_head)
    tree = git(lifecycle.worktree, "rev-parse", f"HEAD:{collision.relative_to(lifecycle.worktree)}")
    return collision, head, tree


def stage_archive(
    worktree: Path,
    *,
    archive_change: str = "fixture-change",
    complete: bool = True,
    drift: bool = False,
) -> tuple[str, ...]:
    """Stage the physical active-to-archive transition without authority."""
    active = worktree / "openspec/changes/fixture-change"
    archive = worktree / f"openspec/changes/archive/2026-08-04-{archive_change}"
    archive.parent.mkdir(parents=True, exist_ok=True)
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
    return tuple(git(worktree, "diff", "--cached", "--name-only").splitlines())


def stub_official_archive_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    completed: bool = False,
    completion_artifact: str = "tasks.md",
) -> None:
    """Project only the official OpenSpec observations relevant to archive state."""
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))

    def run_json(root: Path, base: tuple[str, ...], args: tuple[str, ...]):
        if args[0] == "doctor":
            payload: object = {"root": {"healthy": True}}
        elif args[0] == "list":
            payload = {
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
        elif args[0] == "status":
            payload = {
                "changeName": "fixture-change",
                "artifactPaths": {
                    "completion": {
                        "existingOutputPaths": [
                            str(root / "openspec/changes/fixture-change" / completion_artifact)
                        ]
                    }
                },
            }
        else:
            payload = {"items": [], "summary": {}}
        return {
            "command": [*base, *args],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "run_json", run_json)

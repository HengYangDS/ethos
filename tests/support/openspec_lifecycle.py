"""Semantic fixtures for OpenSpec lifecycle state-transition tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.mutation.lane_lifecycle.archive.command import archive_change
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

HOLDER = "agent:test:case:agent-test"
OUTCOME_FIELDS = (
    "effect_state",
    "compensation_state",
    "residue_state",
    "next_action",
    "user_decision_required",
)


def assert_lifecycle_outcome(
    report: dict[str, object],
    effect: str,
    compensation: str,
    residue: str,
    next_action: str = "",
    *,
    user_decision_required: bool = False,
) -> None:
    """Assert one complete lifecycle outcome value."""
    actual = tuple(report[field] for field in OUTCOME_FIELDS)
    expected = (
        effect,
        compensation,
        residue,
        next_action,
        user_decision_required,
    )
    assert actual == expected, (actual, expected)


@dataclass(frozen=True, slots=True)
class OpenSpecLifecycle:
    """One completed, Lease-bound OpenSpec generation."""

    repository: Path
    candidate: Path
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

    def stage_official_archive(self, change: str = "fixture-change") -> str:
        """Apply official OpenSpec archive output without ETHOS finalization."""
        command = openspec_cli.openspec_base_command()
        assert command is not None
        result = openspec_cli.run_json(
            self.worktree,
            command,
            openspec_cli.archive_command(self.worktree, change)[1:],
        )
        gaps, archive_path = openspec_cli.archive_result(self.worktree, change, result)
        assert gaps == []
        return archive_path

    def archive(self) -> dict[str, object]:
        """Apply the exact archive and require its terminal success contract."""
        report = self.apply_archive()
        assert report["verdict"] == "pass", report
        return report


def completed_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    holder: str = HOLDER,
) -> OpenSpecLifecycle:
    """Create one completed lane and admit its exact HEAD for archive proof."""
    fixture = start_adopted_work_lane(tmp_path, holder_ref=holder)
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
        "ethos.adapters.mutation.lane_lifecycle.archive.command.proof_gaps",
        lambda _root, candidate: [] if candidate == head else ["proof_not_proven"],
    )
    return OpenSpecLifecycle(*fixture, head)


def stub_official_archive_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    completed: bool = False,
    change_name: str = "fixture-change",
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
                        "name": change_name,
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
                "changeName": change_name,
                "artifactPaths": {
                    "completion": {
                        "existingOutputPaths": [
                            str(root / "openspec/changes" / change_name / completion_artifact)
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

"""Semantic fixtures for OpenSpec lifecycle state-transition tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.mutation.lane_lifecycle.archive.command import archive_change
from ethos.adapters.openspec.lifecycle.archive_transition import ArchivePostimage
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    import pytest

HOLDER = "agent:test:case:agent-test"
OUTCOME_FIELDS = (
    "effect_state",
    "compensation_state",
    "residue_state",
    "next_action",
    "user_decision_required",
)


STUB_BRANCH = "work/feature"
STUB_HEAD = "old-head"
STUB_NEW_HEAD = "new-head"
STUB_CHANGE = "fixture-change"
STUB_ARCHIVE_PATH = "openspec/changes/archive/2026-09-10-fixture-change"


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


def completed_archive_governance(
    *, remaining: int = 0, required_gaps: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "required_gaps": list(required_gaps),
        "lifecycle": {"changes": [{"name": STUB_CHANGE, "progress": {"remaining": remaining}}]},
        "commands": {"status": {"json": {"changes": []}}},
    }


def archive_authority() -> CurrentAuthority:
    return CurrentAuthority(
        verdict="pass",
        reason="matched",
        branch=STUB_BRANCH,
        actor="agent:test",
        lease={
            "lease_state": "valid",
            "lane_ref": STUB_BRANCH,
            "holder_ref": "agent:test",
            "generation": 1,
            "expires_at": "2099-01-01T00:00:00Z",
        },
        current_head=STUB_HEAD,
        current_tree="source-tree",
    )


def official_archive_result(
    root: Path, *, change: str = STUB_CHANGE, path: str = STUB_ARCHIVE_PATH
) -> dict[str, Any]:
    absolute = root / path if not Path(path).is_absolute() else Path(path)
    return {
        "exit_code": 0,
        "parse_error": "",
        "stderr": "",
        "command": ["openspec", "archive", change],
        "json": {
            "archive": {
                "change": change,
                "path": absolute.as_posix() if path else "",
                "specsUpdated": [],
                "totals": {},
            }
        },
    }


def stub_archive_public(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    remaining: int = 0,
    result: dict[str, Any] | None = None,
    collision: bool = False,
    invocations: list[str] | None = None,
    resolution_gaps: tuple[str, ...] = (),
    resolution: CurrentResolution | None = None,
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test")
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: STUB_HEAD)
    authority = archive_authority()

    def observe_workspace(*_args: object, **_kwargs: object):
        if invocations is not None:
            invocations.append("workspace")
        return {"branch": STUB_BRANCH, "head": STUB_HEAD, "role": "work_lane"}, authority

    def resolve_current(*_args: object, **_kwargs: object) -> CurrentResolution:
        if invocations is not None:
            invocations.append("resolution")
        return resolution or CurrentResolution(
            verdict="block" if resolution_gaps else "pass",
            authority=authority,
            commitment=(
                None if resolution_gaps else commitment_fixture(id=f"change:{STUB_CHANGE}")
            ),
            scope=CurrentScope(()),
            openspec=completed_archive_governance(
                remaining=remaining,
                required_gaps=resolution_gaps,
            ),
            required_gaps=resolution_gaps,
        )

    monkeypatch.setattr(archive, "workspace_status_observation", observe_workspace)
    monkeypatch.setattr(archive, "resolve_current_resolution", resolve_current)
    monkeypatch.setattr(archive, "proof_gaps", lambda *_args: [])

    def git_stdout(_root: Path, *args: str) -> str:
        return {
            ("branch", "--show-current"): STUB_BRANCH,
            ("status", "--short"): "",
            ("diff", "--cached", "--name-only", "--diff-filter=ACMRTD"): (
                f"{STUB_ARCHIVE_PATH}/proposal.md"
            ),
            ("write-tree",): "archive-tree",
            ("show", "-s", "--format=%ct", STUB_NEW_HEAD): "0",
        }.get(args, "")

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(archive_effect, "git_stdout", git_stdout)

    def collision_report(*_args: object) -> archive.ArchiveCollision | None:
        preserved = root / f"{STUB_ARCHIVE_PATH}.preserved"
        if not collision:
            return None
        if preserved.exists():
            message = "openspec_archive_collision_preservation_conflict"
            raise ValueError(message)
        return archive.ArchiveCollision(
            STUB_ARCHIVE_PATH, "archive-tree", f"{STUB_ARCHIVE_PATH}.preserved"
        )

    monkeypatch.setattr(archive, "archive_collision", collision_report)
    postimages = iter(
        (
            ArchivePostimage(
                change=STUB_CHANGE,
                head=STUB_HEAD,
                scope=None,
                active_present=True,
            ),
            ArchivePostimage(
                change=STUB_CHANGE,
                head=STUB_HEAD,
                scope={
                    "archive_path": STUB_ARCHIVE_PATH,
                    "changed_paths": (f"{STUB_ARCHIVE_PATH}/proposal.md",),
                    "completion_artifacts": (),
                    "tree": "archive-tree",
                },
                active_present=False,
            ),
        )
    )

    def observe_archive_postimage(*_args: object, **_kwargs: object) -> ArchivePostimage:
        return next(postimages)

    monkeypatch.setattr(archive, "archive_postimage", observe_archive_postimage)
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        archive.openspec_cli,
        "run_json",
        lambda *_args: result or official_archive_result(root),
    )
    monkeypatch.setattr(archive, "dirty_changed_paths", lambda _root: ("spec.md",))
    monkeypatch.setattr(archive, "normalize_projected_specs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(archive_effect, "stage_git_worktree", lambda *_args, **_kwargs: None)

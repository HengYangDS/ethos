"""Exercise how an archive compensates when an admitted native effect fails or is refused."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.openspec.lifecycle.archive_transition import ArchivePostimage
from ethos.contracts.outcome import refusal
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.openspec_lifecycle import assert_lifecycle_outcome
from tests.support.openspec_lifecycle import official_archive_result
from tests.support.openspec_lifecycle import stub_archive_public

if TYPE_CHECKING:
    from pathlib import Path

BRANCH = "work/feature"
HEAD = "old-head"
NEW_HEAD = "new-head"
CHANGE = "fixture-change"
ARCHIVE_PATH = "openspec/changes/archive/2026-09-10-fixture-change"


def test_archive_public_missing_native_command_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: None)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_official_cli_missing"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        "ethos lane status --json",
        user_decision_required=True,
    )


@pytest.mark.parametrize("committed", [False, True])
def test_archive_public_exception_compensates_only_before_ref_advancement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, committed: bool
) -> None:
    stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(
        archive.openspec_cli,
        "run_json",
        lambda *_args: (_ for _ in ()).throw(ValueError("archive_failed")),
    )
    compensated: list[dict[str, object]] = []
    monkeypatch.setattr(
        archive, "compensate_git_worktree", lambda _root, **kwargs: compensated.append(kwargs)
    )
    if committed:
        monkeypatch.setattr(archive, "current_tracked_head", lambda _root: NEW_HEAD)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == ("repair_required" if committed else "blocked")
    assert report["required_gaps"] == ["archive_failed"]
    assert_lifecycle_outcome(
        report,
        "committed" if committed else "mutated",
        "not_required" if committed else "completed",
        "retained" if committed else "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} "
        f"--subject 'chore(openspec): archive {CHANGE}' --apply --json",
    )
    assert compensated == ([] if committed else [{"head": HEAD, "untracked_path": ""}])


@pytest.mark.parametrize("collision", [False, True])
def test_archive_public_commit_failure_compensates_native_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, collision: bool
) -> None:
    stub_archive_public(monkeypatch, tmp_path, collision=collision)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)
    monkeypatch.setattr(
        archive_effect,
        "create_git_commit",
        lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 1, "stdout": "", "stderr": "hook rejected"}
        )(),
    )
    compensated: list[str] = []
    monkeypatch.setattr(
        archive_effect,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(str(kwargs["untracked_path"])),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_archive_commit_failed"]
    assert report["stderr"] == "hook rejected"

    assert_lifecycle_outcome(
        report,
        "mutated",
        "completed",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} "
        f"--subject 'chore(openspec): archive {CHANGE}' --apply --json",
    )
    assert compensated == [f"{ARCHIVE_PATH}.preserved" if collision else ARCHIVE_PATH]


def test_archive_policy_refusal_keeps_its_gaps_and_compensates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stub_archive_public(monkeypatch, tmp_path, collision=False)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)

    refused = refusal("git_signature_untrusted", "git_signer_unbound")

    def refuse(*_args, **_kwargs):
        raise refused

    monkeypatch.setattr(archive_effect, "create_git_commit", refuse)
    compensated: list[str] = []
    monkeypatch.setattr(
        archive_effect,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(str(kwargs["untracked_path"])),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == [
        "openspec_archive_commit_failed",
        "git_signature_untrusted",
        "git_signer_unbound",
    ]
    assert compensated == [ARCHIVE_PATH]


@pytest.mark.parametrize(
    ("path", "change", "collision", "compensated_path"),
    [
        ("/outside", CHANGE, False, ""),
        (".", CHANGE, False, ""),
        ("unrelated", CHANGE, False, ""),
        (ARCHIVE_PATH, "other", False, ""),
        ("", "other", False, ""),
        ("", "other", True, f"{ARCHIVE_PATH}.preserved"),
    ],
)
def test_archive_public_rejects_invalid_native_receipt(
    monkeypatch, tmp_path, path, change, collision, compensated_path
):
    result = official_archive_result(tmp_path, change=change, path=path)
    stub_archive_public(monkeypatch, tmp_path, result=result, collision=collision)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)
    compensated: list[str] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(str(kwargs["untracked_path"])),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_archive_result_invalid"]
    assert_lifecycle_outcome(
        report,
        "mutated",
        "completed",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} "
        f"--subject 'chore(openspec): archive {CHANGE}' --apply --json",
    )
    assert compensated == [compensated_path]


@pytest.mark.parametrize("failure", ["restore", "unowned"])
def test_archive_public_reports_failed_compensation_and_retained_residue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    stub_archive_public(
        monkeypatch,
        repo,
        result={
            "exit_code": 0,
            "parse_error": "",
            "json": {"archive": {"change": "other", "path": ""}},
        },
    )
    marker = repo / "unrelated/keep.txt"
    marker.parent.mkdir()
    marker.write_text("preserve unrelated bytes\n")

    def compensate(root, **kwargs):
        if failure == "restore":
            message = "restore_failed"
            raise ValueError(message)
        git_effects.compensate_git_worktree(
            root, head=head, untracked_path=kwargs["untracked_path"]
        )

    monkeypatch.setattr(archive, "compensate_git_worktree", compensate)

    report = archive.archive_change(root=repo, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == [
        "openspec_archive_result_invalid",
        "openspec_archive_compensation_failed",
    ]
    assert_lifecycle_outcome(
        report,
        "mutated",
        "failed",
        "retained",
        "ethos lane status --json",
        user_decision_required=True,
    )
    assert report["compensation_error"] == (
        "restore_failed" if failure == "restore" else "git_effect_compensation_residue"
    )
    assert marker.read_text() == "preserve unrelated bytes\n"
    assert git(repo, "rev-parse", "HEAD") == head


def test_archive_zero_effect_preflight_has_no_compensation_gap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(
        archive,
        "_archive_coordinate_gaps",
        lambda *_args, **_kwargs: [f"work_lane_missing_lease:{BRANCH}"],
    )
    compensated: list[object] = []
    monkeypatch.setattr(
        archive, "compensate_git_worktree", lambda *_args, **kwargs: compensated.append(kwargs)
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == "lease_missing"
    assert report["required_gaps"] == [f"work_lane_missing_lease:{BRANCH}"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        "ethos lane status --json",
        user_decision_required=True,
    )
    assert compensated == []
    required_gaps = report["required_gaps"]
    assert isinstance(required_gaps, list)
    assert not any("compensation" in gap or "cleanup" in gap for gap in required_gaps)


@pytest.mark.parametrize(
    "invalid_postimage",
    [
        None,
        ArchivePostimage(CHANGE, HEAD, None, active_present=True),
        ArchivePostimage(CHANGE, HEAD, None, active_present=False),
    ],
)
def test_archive_public_compensates_unrecognized_official_output(
    monkeypatch, tmp_path, invalid_postimage
):
    stub_archive_public(monkeypatch, tmp_path)
    images = iter((ArchivePostimage(CHANGE, HEAD, None, active_present=True), invalid_postimage))
    monkeypatch.setattr(archive, "archive_postimage", lambda *_args, **_kwargs: next(images))
    removed = []
    monkeypatch.setattr(
        archive, "compensate_git_worktree", lambda _root, **kwargs: removed.append(kwargs)
    )
    result = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)
    assert result["required_gaps"] == ["openspec_archive_delta_invalid"]
    assert result["compensation_state"] == "completed"
    assert removed == [{"head": HEAD, "untracked_path": ARCHIVE_PATH}]

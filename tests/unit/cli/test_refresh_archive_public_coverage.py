from __future__ import annotations

from dataclasses import replace
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
import ethos.adapters.mutation.lane_lifecycle.change_overlay as overlay
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.openspec.lifecycle.archive_transition import ArchivePostimage
from ethos.repository.policy.commit import CommitPolicy
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.openspec_lifecycle import assert_lifecycle_outcome
from tests.support.semantic import commitment_fixture

BRANCH = "work/feature"
HEAD = "old-head"
NEW_HEAD = "new-head"
CHANGE = "fixture-change"
ARCHIVE_DATE = datetime.now(UTC).date().isoformat()
ARCHIVE_PATH = f"openspec/changes/archive/{ARCHIVE_DATE}-fixture-change"


def _completed_governance(
    *, remaining: int = 0, required_gaps: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "required_gaps": list(required_gaps),
        "lifecycle": {"changes": [{"name": CHANGE, "progress": {"remaining": remaining}}]},
        "commands": {"status": {"json": {"changes": []}}},
    }


def _current_authority() -> CurrentAuthority:
    return CurrentAuthority(
        verdict="pass",
        reason="matched",
        branch=BRANCH,
        actor="agent:test",
        lease={
            "lease_state": "valid",
            "lane_ref": BRANCH,
            "holder_ref": "agent:test",
            "generation": 1,
            "expires_at": "2099-01-01T00:00:00Z",
        },
        current_head=HEAD,
        current_tree="source-tree",
    )


def _archive_result(
    root: Path, *, change: str = CHANGE, path: str = ARCHIVE_PATH
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


def _stub_archive_public(
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
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: HEAD)
    authority = _current_authority()

    def observe_workspace(*_args: object, **_kwargs: object):
        if invocations is not None:
            invocations.append("workspace")
        return {"branch": BRANCH, "head": HEAD, "role": "work_lane"}, authority

    def resolve_current(*_args: object, **_kwargs: object) -> CurrentResolution:
        if invocations is not None:
            invocations.append("resolution")
        return resolution or CurrentResolution(
            verdict="block" if resolution_gaps else "pass",
            authority=authority,
            commitment=(None if resolution_gaps else commitment_fixture(id=f"change:{CHANGE}")),
            scope=CurrentScope(()),
            openspec=_completed_governance(
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
            ("branch", "--show-current"): BRANCH,
            ("status", "--short"): "",
            ("diff", "--cached", "--name-only", "--diff-filter=ACMRTD"): (
                f"{ARCHIVE_PATH}/proposal.md"
            ),
            ("write-tree",): "archive-tree",
            ("show", "-s", "--format=%ct", NEW_HEAD): "0",
        }.get(args, "")

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(archive_effect, "git_stdout", git_stdout)

    def collision_report(*_args: object) -> archive.ArchiveCollision | None:
        preserved = root / f"{ARCHIVE_PATH}.preserved"
        if not collision:
            return None
        if preserved.exists():
            message = "openspec_archive_collision_preservation_conflict"
            raise ValueError(message)
        return archive.ArchiveCollision(ARCHIVE_PATH, "archive-tree", f"{ARCHIVE_PATH}.preserved")

    monkeypatch.setattr(archive, "archive_collision", collision_report)
    postimages = iter(
        (
            ArchivePostimage(
                change=CHANGE,
                head=HEAD,
                scope=None,
                active_present=True,
            ),
            ArchivePostimage(
                change=CHANGE,
                head=HEAD,
                scope={
                    "archive_path": ARCHIVE_PATH,
                    "changed_paths": (f"{ARCHIVE_PATH}/proposal.md",),
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
        lambda *_args: result or _archive_result(root),
    )
    monkeypatch.setattr(archive, "dirty_changed_paths", lambda _root: ("spec.md",))
    monkeypatch.setattr(archive, "normalize_projected_specs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(archive_effect, "stage_git_worktree", lambda *_args, **_kwargs: None)


@pytest.mark.parametrize(
    ("subject", "gap"),
    [
        (None, "archive_commit_subject_required"),
        ("invalid", "commit_subject_invalid:invalid"),
        ("release: archive fixture-change", ""),
    ],
)
def test_archive_subject_is_admitted_before_native_mutation(monkeypatch, tmp_path, subject, gap):
    _stub_archive_public(monkeypatch, tmp_path)
    policy = CommitPolicy(
        subject_pattern=r"^release: .+", signing_required=True, signing_format="ssh"
    )
    monkeypatch.setattr(archive, "load_commit_policy", lambda _root: policy)
    observed = {}
    monkeypatch.setattr(
        archive_effect,
        "commit_archive_postimage",
        lambda *_a, **kw: observed.update(kw) or {"state": "archived"},
    )
    if gap:
        monkeypatch.setattr(
            archive.openspec_cli,
            "run_json",
            lambda *_a: pytest.fail("subject must be admitted before mutation"),
        )
    report = archive.archive_change(
        root=tmp_path, change=CHANGE, expect_head=HEAD, subject=subject, apply=True
    )
    if gap:
        assert report["required_gaps"] == [gap]
        assert report["user_decision_required"] is True
        assert "--subject" in report["next_action"]
        assert observed == {}
    else:
        assert report == {"state": "archived"}
        assert observed["subject"] == subject


def test_archive_public_observes_workspace_and_resolves_intent_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    invocations: list[str] = []
    _stub_archive_public(monkeypatch, tmp_path, invocations=invocations)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)

    assert report["state"] == "ready_to_archive"
    assert invocations == ["workspace", "resolution"]


def test_archive_public_preserves_current_resolution_recovery_action(monkeypatch, tmp_path):
    gap = f"invocation_actor_missing:{BRANCH}"
    resolution = CurrentResolution(
        verdict="block",
        authority=replace(_current_authority(), verdict="block", reason=gap, actor=""),
        commitment=None,
        scope=CurrentScope(()),
        required_gaps=(gap,),
        next_action="export ETHOS_ACTOR=agent:test",
    )
    invocations = []
    _stub_archive_public(monkeypatch, tmp_path, invocations=invocations, resolution=resolution)
    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)
    assert invocations == ["workspace", "resolution"]
    assert report["required_gaps"] == [gap]
    assert report["next_action"] == "export ETHOS_ACTOR=agent:test"
    assert report["user_decision_required"] is False


@pytest.mark.parametrize("collision", ["absent", "preserve", "tracked", "untracked"])
def test_archive_collision_observes_exact_git_and_preserves_existing_bytes(
    tmp_path, monkeypatch, collision
):
    repo = init_git_repo(tmp_path / "repo")
    source = repo / ARCHIVE_PATH / "proposal.md"
    source.parent.mkdir(parents=True)
    source.write_text("immutable archive\n")
    head = commit_fixture(repo, "archive fixture")
    if collision == "absent":
        assert archive.archive_collision(repo, head, "other") is None
        return
    if collision == "tracked":
        head = "HEAD"
    found = archive.archive_collision(repo, head, CHANGE)
    assert found.path == ARCHIVE_PATH
    assert found.tree == git(repo, "rev-parse", f"{head}:{ARCHIVE_PATH}")
    assert found.preserved_path.startswith(ARCHIVE_PATH + "-")
    if collision == "preserve":
        assert not (repo / found.preserved_path).exists()
        return
    marker = repo / found.preserved_path / "marker"
    marker.parent.mkdir(parents=True)
    marker.write_text("keep\n")
    if collision == "tracked":
        commit_fixture(repo, "retain prior collision")
    with pytest.raises(ValueError, match="openspec_archive_collision_preservation_conflict"):
        archive.archive_collision(repo, head, CHANGE)
    observe_collision = archive.archive_collision
    observe_git = archive.git_stdout
    _stub_archive_public(monkeypatch, repo)
    projected_git = archive.git_stdout
    monkeypatch.setattr(
        archive,
        "git_stdout",
        lambda root, *args: (observe_git if args[0] == "rev-parse" else projected_git)(root, *args),
    )
    monkeypatch.setattr(
        archive,
        "archive_collision",
        lambda root, _head, change: observe_collision(root, head, change),
    )
    monkeypatch.setattr(
        archive.openspec_cli, "run_json", lambda *_a: pytest.fail("collision mutated")
    )
    report = archive.archive_change(root=repo, change=CHANGE, expect_head=HEAD, apply=True)
    assert report["required_gaps"] == ["openspec_archive_collision_preservation_conflict"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        "ethos lane status --json",
        user_decision_required=True,
    )
    assert marker.read_text() == "keep\n"
    assert source.read_text() == "immutable archive\n"


def test_archive_public_preflight_preserves_all_current_resolution_gaps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(
        monkeypatch,
        tmp_path,
        remaining=1,
        resolution_gaps=("native_warning",),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)

    assert report["required_gaps"] == [
        "native_warning",
        f"openspec_change_incomplete:{CHANGE}",
    ]


def test_archive_public_missing_native_command_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
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


def test_archive_public_exception_compensates_exact_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(
        archive.openspec_cli,
        "run_json",
        lambda *_args: (_ for _ in ()).throw(ValueError("archive_failed")),
    )
    compensated: list[dict[str, object]] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(kwargs),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["archive_failed"]
    assert_lifecycle_outcome(
        report,
        "mutated",
        "completed",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} "
        f"--subject 'chore(openspec): archive {CHANGE}' --apply --json",
    )
    assert compensated == [{"head": HEAD, "untracked_path": ""}]


@pytest.mark.parametrize("collision", [False, True])
def test_archive_public_commit_failure_compensates_native_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, collision: bool
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, collision=collision)
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
    result = _archive_result(tmp_path, change=change, path=path)
    _stub_archive_public(monkeypatch, tmp_path, result=result, collision=collision)
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
    _stub_archive_public(
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


class _WorkLanePolicy:
    def role_for_branch(self, _branch: str) -> str:
        return "work_lane"


@pytest.mark.parametrize(
    ("lease", "actor", "expected_gap", "expected_state", "expected_action"),
    [
        (
            {},
            "agent:test",
            f"work_lane_missing_lease:{BRANCH}",
            "lease_missing",
            "ethos lane status --json",
        ),
        (
            {
                "lease_state": "expired",
                "lane_ref": BRANCH,
                "holder_ref": "agent:test",
                "generation": 7,
                "expires_at": "2026-08-20T00:00:00Z",
            },
            "agent:test",
            f"work_lane_lease_expired:{BRANCH}",
            "lease_expired",
            (
                "ethos lane lease resume --generation 7 "
                "--expires-at 2026-08-20T00:00:00Z "
                f"--branch {BRANCH} "
                "--holder-ref agent:test --apply --json"
            ),
        ),
        (
            {
                "lease_state": "valid",
                "lane_ref": BRANCH,
                "holder_ref": "agent:other",
                "generation": 1,
                "expires_at": "2026-08-30T00:00:00Z",
            },
            "agent:test",
            "lease_actor_mismatch",
            "different_holder",
            (
                "ethos attestation query --predicate lane-resolution:takeover "
                f"--subject git:branch:{BRANCH} --json"
            ),
        ),
    ],
)
def test_work_lane_transition_reports_the_first_exact_lease_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lease: dict[str, object],
    actor: str,
    expected_gap: str,
    expected_state: str,
    expected_action: str,
) -> None:
    monkeypatch.setattr(overlay, "load_branch_role_policy", lambda _root: _WorkLanePolicy())
    monkeypatch.setattr(overlay, "git_stdout", lambda *_args: "")

    gaps = overlay.work_lane_transition_gaps(
        tmp_path,
        branch=BRANCH,
        head=HEAD,
        expect_head=HEAD,
        lease=lease,
        actor=actor,
        role_gap="archive_requires_work_lane",
    )

    assert gaps == [expected_gap]
    report = archive.archive_preflight_report(BRANCH, HEAD, CHANGE, gaps, lease=lease)
    assert report["state"] == expected_state
    assert report["next_action"] == expected_action


def test_archive_zero_effect_preflight_has_no_compensation_gap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(
        archive,
        "_archive_coordinate_gaps",
        lambda *_args, **_kwargs: [f"work_lane_missing_lease:{BRANCH}"],
    )
    compensated: list[object] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda *_args, **kwargs: compensated.append(kwargs),
    )

    report = archive.archive_change(
        root=tmp_path,
        change=CHANGE,
        expect_head=HEAD,
        apply=True,
    )

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

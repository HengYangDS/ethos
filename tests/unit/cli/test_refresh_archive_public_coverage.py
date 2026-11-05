"""Exercise archive admission and preservation against explicit Git and clock inputs."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.openspec.lifecycle.archive_transition import ArchivePostimage
from ethos.repository.policy.commit import CommitPolicy
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.openspec_lifecycle import archive_authority
from tests.support.openspec_lifecycle import assert_lifecycle_outcome
from tests.support.openspec_lifecycle import completed_archive_governance
from tests.support.openspec_lifecycle import stub_archive_public
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

BRANCH = "work/feature"
HEAD = "old-head"
NEW_HEAD = "new-head"
CHANGE = "fixture-change"
ARCHIVE_PATH = "openspec/changes/archive/2026-09-10-fixture-change"


@pytest.mark.parametrize(
    ("subject", "gap"),
    [
        (None, "archive_commit_subject_required"),
        ("invalid", "commit_subject_invalid:invalid"),
        ("release: archive fixture-change", ""),
    ],
)
def test_archive_subject_is_admitted_before_native_mutation(monkeypatch, tmp_path, subject, gap):
    stub_archive_public(monkeypatch, tmp_path)
    policy = CommitPolicy(subject_pattern=r"^release: .+", signing_format="ssh")
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
        action = report["next_action"]
        assert isinstance(action, str)
        assert "--subject" in action
        assert observed == {}
    else:
        assert report == {"state": "archived"}
        assert observed["subject"] == subject


def test_archive_public_observes_workspace_and_resolves_intent_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    invocations: list[str] = []
    stub_archive_public(monkeypatch, tmp_path, invocations=invocations)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)

    assert report["state"] == "ready_to_archive"
    assert invocations == ["workspace", "resolution"]


def test_archive_preview_blocks_what_the_merged_specs_would_refuse(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The preview runs the proof's archive readiness on the head's tree and makes no effect."""
    stub_archive_public(monkeypatch, tmp_path)
    gap = f"openspec_archived_requirement_invalid:{CHANGE}:contracts:Governed fixture"
    simulated: list[tuple[str, str]] = []

    def readiness(_root: Path, *, change: str, tree: str) -> tuple[str, ...]:
        simulated.append((change, tree))
        return (gap,)

    monkeypatch.setattr(archive, "archive_readiness_gaps", readiness)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)

    assert (report["state"], report["required_gaps"]) == ("blocked", [gap])
    assert simulated == [(CHANGE, "source-tree")]


def test_archive_public_preserves_current_resolution_recovery_action(monkeypatch, tmp_path):
    gap = f"invocation_actor_missing:{BRANCH}"
    resolution = CurrentResolution(
        verdict="block",
        authority=replace(archive_authority(), verdict="block", reason=gap, actor=""),
        commitment=None,
        scope=CurrentScope(()),
        required_gaps=(gap,),
        next_action="export ETHOS_ACTOR=agent:test",
    )
    invocations = []
    stub_archive_public(monkeypatch, tmp_path, invocations=invocations, resolution=resolution)
    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)
    assert invocations == ["workspace", "resolution"]
    assert report["required_gaps"] == [gap]
    assert report["next_action"] == "export ETHOS_ACTOR=agent:test"
    assert report["user_decision_required"] is False


@pytest.mark.parametrize("collision", ["absent", "preserve", "tracked", "untracked"])
@pytest.mark.parametrize("archive_date", ["2026-09-10", "2026-09-11"])
def test_archive_collision_observes_exact_git_and_preserves_existing_bytes(
    tmp_path, monkeypatch, collision, archive_date
):
    observed_at = datetime.fromisoformat(archive_date).replace(tzinfo=UTC)
    monkeypatch.setattr(archive, "datetime", SimpleNamespace(now=observed_at.astimezone))
    archive_path = f"openspec/changes/archive/{archive_date}-{CHANGE}"
    repo = init_git_repo(tmp_path / "repo")
    source = repo / archive_path / "proposal.md"
    source.parent.mkdir(parents=True)
    source.write_text("immutable archive\n")
    head = commit_fixture(repo, "archive fixture")
    if collision == "absent":
        assert archive.archive_collision(repo, head, "other") is None
        return
    if collision == "tracked":
        head = "HEAD"
    found = archive.archive_collision(repo, head, CHANGE)
    assert found is not None
    assert found.path == archive_path
    assert found.tree == git(repo, "rev-parse", f"{head}:{archive_path}")
    assert found.preserved_path.startswith(archive_path + "-")
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
    stub_archive_public(monkeypatch, repo)
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
    stub_archive_public(
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


@pytest.mark.parametrize(
    "boundary",
    ["recovery", "role", "head", "commitment", "lifecycle", "postimage", "exception"],
)
def test_archive_public_rejects_invalid_coordinates_before_any_effect(
    monkeypatch, tmp_path, boundary
):
    stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(
        archive.openspec_cli, "run_json", lambda *_args: pytest.fail("preflight must not mutate")
    )
    expected = HEAD
    if boundary in {"recovery", "head"}:
        expected = "earlier-head"
        monkeypatch.setattr(
            archive_effect,
            "recover_archive_effect",
            lambda *_args, **_kwargs: {"state": "recognized"} if boundary == "recovery" else None,
        )
        gap = "expect_head_mismatch"
    elif boundary == "role":
        monkeypatch.setattr(
            archive,
            "workspace_status_observation",
            lambda *_args, **_kwargs: (
                {"branch": BRANCH, "head": HEAD, "role": "accepted_root"},
                archive_authority(),
            ),
        )
        gap = "archive_requires_work_lane"
    elif boundary in {"commitment", "lifecycle"}:
        resolution = CurrentResolution(
            verdict="pass",
            authority=archive_authority(),
            commitment=None
            if boundary == "commitment"
            else commitment_fixture(id=f"change:{CHANGE}"),
            scope=CurrentScope(()),
            openspec=completed_archive_governance() if boundary == "commitment" else {},
        )
        monkeypatch.setattr(
            archive, "resolve_current_resolution", lambda *_args, **_kwargs: resolution
        )
        gap = (
            f"commitment_invalid:{CHANGE}"
            if boundary == "commitment"
            else f"openspec_change_incomplete:{CHANGE}"
        )
    elif boundary == "postimage":
        monkeypatch.setattr(archive, "archive_postimage", lambda *_args, **_kwargs: None)
        gap = "openspec_archive_delta_invalid"
    else:

        def refuse(*_args, **_kwargs):
            message = "postimage_unavailable"
            raise ValueError(message)

        monkeypatch.setattr(archive, "archive_postimage", refuse)
        gap = "postimage_unavailable"
    result = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=expected, apply=True)
    if boundary == "recovery":
        assert result == {"state": "recognized"}
    else:
        assert result["required_gaps"] == [gap]
        assert result["effect_state"] == "zero_effect"
        assert result["residue_state"] == "absent"


@pytest.mark.parametrize(
    "mode", ["ready", "missing_commitment", "incomplete", "missing_lifecycle", "dirty"]
)
def test_archive_public_staged_and_active_readiness_are_distinct(monkeypatch, tmp_path, mode):
    stub_archive_public(monkeypatch, tmp_path)
    resolution = CurrentResolution(
        verdict="pass",
        authority=archive_authority(),
        commitment=None
        if mode == "missing_commitment"
        else commitment_fixture(id=f"change:{CHANGE}"),
        scope=CurrentScope(()),
        openspec={}
        if mode == "missing_lifecycle"
        else completed_archive_governance(remaining=1 if mode == "incomplete" else 0),
    )
    monkeypatch.setattr(archive, "resolve_current_resolution", lambda *_args, **_kwargs: resolution)
    if mode in {"ready", "missing_commitment"}:
        postimage = ArchivePostimage(
            CHANGE,
            HEAD,
            {"archive_path": ARCHIVE_PATH, "changed_paths": [f"{ARCHIVE_PATH}/tasks.md"]},
            active_present=False,
        )
        monkeypatch.setattr(archive, "archive_postimage", lambda *_args, **_kwargs: postimage)
    elif mode == "dirty":
        monkeypatch.setattr(archive, "git_stdout", lambda *_args: " M user-content")
    monkeypatch.setattr(
        archive.openspec_cli, "run_json", lambda *_args: pytest.fail("readiness is read only")
    )
    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)
    gap = {
        "ready": "",
        "missing_commitment": f"commitment_invalid:{CHANGE}",
        "dirty": "work_lane_dirty",
    }.get(mode, f"openspec_change_incomplete:{CHANGE}")
    assert report["required_gaps"] == ([gap] if gap else [])
    assert report["effect_state"] == "zero_effect"
    if mode == "ready":
        assert report["state"] == "ready_to_finalize_archive"
        assert report["archive_path"] == ARCHIVE_PATH

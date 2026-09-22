"""Bind archive execution to selected intent and report recoverable failures."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _plan(
    *,
    branch: str = "work/change",
    change: str = "change",
    archive_path: str = "openspec/changes/archive/change",
    changed_paths: list[str] | None = None,
):
    effect = GitEffect(
        updates={f"refs/heads/{branch}": GitRefUpdate(expected="a" * 40, desired="b" * 40)}
    )
    facts = Facts(
        repository="repository:test",
        head="a" * 40,
        tree="c" * 40,
        observed_at=datetime(2026, 8, 29, tzinfo=UTC),
        values={
            "refs": {f"refs/heads/{branch}": "a" * 40},
            "assertions": {},
            "archive_path": archive_path,
            "changed_paths": ["x"] if changed_paths is None else changed_paths,
        },
    )
    return compile_git_effect_plan(
        None,
        facts,
        prior_attestations={},
        policy={
            "operation": "git.ref.compare-and-swap",
            "transition": "openspec.archive",
            "branch": branch,
            "change": change,
        },
        effect=effect,
    )


@pytest.mark.parametrize("boundary", ["parent", "postimage"])
def test_archive_plan_rejects_parent_and_postimage_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    monkeypatch.setattr(
        archive_effect,
        "git_stdout",
        lambda _root, command, *_args: (
            "not-parent" if boundary == "parent" else "a" * 40 if command == "rev-parse" else "x"
        ),
    )
    monkeypatch.setattr(archive_effect, "current_tree", lambda *_args: "c" * 40)
    monkeypatch.setattr(archive_effect, "archive_postimage_scope_report", lambda *_a, **_k: None)

    gap = "parent_mismatch" if boundary == "parent" else "invalid"
    with pytest.raises(ValueError, match=f"openspec_archive_target_{gap}"):
        archive_effect.compile_archive_plan(
            tmp_path,
            "work/change",
            "change",
            "a" * 40,
            "b" * 40,
            {},
            commitment=commitment_fixture(id="change:change"),
        )


def test_archive_plan_uses_the_resolved_commitment_without_reloading_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commitment = commitment_fixture(id="change:change")
    monkeypatch.setattr(
        archive_effect,
        "load_profile_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("archive effect planning must not reload Commitment")
        ),
        raising=False,
    )
    monkeypatch.setattr(
        archive_effect,
        "git_stdout",
        lambda _root, command, *_args: (
            "a" * 40 if command == "rev-parse" else "openspec/changes/archive/change/proposal.md"
        ),
    )
    monkeypatch.setattr(archive_effect, "current_tree", lambda *_args: "c" * 40)
    monkeypatch.setattr(
        archive_effect,
        "archive_postimage_scope_report",
        lambda *_args, **_kwargs: {
            "verdict": "pass",
            "archive_path": "openspec/changes/archive/change",
        },
    )
    monkeypatch.setattr(
        archive_effect,
        "compile_observed_git_effect",
        lambda _root, selected, *_args, **_kwargs: selected,
    )

    selected = archive_effect.compile_archive_plan(
        tmp_path,
        "work/change",
        "change",
        "a" * 40,
        "b" * 40,
        {},
        commitment=commitment,
    )

    assert selected is commitment


def test_archive_effect_owns_postimage_commit_and_reuses_resolved_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commitment = commitment_fixture(id="change:change")
    plan = _plan()
    archive_path = "openspec/changes/archive/change"
    changed_path = f"{archive_path}/proposal.md"
    write_trees = iter(("original-index-tree", "archive-tree"))
    observed: dict[str, object] = {}

    def git_stdout(_root: Path, *args: str) -> str:
        if args == ("write-tree",):
            return next(write_trees)
        if args == ("diff", "--cached", "--name-only", "--diff-filter=ACMRTD"):
            return changed_path
        raise AssertionError(args)

    monkeypatch.setattr(archive_effect, "git_stdout", git_stdout)
    monkeypatch.setattr(
        archive_effect,
        "stage_git_worktree",
        lambda _root, *, previous: observed.update(staged_from=previous),
        raising=False,
    )
    monkeypatch.setattr(
        archive_effect,
        "create_git_commit",
        lambda _root, **kwargs: (
            observed.update(commit=kwargs)
            or SimpleNamespace(returncode=0, stdout="b" * 40, stderr="")
        ),
        raising=False,
    )

    def compile_plan(*_args: object, **kwargs: object):
        observed["commitment"] = kwargs["commitment"]
        return plan

    monkeypatch.setattr(archive_effect, "compile_archive_plan", compile_plan)
    monkeypatch.setattr(
        archive_effect,
        "complete_archive",
        lambda *_args, **kwargs: observed.update(completion=kwargs) or {"state": "archived"},
    )

    report = archive_effect.commit_archive_postimage(
        tmp_path,
        "work/change",
        "change",
        "a" * 40,
        {
            "archive_path": archive_path,
            "changed_paths": (changed_path,),
            "tree": "archive-tree",
        },
        commitment=commitment,
        lease={"holder_ref": "agent:test"},
        owned_mutation=True,
        compensation_path=archive_path,
        subject="chore(openspec): archive change",
    )

    assert report == {"state": "archived"}
    assert observed["staged_from"] == "a" * 40
    assert observed["commitment"] is commitment
    assert observed["commit"] == {
        "tree": "archive-tree",
        "parent": "a" * 40,
        "message": "chore(openspec): archive change",
    }
    assert observed["completion"] == {"apply": True, "result": None}


@pytest.mark.parametrize("failure", ["missing", "pending", "index-drift", "concurrent-content"])
def test_archive_projection_completion_rejects_drift_and_preserves_caller_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Finalization cannot commit an unverified rendering or erase a later writer."""
    projection = tmp_path / "projection.json"
    projection.write_bytes(b"before")
    trees = iter(("prior-index", "native-tree", "different-tree"))
    observed: list[str] = []
    monkeypatch.setattr(
        archive_effect,
        "git_stdout",
        lambda _root, *args: next(trees) if args == ("write-tree",) else "archive/tasks.md",
    )
    monkeypatch.setattr(archive_effect, "stage_git_worktree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        archive_effect,
        "restore_git_index",
        lambda _root, *, tree: observed.append(tree),
    )
    monkeypatch.setattr(
        archive_effect,
        "archive_projection_updates",
        lambda *_args, **_kwargs: {"projection.json": b"after"},
    )
    monkeypatch.setattr(
        archive_effect,
        "refresh_archive_projections",
        lambda *_args, **_kwargs: projection.write_bytes(
            b"other writer" if failure == "concurrent-content" else b"after"
        ),
    )
    scope = {"tree": "completed-tree"}
    if failure == "pending":
        scope["pending_projection_paths"] = ["projection.json"]
    monkeypatch.setattr(
        archive_effect,
        "archive_postimage",
        lambda *_args, **_kwargs: (
            None if failure in {"missing", "concurrent-content"} else SimpleNamespace(scope=scope)
        ),
    )
    monkeypatch.setattr(
        archive_effect,
        "create_git_commit",
        lambda *_args, **_kwargs: pytest.fail("unverified postimage reached commit"),
    )
    gap = (
        "archive_projection_compensation_conflict"
        if failure == "concurrent-content"
        else "openspec_archive_delta_changed"
        if failure == "index-drift"
        else "archive_projection_completion_invalid"
    )
    with pytest.raises(ValueError, match=gap):
        archive_effect.commit_archive_postimage(
            tmp_path,
            "work/change",
            "change",
            "a" * 40,
            {
                "tree": "native-tree",
                "changed_paths": ["archive/tasks.md"],
                "pending_projection_paths": ["projection.json"],
            },
            commitment=commitment_fixture(id="change:change"),
            lease={},
            owned_mutation=False,
            compensation_path="archive",
            subject="chore(openspec): archive change",
        )
    assert observed == ["prior-index"]
    assert projection.read_bytes() == (
        b"other writer" if failure == "concurrent-content" else b"before"
    )


def test_archive_effect_owns_durable_recovery_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan()
    observed: dict[str, object] = {}
    monkeypatch.setattr(
        archive_effect,
        "recover_plan",
        lambda _root, **kwargs: observed.update(recovery=kwargs) or plan,
    )
    monkeypatch.setattr(
        archive_effect,
        "complete_archive",
        lambda *_args, **kwargs: observed.update(completion=kwargs) or {"state": "recognized"},
    )

    report = archive_effect.recover_archive_effect(
        tmp_path,
        branch="work/change",
        head="b" * 40,
        change="change",
        apply=True,
    )

    assert report == {"state": "recognized"}
    assert observed["recovery"] == {
        "operation": "openspec.archive",
        "desired": "b" * 40,
        "ref_name": "refs/heads/work/change",
    }
    assert observed["completion"] == {"apply": True}


@pytest.mark.parametrize("fault", ["identity", "facts"])
def test_archive_completion_rejects_plan_identity_and_required_facts(tmp_path: Path, fault) -> None:
    branch = "work/other" if fault == "identity" else "work/change"
    plan = _plan() if fault == "identity" else _plan(archive_path="", changed_paths=[])
    gap = "mismatch" if fault == "identity" else "facts_invalid"
    with pytest.raises(ValueError, match=f"openspec_archive_plan_{gap}"):
        archive_effect.complete_archive(tmp_path, branch, "change", plan, "b" * 40, apply=False)


@pytest.mark.parametrize("gap", ["openspec_invalid", "proof_not_proven"])
def test_archive_completion_reports_recovery_and_governance_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gap: str
) -> None:
    plan = _plan()
    monkeypatch.setattr(archive_effect, "leases_by_branch", lambda _root: {})
    monkeypatch.setattr(archive_effect, "current_tracked_head", lambda _root: "a" * 40)

    ready = archive_effect.complete_archive(
        tmp_path, "work/change", "change", plan, "b" * 40, apply=False
    )
    assert ready["state"] == "ready_to_recover"

    monkeypatch.setattr(
        archive_effect,
        "execute_git_effect",
        lambda *_args, **_kwargs: SimpleNamespace(
            model_dump=lambda **_kwargs: {"predicate": "effect:git-ref-update"}
        ),
    )
    monkeypatch.setattr(
        archive_effect,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"required_gaps": [gap] if gap == "openspec_invalid" else []},
    )
    proof = Mock(return_value=[gap])
    monkeypatch.setattr(archive_effect, "proof_gaps", proof, raising=False)

    blocked = archive_effect.complete_archive(
        tmp_path, "work/change", "change", plan, "b" * 40, apply=True
    )
    assert (blocked["state"], blocked["required_gaps"]) == (
        "repair_required",
        [gap],
    )
    if gap == "proof_not_proven":
        proof.assert_called_once_with(tmp_path, "b" * 40, change_id="change")
        assert f"--expect-head {'b' * 40}" in blocked["next_action"]

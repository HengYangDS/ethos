from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

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


def test_archive_plan_rejects_parent_and_postimage_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(archive_effect, "git_stdout", lambda *_args: "not-parent")

    with pytest.raises(ValueError, match="openspec_archive_target_parent_mismatch"):
        archive_effect.compile_archive_plan(
            tmp_path,
            "work/change",
            "change",
            "a" * 40,
            "b" * 40,
            {},
            commitment=commitment_fixture(id="change:change"),
        )

    monkeypatch.setattr(
        archive_effect,
        "git_stdout",
        lambda _root, command, *_args: "a" * 40 if command == "rev-parse" else "x",
    )
    monkeypatch.setattr(archive_effect, "current_tree", lambda *_args: "c" * 40)
    monkeypatch.setattr(archive_effect, "archive_postimage_scope_report", lambda *_a, **_k: None)

    with pytest.raises(ValueError, match="openspec_archive_target_invalid"):
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
        "lifecycle_commit_subject",
        lambda *_args: "chore(openspec): archive change",
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


def test_archive_effect_owns_durable_recovery_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan()
    observed: dict[str, object] = {}
    monkeypatch.setattr(
        archive_effect,
        "recover_plan",
        lambda _root, **kwargs: observed.update(recovery=kwargs) or plan,
        raising=False,
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


def test_archive_completion_rejects_plan_identity_and_required_facts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="openspec_archive_plan_mismatch"):
        archive_effect.complete_archive(
            tmp_path, "work/other", "change", _plan(), "b" * 40, apply=False
        )

    invalid = _plan(archive_path="", changed_paths=[])
    with pytest.raises(ValueError, match="openspec_archive_plan_facts_invalid"):
        archive_effect.complete_archive(
            tmp_path, "work/change", "change", invalid, "b" * 40, apply=False
        )


def test_archive_completion_reports_recovery_and_governance_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        lambda *_args, **_kwargs: type(
            "Attestation",
            (),
            {"model_dump": lambda *_args, **_kwargs: {"predicate": "effect:git-ref-update"}},
        )(),
    )
    monkeypatch.setattr(
        archive_effect,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"required_gaps": ["openspec_invalid"]},
    )

    blocked = archive_effect.complete_archive(
        tmp_path, "work/change", "change", plan, "b" * 40, apply=True
    )
    assert (blocked["state"], blocked["required_gaps"]) == (
        "repair_required",
        ["openspec_invalid"],
    )

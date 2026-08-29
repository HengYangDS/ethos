from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts

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
            tmp_path, "work/change", "change", "a" * 40, "b" * 40, {}
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
            tmp_path, "work/change", "change", "a" * 40, "b" * 40, {}
        )


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

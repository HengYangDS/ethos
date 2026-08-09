# ruff: noqa: SLF001
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.change_rollover as rollover

if TYPE_CHECKING:
    from pathlib import Path


BRANCH = "work/feature"
HEAD = "a" * 40
ARCHIVE = "openspec/changes/archive/2026-08-10-finished/commitment.toml"


def _lease(**updates: object) -> dict[str, object]:
    lease: dict[str, object] = {
        "lease_state": "valid",
        "holder_ref": "agent:test",
        "expected_head": HEAD,
        "base_commitment_path": ARCHIVE,
    }
    lease.update(updates)
    return lease


def _common(monkeypatch: pytest.MonkeyPatch, lease: dict[str, object] | None = None) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test")
    monkeypatch.setattr(rollover, "git_stdout", lambda *_a, **_k: BRANCH)
    monkeypatch.setattr(rollover, "current_tracked_head", lambda _root: HEAD)
    monkeypatch.setattr(rollover, "leases_by_branch", lambda _root: {BRANCH: lease or _lease()})
    monkeypatch.setattr(rollover, "_recognized", lambda *_a: None)


def _start(root: Path, *, apply: bool = False) -> dict[str, object]:
    return rollover.start_change(
        root=root,
        change="next-change",
        intent="Continue exact governed work.",
        scope=("src/**",),
        expect_head=HEAD,
        apply=apply,
    )


def test_start_change_recovery_dry_run_and_finish_failure_are_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(rollover, "_recoverable", lambda *_a: ("openspec", "new"))
    ready = _start(tmp_path)
    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_recover")

    monkeypatch.setattr(rollover, "local_state_mutation_guard", lambda _root: {"required_gaps": []})
    monkeypatch.setattr(
        rollover,
        "_finish",
        lambda *_a: (_ for _ in ()).throw(ValueError("commitment_rebind_failed")),
    )
    failed = _start(tmp_path, apply=True)
    assert failed["required_gaps"] == ["commitment_rebind_failed"]
    assert failed["state"] == "repair_required"


def test_start_change_recovery_guard_falls_back_to_actionable_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(rollover, "_recoverable", lambda *_a: ("openspec", "new"))
    monkeypatch.setattr(
        rollover,
        "local_state_mutation_guard",
        lambda _root: {
            "required_gaps": ["local_state_migration_required"],
            "next_action": "ethos state migrate --json",
        },
    )
    monkeypatch.setattr(
        rollover,
        "_preflight",
        lambda *_a: (["preflight_would_have_run"], rollover._empty_overlay()),
    )
    report = _start(tmp_path, apply=True)
    assert report["required_gaps"] == ["preflight_would_have_run"]


def test_start_change_apply_guard_replaces_preflight_authority_gaps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(rollover, "_recoverable", lambda *_a: None)
    monkeypatch.setattr(rollover, "_preflight", lambda *_a: ([], rollover._empty_overlay()))
    monkeypatch.setattr(
        rollover,
        "local_state_mutation_guard",
        lambda _root: {
            "required_gaps": ["local_state_authority_mismatch"],
            "next_action": "ethos state reconcile --json",
        },
    )
    report = _start(tmp_path, apply=True)
    assert report["required_gaps"] == ["local_state_authority_mismatch"]
    assert report["next_action"] == "ethos state reconcile --json"


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("commitment", "lease_commitment_invalid"),
        ("missing-cli", "openspec_official_cli_missing"),
        ("unreadable-list", "openspec_list_unreadable"),
        ("active-list", "openspec_active_change_present"),
    ],
)
def test_start_change_preflight_rejects_unreadable_or_conflicting_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str, gap: str
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(rollover, "_recoverable", lambda *_a: None)
    monkeypatch.setattr(rollover, "work_lane_transition_gaps", lambda *_a, **_k: [])
    monkeypatch.setattr(
        rollover,
        "change_overlay_report",
        lambda *_a, **_k: {"paths": (), "digest": "", "required_gaps": []},
    )
    if case == "commitment":
        monkeypatch.setattr(
            rollover,
            "load_lease_bound_commitment",
            lambda *_a, **_k: (_ for _ in ()).throw(ValueError(gap)),
        )
    else:
        monkeypatch.setattr(rollover, "load_lease_bound_commitment", lambda *_a, **_k: object())
        monkeypatch.setattr(
            rollover.openspec_cli,
            "openspec_base_command",
            lambda: None if case == "missing-cli" else ("openspec",),
        )
        monkeypatch.setattr(
            rollover.openspec_cli,
            "run_json",
            lambda *_a, **_k: {
                "exit_code": 1 if case == "unreadable-list" else 0,
                "parse_error": "",
                "json": {
                    "changes": []
                    if case == "unreadable-list"
                    else [
                        {
                            "name": "unfinished",
                            "status": "no-tasks",
                            "completedTasks": 0,
                            "totalTasks": 0,
                        }
                    ]
                },
            },
        )
    report = _start(tmp_path)
    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize("case", ["missing-cli", "invalid-result", "commit-failed"])
def test_start_change_apply_compensates_partial_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(rollover, "_recoverable", lambda *_a: None)
    monkeypatch.setattr(rollover, "_preflight", lambda *_a: ([], rollover._empty_overlay()))
    monkeypatch.setattr(rollover, "local_state_mutation_guard", lambda _root: {"required_gaps": []})
    monkeypatch.setattr(
        rollover.openspec_cli,
        "openspec_base_command",
        lambda: None if case == "missing-cli" else ("openspec",),
    )
    change_root = tmp_path / "openspec/changes/next-change"
    change_root.mkdir(parents=True)
    (change_root / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    monkeypatch.setattr(
        rollover.openspec_cli,
        "run_json",
        lambda *_a, **_k: {"command": ["openspec"], "json": {}, "exit_code": 0},
    )
    monkeypatch.setattr(rollover, "_official_new_result", lambda *_a: case != "invalid-result")
    removed: list[str] = []
    compensated: list[str] = []
    monkeypatch.setattr(rollover, "remove_untracked_tree", lambda _r, path: removed.append(path))
    monkeypatch.setattr(rollover, "stage_git_paths", lambda *_a: None)
    monkeypatch.setattr(
        rollover,
        "commit_git_worktree",
        lambda *_a, **_k: {"verdict": "block" if case == "commit-failed" else "pass"},
    )
    monkeypatch.setattr(
        rollover,
        "compensate_created_paths",
        lambda *_a, **_k: compensated.append("compensated"),
    )
    report = _start(tmp_path, apply=True)
    expected = {
        "missing-cli": "openspec_official_cli_missing",
        "invalid-result": "openspec_change_create_failed",
        "commit-failed": "openspec_change_commit_failed",
    }[case]
    assert report["required_gaps"] == [expected]
    assert bool(removed) is (case == "invalid-result")
    assert bool(compensated) is (case == "commit-failed")


def test_start_change_skips_corrupt_receipt_and_invalid_recovery_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    store = tmp_path / "attestations"
    store.mkdir()
    (store / "corrupt.json").write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(rollover, "attestation_store_dir", lambda _root: store)
    monkeypatch.setattr(rollover, "run_git", lambda *_a, **_k: SimpleNamespace(stdout=HEAD + "\n"))
    monkeypatch.setattr(rollover, "git_stdout", lambda *_a, **_k: "")
    monkeypatch.setattr(
        rollover,
        "exact_commitment_fields",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("invalid target")),
    )
    monkeypatch.setattr(
        rollover, "_preflight", lambda *_a: (["not_recoverable"], rollover._empty_overlay())
    )
    report = _start(tmp_path)
    assert report["required_gaps"] == ["not_recoverable"]

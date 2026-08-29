from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.prewrite as prewrite
import ethos.adapters.repo.runtime.binding as runtime_binding_adapter

if TYPE_CHECKING:
    from pathlib import Path


def _status(root: Path, *, role: str = "work_lane") -> dict[str, object]:
    return {
        "root": root.as_posix(),
        "role": role,
        "branch": "work/example" if role == "work_lane" else "dev",
        "runtime_binding": {
            "audit_root": root.as_posix(),
            "runner_source_root": root.as_posix(),
            "schema_source_root": root.as_posix(),
            "runner_matches_audit_root": True,
            "schema_matches_audit_root": True,
        },
        "worktrees": [],
    }


def _bind_common(monkeypatch: pytest.MonkeyPatch, root: Path, *, role: str = "work_lane") -> None:
    monkeypatch.setattr(
        prewrite,
        "_prewrite_status",
        lambda _root, **_kwargs: _status(root, role=role),
    )
    monkeypatch.setattr(runtime_binding_adapter, "profile_gate_registry", lambda _root: False)
    monkeypatch.setattr(prewrite, "openspec_profile_enabled", lambda _root: False)
    monkeypatch.setattr(
        prewrite, "patch_admission", lambda **_kwargs: {"verdict": "pass", "reason": "matched"}
    )
    monkeypatch.setattr(prewrite, "_is_ignored", lambda _root, _path: False)


def test_prewrite_fails_closed_on_non_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prewrite, "git_stdout", lambda *_args: "")
    monkeypatch.setattr(
        prewrite,
        "runtime_binding",
        lambda root, **_kwargs: {"audit_root": str(root)},
    )
    monkeypatch.setattr(runtime_binding_adapter, "profile_gate_registry", lambda _root: True)
    monkeypatch.setattr(prewrite, "openspec_profile_enabled", lambda _root: False)
    monkeypatch.setattr(
        prewrite, "patch_admission", lambda **_kwargs: {"verdict": "pass", "reason": "matched"}
    )
    monkeypatch.setattr(prewrite, "_is_ignored", lambda _root, _path: False)

    report = prewrite.prewrite_guard(root=tmp_path, paths=[tmp_path / "README.md"])

    assert report["verdict"] == "block"
    assert report["runtime_binding"]["reason"] == "root_binding_mismatch"
    assert report["required_gaps"][0] == "root_binding_mismatch"
    assert report["decision"]["next_action"] == "repair_required_gap"


@pytest.mark.parametrize(
    ("editor_root", "require_editor_root_value", "reason"),
    [
        ("foreign", True, "editor_root_mismatch"),
        (None, True, "editor_root_missing"),
        (None, False, "not_checked"),
    ],
)
def test_prewrite_editor_authority_is_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    editor_root: str | None,
    require_editor_root_value: object,
    reason: str,
) -> None:
    _bind_common(monkeypatch, tmp_path, role="accepted_root")
    actual = tmp_path / editor_root if editor_root else None

    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[],
        editor_root=actual,
        require_editor_root=bool(require_editor_root_value),
    )

    assert report["editor_root"]["reason"] == reason
    assert report["verdict"] == ("block" if reason != "not_checked" else "pass")
    if report["verdict"] == "block":
        assert reason in report["required_gaps"]
        assert report["decision"]["next_action"] == "repair_required_gap"
        if reason == "editor_root_missing":
            assert report["next_action"] == (
                f"ethos lane prewrite <path> --editor-root {tmp_path} --require-editor-root --json"
            )


def test_prewrite_reports_outside_path_without_inventing_path_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path, role="accepted_root")
    outside = tmp_path.parent / "outside.txt"
    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[outside, tmp_path / "src/code.py"],
        editor_root=tmp_path,
    )

    assert report["verdict"] == "block"
    assert report["blocked_paths"][0]["reason"] == "path_outside_worktree"
    assert "prewrite_path_outside_worktree" in report["required_gaps"]
    assert report["material_scope"]["state"] == "not_applicable"
    assert report["material_scope"]["uncovered_paths"] == []


def test_prewrite_projects_unknown_openspec_scope_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path, role="accepted_root")
    monkeypatch.setattr(prewrite, "openspec_profile_enabled", lambda _root: True)
    monkeypatch.setattr(
        prewrite,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"verdict": "unknown", "required_gaps": ["carrier_unreadable"]},
    )

    report = prewrite.prewrite_guard(root=tmp_path, paths=[], editor_root=tmp_path)

    assert report["verdict"] == "unknown"
    assert report["material_scope"]["state"] == "not_available"
    assert report["material_scope"]["required_gaps"] == ["openspec_scope_unavailable"]
    assert report["required_gaps"] == ["openspec_scope_unavailable"]


def test_prewrite_combines_minimal_lease_with_official_openspec_attribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path)
    lease = {
        "verdict": "pass",
        "required": True,
        "reason": "matched",
        "holder_ref": "agent:test:case:owner",
        "generation": 1,
        "current_head": "a" * 40,
        "current_tree": "b" * 40,
    }
    monkeypatch.setattr(prewrite, "openspec_profile_enabled", lambda _root: True)
    monkeypatch.setattr(prewrite, "_work_lane_lease_check", lambda **_kwargs: lease)
    monkeypatch.setattr(
        prewrite,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "pass",
            "required_gaps": [],
            "lifecycle": {
                "scope_binding": {
                    "verdict": "pass",
                    "state": "attributed",
                    "changed_paths": ["README.md"],
                    "material_patterns": ["**"],
                    "material_paths": ["README.md"],
                    "changes": [{"name": "example"}],
                    "covered_paths": [{"path": "README.md", "changes": ["example"]}],
                    "uncovered_paths": [],
                    "required_gaps": [],
                    "advisory_gaps": [],
                }
            },
        },
    )
    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[tmp_path / "README.md"],
        editor_root=tmp_path,
    )

    assert report["verdict"] == "pass"
    assert report["material_scope"]["state"] == "attributed"


def test_prewrite_projects_only_minimal_lease_and_fresh_git_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path)
    lease = {
        "lease_state": "valid",
        "lane_ref": "work/example",
        "holder_ref": "agent:test:case:owner",
        "generation": 1,
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")
    monkeypatch.setattr(
        prewrite,
        "_work_lane_lease_check",
        lambda **_kwargs: {
            "verdict": "pass",
            "required": True,
            "reason": "matched",
            **lease,
            "current_head": "a" * 40,
            "current_tree": "b" * 40,
        },
    )

    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[tmp_path / "README.md"],
        editor_root=tmp_path,
    )

    projected = report["work_lane_lease"]
    assert isinstance(projected, dict)
    assert {name: projected[name] for name in lease} == lease
    assert projected["current_head"] == "a" * 40
    assert projected["current_tree"] == "b" * 40
    assert set(projected) == {
        "verdict",
        "required",
        "reason",
        "lane_ref",
        "holder_ref",
        "generation",
        "expires_at",
        "lease_state",
        "current_head",
        "current_tree",
    }

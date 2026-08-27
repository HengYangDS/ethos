from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.lease_binding as lease_binding
import ethos.adapters.admission.prewrite as prewrite
import ethos.adapters.repo.runtime.binding as runtime_binding_adapter
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


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


def _commitment(*scope: str) -> Commitment:
    return commitment_fixture(
        id="change:example",
        intent="Govern exact paths.",
        subjects=("repository:example",),
        scope=scope,
    )


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
    monkeypatch.setattr(prewrite, "load_commitment", lambda _root: _commitment("**"))
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
    monkeypatch.setattr(prewrite, "load_commitment", lambda _root: _commitment("**"))
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


def test_prewrite_reports_outside_path_and_exact_commitment_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path, role="accepted_root")
    monkeypatch.setattr(prewrite, "load_commitment", lambda _root: _commitment("*.md", "docs/**"))

    outside = tmp_path.parent / "outside.txt"
    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[outside, tmp_path / "src/code.py"],
        editor_root=tmp_path,
    )

    assert report["verdict"] == "block"
    assert report["blocked_paths"][0]["reason"] == "path_outside_worktree"
    assert "prewrite_path_outside_worktree" in report["required_gaps"]
    assert report["material_scope"]["uncovered_paths"] == ["src/code.py"]
    assert "commitment_scope_uncovered:src/code.py" in report["required_gaps"]


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


def test_prewrite_uses_lease_commitment_without_full_openspec_governance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path)
    lease = {
        "verdict": "pass",
        "required": True,
        "reason": "matched",
        "holder_ref": "agent:test:case:owner",
        "lease_id": "lease:test",
        "epoch": 1,
        "expected_head": "a" * 40,
        "scope": ["README.md"],
    }
    monkeypatch.setattr(prewrite, "openspec_profile_enabled", lambda _root: True)
    monkeypatch.setattr(prewrite, "_work_lane_lease_check", lambda **_kwargs: lease)
    monkeypatch.setattr(
        prewrite,
        "openspec_governance_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("prewrite_must_not_run_full_openspec_governance")
        ),
    )
    monkeypatch.setattr(prewrite, "archive_prewrite_authority", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        prewrite, "prepared_start_prewrite_authority", lambda *_args, **_kwargs: None
    )

    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[tmp_path / "README.md"],
        editor_root=tmp_path,
    )

    assert report["verdict"] == "pass"
    assert report["material_scope"]["state"] == "covered"


def test_prewrite_preserves_exact_lease_commitment_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path)
    lease = {
        "lease_state": "valid",
        "commitment_binding": "bound",
        "holder_ref": "agent:test:case:owner",
        "lease_id": "lease:test",
        "epoch": 1,
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
    }
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")
    monkeypatch.setattr(lease_binding, "git_stdout", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        lease_binding,
        "current_tree",
        lambda *_args, **_kwargs: "b" * 40,
    )
    monkeypatch.setattr(
        lease_binding, "leases_by_branch", lambda *_args, **_kwargs: {"work/example": lease}
    )
    monkeypatch.setattr(
        lease_binding,
        "load_lease_bound_commitment",
        lambda *_args, **_kwargs: _commitment("README.md"),
    )

    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[tmp_path / "README.md"],
        editor_root=tmp_path,
    )

    projected = report["work_lane_lease"]
    assert isinstance(projected, dict)
    coordinates = {
        name: lease[name]
        for name in (
            "holder_ref",
            "lease_id",
            "epoch",
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }
    assert {name: projected[name] for name in coordinates} == coordinates


def test_prewrite_surfaces_lease_commitment_binding_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_common(monkeypatch, tmp_path)
    lease = {
        "lease_state": "valid",
        "commitment_binding": "bound",
        "holder_ref": "agent:test:case:owner",
        "lease_id": "lease:test",
        "epoch": 1,
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
    }
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")
    monkeypatch.setattr(prewrite, "current_branch", lambda _root: "work/example")
    monkeypatch.setattr(lease_binding, "git_stdout", lambda *_args: "a" * 40)
    monkeypatch.setattr(lease_binding, "current_tree", lambda *_args: "b" * 40)
    monkeypatch.setattr(
        lease_binding, "leases_by_branch", lambda *_args, **_kwargs: {"work/example": lease}
    )
    monkeypatch.setattr(
        lease_binding,
        "load_lease_bound_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("lease_base_commitment_bytes_mismatch")
        ),
    )

    report = prewrite.prewrite_guard(
        root=tmp_path,
        paths=[tmp_path / "README.md"],
        editor_root=tmp_path,
    )

    gap = "lease_base_commitment_bytes_mismatch:work/example"
    assert report["verdict"] == "block"
    assert report["work_lane_lease"]["reason"] == gap
    assert gap in report["required_gaps"]

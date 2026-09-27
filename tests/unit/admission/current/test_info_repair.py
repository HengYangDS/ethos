"""Canonical INFO repair admission for active and archived OpenSpec intent."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.current.resolution as resolution_adapter
from tests.support.semantic import commitment_fixture
from tests.unit.admission.current.support import official_artifact
from tests.unit.admission.current.support import official_report
from tests.unit.admission.current.support import resolve_report

if TYPE_CHECKING:
    from pathlib import Path


def _canonical_info_report() -> dict[str, object]:
    """Model successful native validation with a repository-blocking spec finding."""
    report = official_report(
        change="repair-spec",
        gaps=("openspec_validation_issue:INFO:spec:quality:requirements[0]",),
        artifacts=(official_artifact("tasks", "tasks.md"),),
        commitment=commitment_fixture(id="change:repair-spec").model_dump(mode="json"),
        validate_payload={
            "items": [
                {
                    "id": "quality",
                    "type": "spec",
                    "valid": True,
                    "issues": [
                        {
                            "level": "INFO",
                            "path": "requirements[0]",
                            "message": "Requirement text is very long (> 500 characters).",
                        }
                    ],
                }
            ]
        },
    )
    report["commands"]["validate"]["exit_code"] = 0
    return report


@pytest.mark.parametrize("envelope", ["items", "itemFindings"])
def test_canonical_info_can_be_repaired_without_satisfying_ordinary_resolution(
    tmp_path: Path, monkeypatch, envelope: str
) -> None:
    path = "openspec/specs/quality/spec.md"
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_text("### Requirement: Long text\n", encoding="utf-8")
    report = _canonical_info_report()
    if envelope == "itemFindings":
        items = report["commands"]["validate"]["json"]["items"]
        report["commands"]["validate"]["json"] = {
            "report": {
                "kind": "validation-findings",
                "version": "1.0",
                "returnedItems": 1,
                "totalItems": 1,
            },
            "itemFindings": items,
        }
    repair = resolve_report(monkeypatch, report, root=tmp_path, paths=(path,))
    assert repair.verdict == "pass"
    assert repair.scope.material_scope["state"] == "canonical_spec_repair"
    assert repair.scope_report((path,))["authorized_paths"] == [path]
    ordinary = resolve_report(monkeypatch, report, root=tmp_path)
    assert ordinary.verdict == "block"
    assert ordinary.required_gaps == (
        "openspec_validation_issue:INFO:spec:quality:requirements[0]",
    )
    assert "ethos lane prewrite" in ordinary.next_action
    assert path in ordinary.next_action


def test_valid_canonical_info_does_not_preempt_unrelated_change_authoring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A final proof gap must not monopolize an otherwise admitted source write."""
    canonical = tmp_path / "openspec/specs/quality/spec.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("### Requirement: Long text\n", encoding="utf-8")
    path = "src/feature.py"
    report = _canonical_info_report()
    report["lifecycle"]["scope_binding"] = {
        "verdict": "pass",
        "state": "attributed",
        "changed_paths": [path],
        "material_patterns": ["**"],
        "material_paths": [path],
        "changes": [{"name": "repair-spec"}],
        "covered_paths": [{"path": path, "changes": ["repair-spec"]}],
        "uncovered_paths": [],
        "required_gaps": [],
        "advisory_gaps": [],
    }

    authoring = resolve_report(monkeypatch, report, root=tmp_path, paths=(path,))
    assert authoring.verdict == "pass"
    assert authoring.scope_report((path,))["covered_paths"] == [
        {"path": path, "changes": ["repair-spec"]}
    ]
    assert authoring.openspec["required_gaps"] == report["required_gaps"]
    assert resolve_report(monkeypatch, report, root=tmp_path).verdict == "block"
    report["lifecycle"]["scope_binding"]["required_gaps"] = [
        f"openspec_material_path_uncovered:{path}"
    ]
    report["lifecycle"]["scope_binding"]["verdict"] = "block"
    assert resolve_report(monkeypatch, report, root=tmp_path, paths=(path,)).verdict == "block"
    report["commitment"] = {}
    assert resolve_report(monkeypatch, report, root=tmp_path, paths=(path,)).verdict == "block"


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "symlink",
        "mismatch",
        "bad-envelope",
        "bad-exit",
        "duplicate-id",
        "colon-id",
        "mixed",
        "other-path",
    ],
)
def test_canonical_info_repair_rejects_unsupported_evidence_or_paths(
    tmp_path: Path, monkeypatch, mode: str
) -> None:
    path = "openspec/specs/quality/spec.md"
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    if mode == "symlink":
        target.symlink_to(tmp_path / "outside.md")
    elif mode != "missing":
        target.write_text("### Requirement: Long text\n", encoding="utf-8")
    report = _canonical_info_report()
    if mode == "mismatch":
        report["commands"]["validate"]["json"]["items"][0]["id"] = "other"
    elif mode == "bad-envelope":
        report["commands"]["validate"]["json"] = {"itemFindings": []}
    elif mode == "bad-exit":
        report["commands"]["validate"]["exit_code"] = 1
    elif mode == "duplicate-id":
        report["required_gaps"].append(
            "openspec_validation_issue:INFO:spec:quality:requirements[1]"
        )
        report["commands"]["validate"]["json"]["items"].append(
            {
                "id": "quality",
                "type": "spec",
                "valid": True,
                "issues": [{"level": "INFO", "path": "requirements[1]"}],
            }
        )
    elif mode == "colon-id":
        report["required_gaps"] = [
            "openspec_validation_issue:INFO:spec:quality:spoof:requirements[0]"
        ]
        report["commands"]["validate"]["json"]["items"][0]["id"] = "quality:spoof"
    requested = (
        (path, "src/ethos/unrelated.py")
        if mode == "mixed"
        else ("openspec/specs/unrelated/spec.md",)
        if mode == "other-path"
        else (path,)
    )
    repair = resolve_report(monkeypatch, report, root=tmp_path, paths=requested)
    assert repair.verdict == "block"
    assert repair.scope_report(requested).get("authorized_paths", []) != list(requested)


@pytest.mark.parametrize(
    "mode",
    [
        "valid",
        "missing-archive",
        "unrelated-output",
        "wrong-change",
        "mixed-path",
        "extra-gap",
        "bad-exit",
        "symlink",
    ],
)
def test_archived_info_repair_requires_exact_validated_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """Two INFO findings grant one archived output, never broader write authority."""
    path = "openspec/specs/quality/spec.md"
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    if mode == "symlink":
        target.symlink_to(tmp_path / "outside.md")
    else:
        target.write_text("### Requirement: Long text\n", encoding="utf-8")
    report = _canonical_info_report()
    report["commitment"] = {}
    report["lifecycle"]["changes"] = []
    second = "openspec_validation_issue:INFO:spec:quality:requirements[1]"
    report["required_gaps"].append(second)
    report["commands"]["validate"]["json"]["items"][0]["issues"].append(
        {"level": "INFO", "path": "requirements[1]"}
    )
    if mode == "extra-gap":
        report["required_gaps"].append("openspec_doctor_unhealthy")
    elif mode == "bad-exit":
        report["commands"]["validate"]["exit_code"] = 1
    archived = (
        commitment_fixture(id="change:other" if mode == "wrong-change" else "change:repair-spec"),
        {"authorized_paths": [] if mode == "unrelated-output" else [path]},
    )
    monkeypatch.setattr(
        resolution_adapter,
        "attested_archive_transition",
        lambda *_args, **_kwargs: None if mode == "missing-archive" else archived,
    )
    paths = (path, "src/unrelated.py") if mode == "mixed-path" else (path,)
    repair = resolve_report(monkeypatch, report, root=tmp_path, paths=paths)
    assert repair.verdict == ("pass" if mode == "valid" else "block")
    if mode == "valid":
        assert repair.scope_report(paths)["authorized_paths"] == [path]
        ordinary = resolve_report(monkeypatch, report, root=tmp_path)
        assert ordinary.verdict == "block"
        assert path in ordinary.next_action

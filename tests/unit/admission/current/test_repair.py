"""Bounded repair admission follows exact official validation evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest

import ethos.adapters.admission.current.resolution as resolution_adapter
from tests.support.semantic import commitment_fixture
from tests.unit.admission.current.support import official_artifact
from tests.unit.admission.current.support import official_report
from tests.unit.admission.current.support import resolve_report

ACTIVE_SPEC = "openspec/changes/repair-change/specs/repository-governance/spec.md"


def _corrupt_report_coordinate(
    subject: object, coordinate: tuple[str | int, ...], value: object
) -> None:
    """Replace one field of an otherwise valid untrusted OpenSpec report."""
    for key in coordinate[:-1]:
        if isinstance(key, int):
            assert isinstance(subject, list)
            subject = subject[key]
        else:
            assert isinstance(subject, dict)
            subject = subject[key]
    field = coordinate[-1]
    assert isinstance(field, str)
    assert isinstance(subject, dict)
    subject[field] = value


def _active_change_validation_report(
    root: Path,
    *,
    issue_level: str = "ERROR",
    issue_path: object = "repository-governance/spec.md",
    spec_outputs: tuple[str, ...] = ("specs/repository-governance/spec.md",),
    create_outputs: bool = True,
    additional_issues: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    change = "repair-change"
    change_root = root / "openspec" / "changes" / change
    outputs = {
        "proposal": ("proposal.md",),
        "specs": spec_outputs,
        "design": ("design.md",),
        "tasks": ("tasks.md",),
    }
    if create_outputs:
        for relative in (".openspec.yaml", *(path for paths in outputs.values() for path in paths)):
            output = change_root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("official artifact\n", encoding="utf-8")
    return official_report(
        change=change,
        gaps=(
            f"openspec_validation_failed:change:{change}",
            f"commitment_invalid:{change}",
        ),
        artifacts=tuple(
            official_artifact(identifier, paths[0]) for identifier, paths in outputs.items()
        ),
        commitment={},
        change_path=change_root.as_posix(),
        status_payload={
            "changeName": change,
            "changeRoot": change_root.as_posix(),
            "artifactPaths": {
                identifier: {
                    "existingOutputPaths": [(change_root / output).as_posix() for output in paths]
                }
                for identifier, paths in outputs.items()
            },
        },
        validate_payload={
            "items": [
                {
                    "id": change,
                    "type": "change",
                    "valid": False,
                    "issues": [
                        {
                            "level": issue_level,
                            "path": issue_path,
                            "message": "structured validator detail",
                        },
                        *additional_issues,
                    ],
                }
            ]
        },
    )


def _canonical_repair_report(
    *, gaps: tuple[str, ...] = ("openspec_validation_failed:spec:distribution",)
) -> dict[str, object]:
    change = "repair-spec"
    return official_report(
        change=change,
        gaps=gaps,
        artifacts=(official_artifact("tasks", "tasks.md"),),
        commitment=commitment_fixture(id=f"change:{change}").model_dump(mode="json"),
    )


@pytest.mark.parametrize(
    ("paths", "verdict", "uncovered"),
    [
        (("openspec/specs/distribution/spec.md",), "pass", []),
        (
            ("openspec/specs/product-status-contract/spec.md",),
            "block",
            ["openspec/specs/product-status-contract/spec.md"],
        ),
        (
            ("openspec/specs/distribution/spec.md", "src/ethos/product.py"),
            "block",
            ["src/ethos/product.py"],
        ),
    ],
)
def test_current_resolution_admits_only_validator_named_canonical_spec_repairs(
    monkeypatch,
    paths: tuple[str, ...],
    verdict: str,
    uncovered: list[str],
) -> None:
    resolution = resolve_report(monkeypatch, _canonical_repair_report(), paths=paths)
    assert resolution.verdict == verdict
    assert resolution.commitment is None
    assert resolution.scope.material_scope["state"] == "canonical_spec_repair"
    assert resolution.scope.material_scope["uncovered_paths"] == uncovered
    assert resolution.next_action == "openspec validate --all --strict --json"


@pytest.mark.parametrize(
    ("issue_level", "issue_path", "requested_path"),
    [
        ("ERROR", "repository-governance/spec.md", ACTIVE_SPEC),
        ("WARNING", "specs/repository-governance/spec.md", ACTIVE_SPEC),
        ("ERROR", ".openspec.yaml", "openspec/changes/repair-change/.openspec.yaml"),
    ],
)
def test_current_resolution_admits_selected_change_strict_validation_repair_without_commitment(
    tmp_path: Path,
    monkeypatch,
    issue_level: str,
    issue_path: str,
    requested_path: str,
) -> None:
    report = _active_change_validation_report(
        tmp_path, issue_level=issue_level, issue_path=issue_path
    )
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(requested_path,))
    assert resolution.verdict == "pass"
    assert resolution.commitment is None
    assert resolution.required_gaps == ()
    assert resolution.scope.material_scope["state"] == "official_change_validation_repair"
    assert resolution.scope.material_scope["authorized_paths"] == [requested_path]
    assert resolution.next_action == "openspec validate --all --strict --json"


@pytest.mark.parametrize(
    ("coordinate", "value"),
    [
        (("official_cli", "available"), False),
        (("commands",), None),
        (("commands", "list", "parse_error"), "invalid JSON"),
        (("commands", "validate", "json", "items"), None),
        (("commands", "validate", "json", "items", 0, "type"), "spec"),
        (("commands", "validate", "json", "items", 0, "id"), "other-change"),
        (("commands", "validate", "json", "items", 0, "valid"), True),
        (("commands", "validate", "json", "items", 0, "issues"), [None]),
        (("commands", "validate", "json", "items", 0, "issues", 0, "level"), "INFO"),
        (("commands", "validate", "json", "items", 0, "issues", 0, "level"), "UNKNOWN"),
        (("commands", "status", "parse_error"), "invalid JSON"),
        (("commands", "validate", "exit_code"), 0),
        (("lifecycle", "changes"), []),
        (("lifecycle", "changes", 0, "required_gaps"), ["artifact_unavailable"]),
        (("lifecycle", "changes", 0, "artifacts", 0, "status"), "blocked"),
        (("change",), "Invalid"),
        (
            ("required_gaps",),
            ["openspec_validation_failed:change:repair-change", "openspec_doctor_unhealthy"],
        ),
    ],
)
def test_current_resolution_rejects_untrusted_active_change_validation_items(
    tmp_path, monkeypatch, coordinate, value
):
    report = _active_change_validation_report(tmp_path)
    valid = resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert valid.verdict == "pass"
    assert valid.scope.material_scope["authorized_paths"] == [ACTIVE_SPEC]
    _corrupt_report_coordinate(report, coordinate, value)
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")
    assert list(resolution.required_gaps) == report["required_gaps"]


def test_current_resolution_ignores_info_beside_strict_blocking_change_issue(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report = _active_change_validation_report(
        tmp_path,
        additional_issues=({"level": "INFO", "path": "requirements[0]", "message": "guidance"},),
    )
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert resolution.verdict == "pass"
    assert resolution.scope.material_scope["authorized_paths"] == [ACTIVE_SPEC]


@pytest.mark.parametrize(
    "issue_path",
    ["", "/absolute/spec.md", "../tasks.md", "specs/../tasks.md", "missing/spec.md", None],
)
def test_current_resolution_rejects_invalid_active_change_validation_issue_paths(
    tmp_path: Path,
    monkeypatch,
    issue_path: object,
) -> None:
    report = _active_change_validation_report(tmp_path, issue_path=issue_path)
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "official_change_validation_repair"


@pytest.mark.parametrize("fault", ["missing", "metadata_link", "output_link", "ambiguous"])
def test_current_resolution_requires_unique_existing_unlinked_official_repair(
    tmp_path, monkeypatch, fault
):
    requested = {
        "metadata_link": "openspec/changes/repair-change/.openspec.yaml",
        "output_link": "openspec/changes/repair-change/shadow.md",
        "ambiguous": "openspec/changes/repair-change/tasks.md",
    }.get(fault, ACTIVE_SPEC)
    issue = {
        "metadata_link": ".openspec.yaml",
        "output_link": "shadow.md",
        "ambiguous": "tasks.md",
    }.get(fault, "repository-governance/spec.md")
    report = _active_change_validation_report(
        tmp_path,
        issue_path=issue,
        create_outputs=fault != "missing",
        spec_outputs=("specs/repository-governance/spec.md", "specs/tasks.md")
        if fault == "ambiguous"
        else ("specs/repository-governance/spec.md",),
    )
    target = None
    if fault in {"metadata_link", "output_link"}:
        declared = tmp_path / (requested if fault == "metadata_link" else ACTIVE_SPEC)
        target = tmp_path / ("outside-metadata.yaml" if fault == "metadata_link" else requested)
        target.write_text("unofficial target\n", encoding="utf-8")
        declared.unlink()
        declared.symlink_to(target)
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(requested,))
    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")
    if target is not None:
        assert target.read_text() == "unofficial target\n"


@pytest.mark.parametrize(
    "requested_paths",
    [
        ("openspec/changes/repair-change/design.md",),
        (ACTIVE_SPEC, "openspec/changes/repair-change/design.md"),
        ("openspec/changes/repair-change/specs",),
    ],
)
def test_current_resolution_blocks_unrelated_or_mixed_validation_repair_paths(
    tmp_path: Path,
    monkeypatch,
    requested_paths: tuple[str, ...],
) -> None:
    report = _active_change_validation_report(tmp_path)
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=requested_paths)
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope["state"] == "official_change_validation_repair"
    assert resolution.scope.material_scope["uncovered_paths"]


@pytest.mark.parametrize(
    "gap",
    [
        "openspec_validation_failed:spec:",
        "openspec_validation_failed:spec:Invalid",
        "openspec_validation_failed:spec:../distribution",
        "openspec_validation_failed:change:distribution",
    ],
)
def test_current_resolution_does_not_derive_canonical_repair_from_invalid_gap(
    monkeypatch,
    gap: str,
) -> None:
    resolution = resolve_report(
        monkeypatch,
        _canonical_repair_report(gaps=(gap,)),
        paths=("openspec/specs/distribution/spec.md",),
    )
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "canonical_spec_repair"
    assert resolution.required_gaps == (gap,)


@pytest.mark.parametrize(
    ("coordinate", "value"),
    [
        (("commitment",), {}),
        (("commitment",), None),
        (("commitment", "id"), "change:other"),
        (("lifecycle", "changes"), []),
        (("lifecycle", "changes", 0, "artifacts"), []),
        (
            ("required_gaps",),
            ["openspec_validation_failed:spec:distribution", "commitment_invalid:repair-spec"],
        ),
    ],
)
def test_current_resolution_requires_valid_change_contract_for_canonical_repair(
    monkeypatch, coordinate, value
):
    report = _canonical_repair_report()
    paths = ("openspec/specs/distribution/spec.md",)
    assert resolve_report(monkeypatch, report, paths=paths).verdict == "pass"
    _corrupt_report_coordinate(report, coordinate, value)
    resolution = resolve_report(monkeypatch, report, paths=paths)
    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")


@pytest.mark.parametrize(
    "mode",
    ["valid", "missing", "unrelated", "mixed", "other-gap", "info", "wrong-change", "missing-file"],
)
def test_archived_canonical_repair_uses_verified_source_without_masking_proof(
    monkeypatch, tmp_path, mode
):
    path = "openspec/specs/distribution/spec.md"
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_text("## Purpose\n\nTBD\n", encoding="utf-8")
    if mode == "missing-file":
        target.unlink()
    report = official_report(
        change="repair-spec",
        commitment={},
        gaps=("openspec_validation_failed:spec:distribution",),
        validate_payload={
            "items": [
                {
                    "id": "distribution",
                    "type": "spec",
                    "valid": False,
                    "issues": [
                        {"level": "INFO" if mode == "info" else "ERROR", "path": "overview"}
                    ],
                }
            ]
        },
    )
    _corrupt_report_coordinate(report, ("lifecycle", "changes"), [])
    if mode == "other-gap":
        report["required_gaps"] = [
            "openspec_validation_failed:spec:distribution",
            "openspec_doctor_unhealthy",
        ]
    source = (
        None
        if mode == "missing"
        else (
            commitment_fixture(
                id="change:other" if mode == "wrong-change" else "change:repair-spec"
            ),
            {"authorized_paths": [] if mode == "unrelated" else [path]},
        )
    )
    calls = []

    def recover(*_args, **kwargs):
        calls.append(kwargs)
        return source

    monkeypatch.setattr(resolution_adapter, "attested_archive_transition", recover)
    paths = (path, "src/unrelated.py") if mode == "mixed" else (path,)
    result = resolve_report(monkeypatch, report, root=tmp_path, paths=paths)
    assert result.verdict == ("pass" if mode == "valid" else "block")
    if mode == "valid":
        assert len(calls) == 1
        assert result.scope_report(paths)["authorized_paths"] == [path]
        assert result.next_action == "openspec validate --all --strict --json"
    ordinary = resolve_report(monkeypatch, report, root=tmp_path)
    assert ordinary.verdict == "block"
    assert "openspec_validation_failed:spec:distribution" in ordinary.required_gaps

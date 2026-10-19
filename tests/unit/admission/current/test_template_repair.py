"""Template-conformance repair admission is bounded to the drifted official artifact."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from tests.unit.admission.current.support import official_artifact
from tests.unit.admission.current.support import official_report
from tests.unit.admission.current.support import resolve_report

DRIFTED_DESIGN = "openspec/changes/repair-change/design.md"


def _template_drift_report(root: Path, *gaps: str) -> dict[str, object]:
    """Report a selected Change whose design lacks a template heading yet passes validation."""
    change = "repair-change"
    change_root = root / "openspec" / "changes" / change
    outputs = {"proposal": "proposal.md", "design": "design.md", "tasks": "tasks.md"}
    for relative in outputs.values():
        (change_root / relative).parent.mkdir(parents=True, exist_ok=True)
        (change_root / relative).write_text("official artifact\n", encoding="utf-8")
    return official_report(
        change=change,
        gaps=(f"openspec_template_heading_missing:{change}:design:Risks / Trade-offs", *gaps),
        artifacts=tuple(official_artifact(name, path) for name, path in outputs.items()),
        commitment={},
        change_path=change_root.as_posix(),
        status_payload={
            "changeName": change,
            "changeRoot": change_root.as_posix(),
            "artifactPaths": {
                name: {"existingOutputPaths": [(change_root / path).as_posix()]}
                for name, path in outputs.items()
            },
        },
    )


@pytest.mark.parametrize(
    ("requested_path", "admitted"),
    [
        (DRIFTED_DESIGN, True),
        ("openspec/changes/repair-change/proposal.md", False),
        ("README.md", False),
    ],
)
def test_current_resolution_admits_only_the_template_drifted_artifact_as_a_repair(
    tmp_path: Path, monkeypatch, requested_path: str, *, admitted: bool
) -> None:
    report = _template_drift_report(tmp_path)
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(requested_path,))
    assert resolution.scope.material_scope["state"] == "official_template_conformance_repair"
    assert resolution.scope.material_scope["authorized_paths"] == [DRIFTED_DESIGN]
    if admitted:
        assert (resolution.verdict, resolution.required_gaps) == ("pass", ())
    else:
        assert resolution.verdict == "block"
        assert resolution.required_gaps == (f"openspec_material_path_uncovered:{requested_path}",)


def test_another_drifted_change_does_not_hold_the_selected_template_repair(
    tmp_path: Path, monkeypatch
) -> None:
    report = _template_drift_report(
        tmp_path, "openspec_template_heading_missing:other-change:proposal:Why"
    )
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(DRIFTED_DESIGN,))
    assert (resolution.verdict, resolution.required_gaps) == ("pass", ())
    assert resolution.scope.material_scope["authorized_paths"] == [DRIFTED_DESIGN]


def test_a_non_template_gap_keeps_the_template_repair_closed(tmp_path: Path, monkeypatch) -> None:
    report = _template_drift_report(tmp_path, "openspec_official_cli_missing")
    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(DRIFTED_DESIGN,))
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "official_template_conformance_repair"
    assert "openspec_official_cli_missing" in resolution.required_gaps

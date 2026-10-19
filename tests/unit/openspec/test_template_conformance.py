"""Active proposals and designs follow the templates the official CLI resolves."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import ethos.adapters.openspec.governance as governance
import tests.support.governed_repository as fixture
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.openspec.template_conformance import template_conformance_gaps
from ethos.repository.openspec.template_outline import markdown_outline
from ethos.repository.openspec.template_outline import outline_gaps
from ethos.repository.openspec.template_outline import template_outline

_DESIGN_TEMPLATE = (
    "# Design\n\n## Context\n\n<!-- Current state -->\n\n## Goals / Non-Goals\n\n"
    "**Goals:**\n<!-- Aims -->\n\n## Decisions\n\n<!-- Decisions -->\n\n"
    "## Risks / Trade-offs\n\n<!-- Risks -->\n"
)
_PROPOSAL_TEMPLATE = (
    "# Proposal\n\n## Why\n\n<!-- Why -->\n\n## What Changes\n\n<!-- What -->\n\n"
    "## Capabilities\n\n### New Capabilities\n<!-- New -->\n\n"
    "### Modified Capabilities\n<!-- Modified -->\n\n## Impact\n\n<!-- Impact -->\n"
)
_DESIGN = (
    "# Design\n\n## Context\n\nNow.\n\n## Goals / Non-Goals\n\nAims.\n\n"
    "## Decisions\n\nOne.\n\n## Risks / Trade-offs\n\nSome.\n"
)


def _gaps(template: str, artifact: str) -> list[tuple[str, str]]:
    return list(outline_gaps(template_outline(template), markdown_outline(artifact)))


def test_official_sections_followed_by_optional_and_own_sections_have_no_gap() -> None:
    design = _DESIGN + "\n## Migration Plan\n\nSteps.\n\n## Own Topic\n\nMore.\n"

    assert _gaps(_DESIGN_TEMPLATE, design) == []


def test_a_missing_misplaced_or_misordered_heading_is_named_by_its_template_path() -> None:
    proposal = (
        "## Why\n\nBecause.\n\n## Impact\n\n### New Capabilities\n\n- None.\n\n"
        "## Capabilities\n\n### Modified Capabilities\n\n- None.\n\n## What Changes\n\n- One.\n"
    )

    assert _gaps(_PROPOSAL_TEMPLATE, proposal) == [
        ("misordered", "What Changes"),
        ("misplaced", "Capabilities > New Capabilities"),
        ("misordered", "Impact"),
    ]
    assert _gaps(_DESIGN_TEMPLATE, _DESIGN.replace("## Risks / Trade-offs", "## Risks")) == [
        ("missing", "Risks / Trade-offs")
    ]


def test_fenced_or_differently_nested_headings_do_not_satisfy_the_template() -> None:
    fenced = _DESIGN.replace("## Risks / Trade-offs\n", "```markdown\n## Risks / Trade-offs\n```\n")
    nested = _DESIGN.replace("## Risks / Trade-offs", "### Risks / Trade-offs")

    assert _gaps(_DESIGN_TEMPLATE, fenced) == [("missing", "Risks / Trade-offs")]
    assert _gaps(_DESIGN_TEMPLATE, nested) == [("misplaced", "Risks / Trade-offs")]


def test_template_headings_are_literal_and_placeholders_are_not_required() -> None:
    tasks = "# Tasks\n\n## 1. <!-- Task Group Name -->\n\n- [ ] 1.1 <!-- Task -->\n"
    extended = _DESIGN_TEMPLATE + "\n## Rollout\n\n<!-- Rollout -->\n"

    assert template_outline(tasks) == ()
    assert _gaps(extended, _DESIGN) == [("missing", "Rollout")]


def _governed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *changes: str) -> Path:
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    root = fixture.init_git_repo(tmp_path / "repo")
    for change in changes:
        fixture.write_active_commitment(root, change_id=change)
    return root


def _template_gaps(report: dict[str, object]) -> list[str]:
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    return [gap for gap in gaps if gap.startswith("openspec_template_heading_")]


def test_governance_reads_every_artifact_graph_and_each_schema_template_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _governed(tmp_path, monkeypatch, "first", "second")

    report = governance.openspec_governance_report(root, change="first")

    commands = report["commands"]
    changes = commands["status_all"]["json"]["changes"]
    assert sorted(change["changeName"] for change in changes) == ["first", "second"]
    assert list(commands["templates"]) == ["spec-driven"]
    assert _template_gaps(report) == []


def test_every_active_change_reports_its_missing_and_misplaced_headings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _governed(tmp_path, monkeypatch, "first", "second")
    design = root / "openspec/changes/second/design.md"
    design.write_text(design.read_text().replace("## Risks / Trade-offs", "## Hazards"))
    proposal = root / "openspec/changes/first/proposal.md"
    text = proposal.read_text()
    new = text[text.index("### New Capabilities") : text.index("### Modified Capabilities")]
    proposal.write_text(text.replace(new, "") + "\n" + new)

    report = governance.openspec_governance_report(root, change="first")

    assert report["verdict"] == "block"
    assert _template_gaps(report) == [
        "openspec_template_heading_misplaced:first:proposal:Capabilities > New Capabilities",
        "openspec_template_heading_missing:second:design:Risks / Trade-offs",
    ]


def test_a_heading_the_resolved_template_gains_is_required_without_an_ethos_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _governed(tmp_path, monkeypatch, "first")
    official = governance.openspec_governance_report(root, change="first")
    package = Path(official["commands"]["templates"]["spec-driven"]["json"]["design"]["path"])
    project = root / "openspec/schemas/spec-driven"
    shutil.copytree(package.parents[1], project)
    template = project / "templates/design.md"
    template.write_text(template.read_text() + "\n## Rollout\n\n<!-- Rollout -->\n")

    report = governance.openspec_governance_report(root, change="first")

    assert report["commands"]["templates"]["spec-driven"]["json"]["design"]["source"] == "project"
    assert _template_gaps(report) == ["openspec_template_heading_missing:first:design:Rollout"]


def _template_read(**paths: Path) -> dict[str, object]:
    return {
        "exit_code": 0,
        "parse_error": "",
        "json": {artifact: {"path": path.as_posix()} for artifact, path in paths.items()},
    }


def test_an_unreadable_template_is_a_gap_and_an_absent_template_is_not_required(
    tmp_path: Path,
) -> None:
    changes = [{"changeName": "first", "schemaName": "custom", "artifactPaths": {}}]
    templates = {"custom": _template_read(proposal=tmp_path / "missing.md")}

    assert template_conformance_gaps(tmp_path, changes, templates) == [
        "openspec_template_unreadable:custom:proposal"
    ]


@pytest.mark.parametrize("artifact", ["relative", "outside", "directory", "oversized", "binary"])
def test_an_artifact_the_repository_cannot_supply_is_a_gap(tmp_path: Path, artifact: str) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    template = tmp_path / "proposal.md"
    template.write_text("## Why\n", encoding="utf-8")
    (root / "oversized.md").write_text("x" * ((1 << 20) + 1), encoding="utf-8")
    (root / "binary.md").write_bytes(b"\xff")
    output = {
        "relative": Path("proposal.md"),
        "outside": template,
        "directory": root,
        "oversized": root / "oversized.md",
        "binary": root / "binary.md",
    }[artifact]
    changes = [
        {
            "changeName": "first",
            "schemaName": "custom",
            "artifactPaths": {"proposal": {"existingOutputPaths": [output.as_posix()]}},
        }
    ]

    gaps = template_conformance_gaps(root, changes, {"custom": _template_read(proposal=template)})

    assert gaps == ["openspec_artifact_unreadable:first:proposal"]


def test_a_work_lane_repairs_only_its_drifted_design(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drift that strict validation accepts is repairable, and nothing else becomes writable."""
    work = fixture.prepared_work_lane(tmp_path).worktree
    fixture.write_active_commitment(work, change_id="drifted")
    design = work / "openspec/changes/drifted/design.md"
    design.write_text(design.read_text().replace("## Risks / Trade-offs", "## Hazards"))
    monkeypatch.setenv("ETHOS_CHANGE", "drifted")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    repaired = prewrite_guard(root=work, paths=[design], editor_root=work)
    unrelated = prewrite_guard(root=work, paths=[work / "README.md"], editor_root=work)

    assert repaired["verdict"] == "pass", repaired["required_gaps"]
    assert unrelated["required_gaps"] == ["openspec_material_path_uncovered:README.md"]

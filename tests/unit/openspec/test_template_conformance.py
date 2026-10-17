"""Active proposals and designs follow the templates the official CLI resolves."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.openspec.governance as governance
import tests.support.governed_repository as fixture
from ethos.repository.openspec.template_outline import markdown_outline
from ethos.repository.openspec.template_outline import outline_gaps
from ethos.repository.openspec.template_outline import template_outline

if TYPE_CHECKING:
    import pytest

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

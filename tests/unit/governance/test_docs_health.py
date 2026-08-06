"""Regression coverage for documentation command validation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from ethos.surface.cli.root.reference import docs_registry_report


def write_active_doc(root: Path, command: str) -> None:
    """Write one minimal canonical document containing a shell command example."""
    path = root / "docs" / "reference" / "example.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""\
---
subject: ethos:example
role: reference
state: canonical
relations: none
---

# Example

Status: canonical.

Purpose: exercise the command validator.

See also: none.

```bash
{command}
```
""",
        encoding="utf-8",
    )


def test_docs_health_rejects_deleted_quality_provenance_command(tmp_path: Path) -> None:
    """Deleted quality commands cannot persist in canonical examples."""
    write_active_doc(tmp_path, "ethos quality provenance --json")

    report = docs_registry_report(tmp_path)

    assert report["invalid_command_examples"] == [
        "unknown_ethos_command_example:docs/reference/example.md:17:ethos quality provenance"
    ]


def test_docs_health_rejects_unregistered_nested_command(tmp_path: Path) -> None:
    """A nested example must resolve through the live Cyclopts command tree."""
    write_active_doc(tmp_path, "ethos lane lease migrate --json")

    report = docs_registry_report(tmp_path)

    assert report["invalid_command_examples"] == [
        "unknown_ethos_command_example:docs/reference/example.md:17:ethos lane lease migrate"
    ]


def test_docs_health_accepts_registered_nested_command(tmp_path: Path) -> None:
    """A live nested Cyclopts operation remains an admitted documentation example."""
    write_active_doc(tmp_path, "uv run --no-sync ethos lane lease renew --json")

    report = docs_registry_report(tmp_path)

    assert report["invalid_command_examples"] == []


def test_docs_health_rejects_unindexed_plan(tmp_path: Path) -> None:
    """Every active or planned plan must be reachable from the plan index."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "README.md").write_text(
        """\
---
subject: docs:plans
role: index
state: planned
relations: none
---

# Plans
""",
        encoding="utf-8",
    )
    (plans / "orphan.md").write_text(
        """\
---
subject: ethos:orphan-plan
role: plan
state: active
relations: none
---

# Orphan Plan
""",
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["unindexed_plans"] == ["unindexed_plan:docs/plans/orphan.md"]


def test_docs_health_is_portable_without_ethos_physical_layout(tmp_path: Path) -> None:
    """Adopter docs health validates semantics without imposing ETHOS paths."""
    path = tmp_path / "docs" / "native" / "guide.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        """---
subject: adopter:guide
role: how-to
state: active
relations: none
---

# Guide

Status: active.

Purpose: exercise portable documentation health.

See also: none.
""",
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_docs_health_uses_the_profile_declared_docs_root(tmp_path: Path) -> None:
    """One profile-relative root drives every portable docs check."""
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        "profile_id = 'sample'\n"
        "[roots]\n"
        "docs = 'handbook'\n"
        "[openspec]\n"
        "material_paths = ['openspec/**']\n",
        encoding="utf-8",
    )
    path = tmp_path / "handbook" / "guide.md"
    path.parent.mkdir()
    path.write_text(
        """---
subject: adopter:guide
role: how-to
state: active
relations: none
---

# Guide

Status: active.

Purpose: prove profile-relative discovery.

See also: none.
""",
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    registry = cast("list[dict[str, str]]", report["registry"])
    assert [entry["path"] for entry in registry] == ["handbook/guide.md"]


def test_docs_health_fails_closed_for_an_invalid_profile(tmp_path: Path) -> None:
    """An invalid declaration never falls back to the default docs root."""
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'sample'\n[roots]\ndocs = '../outside'\n", encoding="utf-8")
    write_active_doc(tmp_path, "ethos status --json")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["document_count"] == 0
    assert report["required_gaps"] == ["repository_profile_invalid:.ethos/profile.toml"]


def test_docs_health_fails_closed_for_invalid_taxonomy(tmp_path: Path) -> None:
    """A present but malformed taxonomy cannot silently select defaults."""
    write_active_doc(tmp_path, "ethos status --json")
    taxonomy = tmp_path / "docs" / "_meta" / "taxonomy.toml"
    taxonomy.parent.mkdir()
    taxonomy.write_text("[states\n", encoding="utf-8")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["docs_taxonomy_invalid:docs/_meta/taxonomy.toml"]


def test_docs_health_does_not_scan_product_distribution_layout(tmp_path: Path) -> None:
    """Portable docs semantics do not absorb ETHOS product carriers."""
    write_active_doc(tmp_path, "ethos status --json")
    distribution = tmp_path / "distributions" / "python" / "README.md"
    distribution.parent.mkdir(parents=True)
    distribution.write_text("# Product-only carrier\n", encoding="utf-8")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    registry = cast("list[dict[str, str]]", report["registry"])
    assert [entry["path"] for entry in registry] == ["docs/reference/example.md"]


def test_observational_roles_do_not_require_reader_sections(tmp_path: Path) -> None:
    """Evidence and history are classified by role, not by hard-coded paths."""
    path = tmp_path / "docs" / "native" / "observation.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        """---
subject: adopter:observation
role: evidence
state: active
relations: none
---

# Observation
""",
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["missing_visible_sections"] == []


def test_docs_registry_gate_declares_only_its_owned_dimensions() -> None:
    """Links and durable evidence remain owned by their dedicated gates."""
    registry = tomllib.loads(
        (Path(__file__).resolve().parents[3] / "system" / "gates.toml").read_text(encoding="utf-8")
    )
    docs = next(gate for gate in registry["gates"] if gate["id"] == "docs-registry")

    assert docs["dimensions"] == [
        "front-matter",
        "taxonomy",
        "visible-sections",
        "command-examples",
        "plan-discoverability",
        "decision-records",
    ]


def test_decision_records_use_one_comparison_table_shape() -> None:
    """Every durable ruling compares options through the canonical table grammar."""
    root = Path(__file__).resolve().parents[3] / "docs" / "decisions"
    for path in [root / "decision-record-template.md", *sorted(root.glob("DR-*.md"))]:
        alternatives = (
            path.read_text(encoding="utf-8")
            .split("## Alternatives Considered", 1)[1]
            .split("## Selected Approach And Rationale", 1)[0]
        )
        assert "| Option | Verdict | Pros | Cons | Decision basis |" in alternatives
        assert not {"**Pros**", "**Cons**", "**Why Rejected**"} & set(alternatives.splitlines())


def test_decision_records_require_the_single_concise_grammar(tmp_path: Path) -> None:
    """A durable ruling is incomplete when its comparable decision grammar is partial."""
    path = tmp_path / "docs" / "decisions" / "DR-0001-example.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        """---
subject: example:decision
role: decision
state: canonical
relations: none
---

# DR-0001: Example

Status: accepted.

Purpose: expose an incomplete durable ruling.

See also: none.

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0001 |
| Status | accepted |
| Decision Date | 2026-08-06 |
| Decision Change Date | 2026-08-06 |
""",
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["decision_record_gaps"] == [
        (
            "decision_record_sections_missing:docs/decisions/DR-0001-example.md:"
            "Context,Invariants,Alternatives Considered,Decision,Consequences,Proof Or Evidence,"
            "Revisit Trigger,Decision Change Ledger"
        ),
        "decision_index_missing:docs/decisions/decision-index.md",
    ]
    assert report["verdict"] == "block"


def test_decision_index_requires_current_records_newest_first(tmp_path: Path) -> None:
    """The decision index leads with accepted rulings ordered by latest change date."""
    decisions = tmp_path / "docs" / "decisions"
    decisions.mkdir(parents=True)
    for decision_id, changed in (("DR-0001", "2026-08-01"), ("DR-0002", "2026-08-06")):
        (decisions / f"{decision_id}-example.md").write_text(
            _decision_record(decision_id, changed),
            encoding="utf-8",
        )
    (decisions / "decision-index.md").write_text(
        _decision_index(("DR-0001", "DR-0002")),
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["decision_record_gaps"] == [
        "decision_index_order_invalid:docs/decisions/decision-index.md:DR-0002,DR-0001"
    ]


def _decision_record(decision_id: str, changed: str) -> str:
    return f"""---
subject: example:decision:{decision_id.lower()}
role: decision
state: canonical
relations: none
---

# {decision_id}: Example

Status: accepted.

Purpose: exercise decision ordering.

See also: none.

## Record

| Field | Value |
| --- | --- |
| Decision ID | {decision_id} |
| Status | accepted |
| Decision Date | {changed} |
| Decision Change Date | {changed} |

## Context

Context.

## Invariants

- One invariant.

## Alternatives Considered

| Option | Verdict | Pros | Cons | Decision basis |
| --- | --- | --- | --- | --- |
| One | selected | Clear. | Cost. | Best fit. |
| Two | rejected | Familiar. | Breaks invariant. | Inferior. |

## Decision

Select one.

## Consequences

One consequence.

## Proof Or Evidence

- One check.

## Revisit Trigger

One falsifiable trigger.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 1 | {changed} | Initial ruling | Select | Check |
"""


def _decision_index(decision_ids: tuple[str, ...]) -> str:
    rows = "\n".join(
        f"| [{decision_id}]({decision_id}-example.md) | Example | accepted | 2026-08-06 |"
        for decision_id in decision_ids
    )
    return f"""---
subject: example:decision:index
role: index
state: canonical
relations: none
---

# Decision Index

Status: canonical.

Purpose: route decisions.

See also: none.

| ID | Title | Status | Changed |
| --- | --- | --- | --- |
{rows}
"""

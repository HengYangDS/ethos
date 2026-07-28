"""Regression coverage for documentation command validation."""

from __future__ import annotations

import tomllib
from pathlib import Path

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
    write_active_doc(tmp_path, "ethos lane lease takeover --json")

    report = docs_registry_report(tmp_path)

    assert report["invalid_command_examples"] == [
        "unknown_ethos_command_example:docs/reference/example.md:17:ethos lane lease takeover"
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

    assert report["ok"] is True
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

    assert report["ok"] is True
    assert [entry["path"] for entry in report["registry"]] == ["handbook/guide.md"]


def test_docs_health_fails_closed_for_an_invalid_profile(tmp_path: Path) -> None:
    """An invalid declaration never falls back to the default docs root."""
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'sample'\n", encoding="utf-8")
    write_active_doc(tmp_path, "ethos status --json")

    report = docs_registry_report(tmp_path)

    assert report["ok"] is False
    assert report["document_count"] == 0
    assert report["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]


def test_docs_health_fails_closed_for_invalid_taxonomy(tmp_path: Path) -> None:
    """A present but malformed taxonomy cannot silently select defaults."""
    write_active_doc(tmp_path, "ethos status --json")
    taxonomy = tmp_path / "docs" / "_meta" / "taxonomy.toml"
    taxonomy.parent.mkdir()
    taxonomy.write_text("[states\n", encoding="utf-8")

    report = docs_registry_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["docs_taxonomy_invalid:docs/_meta/taxonomy.toml"]


def test_docs_health_does_not_scan_product_distribution_layout(tmp_path: Path) -> None:
    """Portable docs semantics do not absorb ETHOS product carriers."""
    write_active_doc(tmp_path, "ethos status --json")
    distribution = tmp_path / "distributions" / "python" / "README.md"
    distribution.parent.mkdir(parents=True)
    distribution.write_text("# Product-only carrier\n", encoding="utf-8")

    report = docs_registry_report(tmp_path)

    assert report["ok"] is True
    assert [entry["path"] for entry in report["registry"]] == ["docs/reference/example.md"]


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

    assert report["ok"] is True
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
    ]

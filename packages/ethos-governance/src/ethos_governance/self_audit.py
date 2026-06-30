from __future__ import annotations

from pathlib import Path

from ethos_governance.command_registry import command_registry_report

CANONICAL_PACKAGES = (
    "ethos",
    "ethos-kernel",
    "ethos-governance",
    "ethos-workspace",
    "ethos-agent",
    "ethos-adopt",
)

REQUIRED_DOCS = (
    "docs/architecture/product-ontology.md",
    "docs/concepts/kernel-model.md",
    "docs/architecture/action-graph.md",
    "docs/governance/provenance-and-attestation.md",
    "docs/governance/self-evolution-campaign.md",
)

REQUIRED_SCHEMAS = (
    "result.schema.json",
    "subject.schema.json",
    "commitment.schema.json",
    "change.schema.json",
    "action.schema.json",
    "evidence.schema.json",
    "chronicle.schema.json",
    "evolution.schema.json",
)


def _front_matter_ok(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    header = text.split("---", 2)[1]
    return all(f"{key}:" in header for key in ("subject", "role", "state", "relations"))


def self_audit(root: Path) -> dict[str, object]:
    package_missing = [
        package
        for package in CANONICAL_PACKAGES
        if not (root / "packages" / package / "README.md").exists()
    ]
    docs_missing = [doc for doc in REQUIRED_DOCS if not (root / doc).exists()]
    docs_without_front_matter = [
        doc for doc in REQUIRED_DOCS if (root / doc).exists() and not _front_matter_ok(root / doc)
    ]
    schemas_missing = [
        schema for schema in REQUIRED_SCHEMAS if not (root / "schemas" / "ethos" / schema).exists()
    ]
    command_report = command_registry_report()
    gaps = package_missing + docs_missing + docs_without_front_matter + schemas_missing
    return {
        "ok": not gaps and bool(command_report["ok"]),
        "package_ontology": {
            "ok": not package_missing,
            "canonical_packages": list(CANONICAL_PACKAGES),
            "missing": package_missing,
        },
        "docs": {
            "ok": not docs_missing and not docs_without_front_matter,
            "missing": docs_missing,
            "without_front_matter": docs_without_front_matter,
        },
        "schemas": {
            "ok": not schemas_missing,
            "missing": schemas_missing,
        },
        "command_registry": command_report,
        "required_gaps": gaps,
    }

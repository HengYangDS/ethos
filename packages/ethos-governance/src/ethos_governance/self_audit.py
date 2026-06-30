from __future__ import annotations

from pathlib import Path

from ethos_governance.claims import claims_report
from ethos_governance.command_registry import command_registry_report
from ethos_governance.evolution import evolution_report
from ethos_governance.openspec_native import openspec_self_governance_report
from ethos_governance.schema_validation import schema_validation_report

CANONICAL_PACKAGES = (
    "ethos",
    "ethos-kernel",
    "ethos-governance",
    "ethos-workspace",
    "ethos-agent",
    "ethos-project",
)

REQUIRED_DOCS = (
    "docs/architecture/product-ontology.md",
    "docs/concepts/kernel-model.md",
    "docs/architecture/action-graph.md",
    "docs/architecture/adoption-profiles.md",
    "docs/architecture/agent-projections.md",
    "docs/architecture/gate-runner.md",
    "docs/architecture/local-state.md",
    "docs/architecture/mcp-server.md",
    "docs/architecture/fleet-and-adopters.md",
    "docs/architecture/runner-and-mutation.md",
    "docs/architecture/schema-validation.md",
    "docs/governance/commit-signature-policy.md",
    "docs/governance/provenance-and-attestation.md",
    "docs/governance/docs-registry.md",
    "docs/governance/openspec-self-governance.md",
    "docs/governance/playbooks-and-skills.md",
    "docs/governance/release-governance.md",
    "docs/governance/self-evolution-campaign.md",
)

REQUIRED_SCHEMAS = (
    "result.schema.json",
    "claim.schema.json",
    "commit-policy.schema.json",
    "subject.schema.json",
    "commitment.schema.json",
    "change.schema.json",
    "action.schema.json",
    "evidence.schema.json",
    "proof-run.schema.json",
    "evidence-set.schema.json",
    "provenance.schema.json",
    "chronicle.schema.json",
    "evolution.schema.json",
    "docs-registry.schema.json",
    "evolution-ledger.schema.json",
    "gate.schema.json",
    "assistant-projection.schema.json",
    "mutation-decision.schema.json",
)

REQUIRED_RELEASE_FILES = (
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    ".gitlab-ci.yml",
    ".gitlab/merge_request_templates/default.md",
    ".gitlab/issue_templates/task.md",
    "docs/governance/self-evolution-ledger.toml",
)

REQUIRED_PLAYBOOK_FILES = (
    ".agents/skills/README.md",
    ".agents/skills/activation.toml",
    ".agents/skills/ethos-repository-governance/SKILL.md",
)

REQUIRED_OPENSPEC_FAMILIES = (
    "ethos-agent",
    "ethos-governance",
    "ethos-kernel",
    "ethos-project",
    "ethos-workspace",
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
    release_files_missing = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    playbooks_missing = [path for path in REQUIRED_PLAYBOOK_FILES if not (root / path).exists()]
    openspec_family_missing = [
        f"openspec/specs/{family}/spec.md"
        for family in REQUIRED_OPENSPEC_FAMILIES
        if not (root / "openspec" / "specs" / family / "spec.md").exists()
    ]
    command_report = command_registry_report(root)
    claim_report = claims_report(root)
    schema_report = schema_validation_report(root)
    evolution = evolution_report(root)
    openspec = openspec_self_governance_report(root)
    claim_gaps = [str(gap) for gap in claim_report["required_gaps"]]
    schema_gaps = [str(gap) for gap in schema_report["required_gaps"]]
    evolution_gaps = [str(gap) for gap in evolution["required_gaps"]]
    openspec_gaps = [str(gap) for gap in openspec["required_gaps"]]
    command_gaps = [str(gap) for gap in command_report["required_gaps"]]
    gaps = (
        package_missing
        + docs_missing
        + docs_without_front_matter
        + schemas_missing
        + release_files_missing
        + [f"adoption_scaffold_missing:{path}" for path in playbooks_missing]
        + [f"openspec_family_missing:{path}" for path in openspec_family_missing]
        + claim_gaps
        + schema_gaps
        + evolution_gaps
        + openspec_gaps
        + command_gaps
    )
    return {
        "ok": not gaps,
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
            "ok": not schemas_missing and bool(schema_report["ok"]),
            "missing": schemas_missing,
            "validation": schema_report,
        },
        "release_files": {
            "ok": not release_files_missing,
            "missing": release_files_missing,
        },
        "playbooks": {
            "ok": not playbooks_missing,
            "missing": playbooks_missing,
        },
        "openspec_families": {
            "ok": not openspec_family_missing,
            "expected": list(REQUIRED_OPENSPEC_FAMILIES),
            "missing": openspec_family_missing,
        },
        "command_registry": command_report,
        "claims": claim_report,
        "evolution": evolution,
        "openspec": openspec,
        "required_gaps": gaps,
    }

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ethos_assistants.playbooks import playbooks_report
from ethos_contracts.package_ontology import (
    package_ontology_report,
    workspace_package_config_report,
)

from ethos_repository.claims import claims_report
from ethos_repository.command_registry import command_registry_report
from ethos_repository.coupling import coupling_audit_report
from ethos_repository.evolution import evolution_report
from ethos_repository.release import REQUIRED_RELEASE_FILES as PRODUCT_RELEASE_FILES
from ethos_repository.schema_validation import schema_validation_report

OpenSpecReporter = Callable[[Path], dict[str, object]]

_PACKAGE_ONTOLOGY = package_ontology_report()
TARGET_PRODUCT_PACKAGES = tuple(str(item) for item in _PACKAGE_ONTOLOGY["target_packages"])
MIGRATION_HOST_PACKAGES = tuple(str(item) for item in _PACKAGE_ONTOLOGY["migration_hosts"])
MIGRATION_HOST_LIFECYCLE = {
    str(key): str(value) for key, value in _PACKAGE_ONTOLOGY["migration_host_lifecycle"].items()
}
TARGET_DISTRIBUTION_ADAPTERS = tuple(
    str(item) for item in _PACKAGE_ONTOLOGY["target_distributions"]
)
DISTRIBUTION_MIGRATION_HOSTS = tuple(
    str(item["migration_host"])
    for item in _PACKAGE_ONTOLOGY["migration_distributions"].values()
    if "migration_host" in item
)

REQUIRED_DOCS = (
    "docs/architecture/product-ontology.md",
    "docs/architecture/package-ontology.md",
    "docs/architecture/distribution.md",
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
    "docs/governance/conversation-ledger.md",
    "docs/governance/product-design-contract.md",
    "docs/governance/product-boundary-convergence.md",
    "docs/governance/capability-parity-ledger.md",
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
    "skill-activation.schema.json",
    "skill-registry.schema.json",
    "skill-package-manifest.schema.json",
    "mutation-decision.schema.json",
    "workspace-status.schema.json",
)

REQUIRED_RELEASE_FILES = (
    *PRODUCT_RELEASE_FILES,
    "docs/governance/self-evolution-ledger.toml",
)

REQUIRED_PLAYBOOK_FILES = (
    ".agents/skills/README.md",
    ".agents/skills/activation.toml",
    ".agents/skills/ethos-repository-governance/SKILL.md",
)

REQUIRED_OPENSPEC_FAMILIES = (
    "ethos-assistants",
    "ethos-cli",
    "ethos-contracts",
    "ethos-core",
    "ethos-distribution",
    "ethos-repository",
    "ethos-adapters",
    "ethos-test",
)


def _front_matter_ok(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    header = text.split("---", 2)[1]
    return all(f"{key}:" in header for key in ("subject", "role", "state", "relations"))


def release_files_report(root: Path) -> dict[str, object]:
    release_files_missing = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    return {
        "ok": not release_files_missing,
        "missing": release_files_missing,
    }


def _openspec_shape_report(root: Path) -> dict[str, object]:
    openspec_root = root / "openspec"
    required_gaps = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    if not (openspec_root / "config.yaml").exists():
        required_gaps.append("openspec_config_missing")
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")
    return {
        "ok": not required_gaps,
        "mode": "shape",
        "required_gaps": required_gaps,
    }


def _openspec_provider_missing_report(root: Path) -> dict[str, object]:
    shape = _openspec_shape_report(root)
    return {
        "ok": False,
        "mode": "deep",
        "shape": shape,
        "required_gaps": ["openspec_reporter_not_configured"],
    }


def self_audit(
    root: Path,
    *,
    openspec_mode: str = "deep",
    openspec_reporter: OpenSpecReporter | None = None,
) -> dict[str, object]:
    package_missing = [
        f"packages/{package}"
        for package in MIGRATION_HOST_PACKAGES
        if (root / "packages" / package).exists()
    ]
    target_package_missing = [
        f"packages/{package}"
        for package in TARGET_PRODUCT_PACKAGES
        if not (root / "packages" / package).exists()
    ]
    distribution_missing = [
        adapter
        for adapter in DISTRIBUTION_MIGRATION_HOSTS
        if not (
            (root / adapter / "README.md").exists()
            and (root / adapter / "package.json").exists()
            and (root / adapter / "bin" / "ethos.mjs").exists()
        )
    ]
    target_distribution_missing = [
        adapter for adapter in TARGET_DISTRIBUTION_ADAPTERS if not (root / adapter).exists()
    ]
    physical_target_homes_present = not target_package_missing and not target_distribution_missing
    docs_missing = [doc for doc in REQUIRED_DOCS if not (root / doc).exists()]
    docs_without_front_matter = [
        doc for doc in REQUIRED_DOCS if (root / doc).exists() and not _front_matter_ok(root / doc)
    ]
    schemas_missing = [
        schema for schema in REQUIRED_SCHEMAS if not (root / "schemas" / "ethos" / schema).exists()
    ]
    release_files = release_files_report(root)
    release_files_missing = list(release_files["missing"])
    playbooks_missing = [path for path in REQUIRED_PLAYBOOK_FILES if not (root / path).exists()]
    openspec_family_missing = [
        f"openspec/specs/{family}/spec.md"
        for family in REQUIRED_OPENSPEC_FAMILIES
        if not (root / "openspec" / "specs" / family / "spec.md").exists()
    ]
    command_report = command_registry_report(root)
    claim_report = claims_report(root)
    workspace_config = workspace_package_config_report(root)
    schema_report = schema_validation_report(root)
    evolution = evolution_report(root)
    coupling = coupling_audit_report(root)
    if openspec_mode == "shape":
        openspec = _openspec_shape_report(root)
    elif openspec_reporter is None:
        openspec = _openspec_provider_missing_report(root)
    else:
        openspec = openspec_reporter(root)
    claim_gaps = [str(gap) for gap in claim_report["required_gaps"]]
    schema_gaps = [str(gap) for gap in schema_report["required_gaps"]]
    evolution_gaps = [str(gap) for gap in evolution["required_gaps"]]
    coupling_gaps = [str(gap) for gap in coupling["required_gaps"]]
    openspec_gaps = [str(gap) for gap in openspec["required_gaps"]]
    command_gaps = [str(gap) for gap in command_report["required_gaps"]]
    workspace_config_gaps = [str(gap) for gap in workspace_config["required_gaps"]]
    playbook_report = playbooks_report(root, mode="v2-strict")
    playbook_gaps = [str(gap) for gap in playbook_report["required_gaps"]]
    gaps = (
        package_missing
        + [f"distribution_adapter_missing:{adapter}" for adapter in distribution_missing]
        + docs_missing
        + docs_without_front_matter
        + schemas_missing
        + release_files_missing
        + [f"adoption_scaffold_missing:{path}" for path in playbooks_missing]
        + [f"openspec_family_missing:{path}" for path in openspec_family_missing]
        + claim_gaps
        + schema_gaps
        + evolution_gaps
        + coupling_gaps
        + openspec_gaps
        + command_gaps
        + workspace_config_gaps
        + playbook_gaps
    )
    return {
        "ok": not gaps,
        "package_ontology": {
            "ok": not package_missing and not distribution_missing,
            "stage": "complete",
            "migration_host_packages": list(MIGRATION_HOST_PACKAGES),
            "migration_host_lifecycle": dict(MIGRATION_HOST_LIFECYCLE),
            "target_package_contract": list(TARGET_PRODUCT_PACKAGES),
            "target_distribution_contract": list(TARGET_DISTRIBUTION_ADAPTERS),
            "distribution_migration_hosts": list(DISTRIBUTION_MIGRATION_HOSTS),
            "missing": package_missing,
            "adapter_missing": distribution_missing,
        },
        "target_package_ontology": {
            "ok": not target_package_missing and not target_distribution_missing,
            "contract_ok": True,
            "physical_target_homes_present": physical_target_homes_present,
            "migration_complete": not MIGRATION_HOST_PACKAGES and not DISTRIBUTION_MIGRATION_HOSTS,
            "migration_status": "complete"
            if not MIGRATION_HOST_PACKAGES and not DISTRIBUTION_MIGRATION_HOSTS
            else "in_progress",
            "target_packages": list(TARGET_PRODUCT_PACKAGES),
            "migration_hosts": list(MIGRATION_HOST_PACKAGES),
            "target_distribution_adapters": list(TARGET_DISTRIBUTION_ADAPTERS),
            "distribution_status": dict(_PACKAGE_ONTOLOGY["migration_distributions"]),
            "distribution_migration_hosts": list(DISTRIBUTION_MIGRATION_HOSTS),
            "missing": target_package_missing,
            "adapter_missing": target_distribution_missing,
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
            "ok": release_files["ok"],
            "missing": release_files_missing,
        },
        "playbooks": {
            "ok": not playbooks_missing and bool(playbook_report["ok"]),
            "missing": playbooks_missing,
            "validation": playbook_report,
        },
        "openspec_families": {
            "ok": not openspec_family_missing,
            "expected": list(REQUIRED_OPENSPEC_FAMILIES),
            "missing": openspec_family_missing,
        },
        "command_registry": command_report,
        "workspace_config": workspace_config,
        "claims": claim_report,
        "evolution": evolution,
        "coupling": coupling,
        "openspec": openspec,
        "required_gaps": gaps,
    }

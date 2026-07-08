from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

import ethos.repository.audit_openspec as _audit_openspec
from ethos.assistants.playbooks import playbooks_report
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.audit_design import DESIGN_INTEGRITY_DOCS
from ethos.repository.audit_design import DESIGN_INTEGRITY_FORBIDDEN_ROOT_PATHS
from ethos.repository.audit_design import DESIGN_INTEGRITY_FORBIDDEN_TERMS
from ethos.repository.audit_design import DESIGN_INTEGRITY_REQUIRED_TERMS
from ethos.repository.audit_design import DESIGN_INTEGRITY_VENDOR_TERMS
from ethos.repository.audit_design import _design_integrity_report
from ethos.repository.audit_design import _front_matter_ok
from ethos.repository.audit_openspec import _active_change_violations_for_role
from ethos.repository.audit_openspec import _completed_unarchived_changes
from ethos.repository.audit_openspec import _openspec_provider_missing_report
from ethos.repository.audit_openspec import _openspec_shape_report as _openspec_shape_report_impl
from ethos.repository.context import governance_context
from ethos.repository.evidence.claims import claims_report
from ethos.repository.policy.coupling.core import coupling_audit_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.registry.authority import authority_graph_report
from ethos.repository.registry.commands import command_registry_report
from ethos.repository.release.core import REQUIRED_RELEASE_FILES as PRODUCT_RELEASE_FILES
from ethos_core.contracts.package_ontology import package_ontology_report
from ethos_core.contracts.package_ontology import workspace_package_config_report
from ethos_core.contracts.system_contracts import system_contracts_report

OpenSpecReporter = Callable[[Path], dict[str, object]]

__all__ = (
    "DESIGN_INTEGRITY_DOCS",
    "DESIGN_INTEGRITY_FORBIDDEN_ROOT_PATHS",
    "DESIGN_INTEGRITY_FORBIDDEN_TERMS",
    "DESIGN_INTEGRITY_REQUIRED_TERMS",
    "DESIGN_INTEGRITY_VENDOR_TERMS",
    "_active_change_violations_for_role",
    "_completed_unarchived_changes",
)

_PACKAGE_ONTOLOGY = package_ontology_report()
TARGET_PRODUCT_PACKAGES = tuple(
    str(item) for item in cast("list[str]", _PACKAGE_ONTOLOGY["target_packages"])
)
MIGRATION_HOST_PACKAGES = tuple(
    str(item) for item in cast("list[str]", _PACKAGE_ONTOLOGY["migration_hosts"])
)
MIGRATION_HOST_LIFECYCLE = {
    str(key): str(value)
    for key, value in cast("dict[str, str]", _PACKAGE_ONTOLOGY["migration_host_lifecycle"]).items()
}
TARGET_DISTRIBUTION_ADAPTERS = tuple(
    str(item) for item in cast("list[str]", _PACKAGE_ONTOLOGY["target_distributions"])
)
DISTRIBUTION_MIGRATION_HOSTS = tuple(
    str(item["migration_host"])
    for item in cast(
        "dict[str, dict[str, str]]", _PACKAGE_ONTOLOGY["migration_distributions"]
    ).values()
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
    "docs/governance/authority.md",
    "docs/governance/product-design-contract.md",
    "docs/governance/product-boundary-convergence.md",
    "docs/governance/capability-parity-ledger.md",
    "docs/governance/repository-profile-contract.md",
    "docs/governance/config-boundary-model.md",
    "docs/governance/adopter-boundary-and-retirement.md",
    "docs/governance/provenance-and-attestation.md",
    "docs/governance/docs-registry.md",
    "docs/governance/openspec-governance.md",
    "docs/governance/playbooks-and-skills.md",
    "docs/governance/release-governance.md",
    "docs/governance/evolution-campaign.md",
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
    "authority.schema.json",
    "authority-graph.schema.json",
    "quality-asset.schema.json",
    "quality-finding.schema.json",
    "quality-gate-plan.schema.json",
    "quality-profile.schema.json",
    "review-record.schema.json",
    "host-capability.schema.json",
)

REQUIRED_RELEASE_FILES = (
    *PRODUCT_RELEASE_FILES,
    "evolution/ledger.toml",
)

REQUIRED_PLAYBOOK_FILES = (
    ".agents/skills/README.md",
    ".agents/skills/activation.toml",
    ".agents/skills/ethos-repository-governance/SKILL.md",
)

REQUIRED_OPENSPEC_CAPABILITIES = (
    "kernel",
    "contracts",
    "repository-governance",
    "adapters",
    "command-plane",
    "assistant-projections",
    "distribution",
    "quality",
    "proof-hosts",
)


def release_files_report(root: Path) -> dict[str, object]:
    release_files_missing = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    return {
        "ok": not release_files_missing,
        "missing": release_files_missing,
    }


def _write_admission_armed_gaps(root: Path) -> list[str]:
    """Gap when the write-admission moat is NOT armed for this checkout.

    ETHOS's write-admission depends on git core.hooksPath pointing at .githooks so the
    pre-commit gate actually fires. Prior to this check the audit could report ok=True
    while the moat was unwired — a governance runtime green about its own ungated
    writes. Bind the moat to the always-run audit: an unarmed checkout is a blocking
    gap, discoverable and fixable via `ethos hook install`.
    """
    hook_script = root / ".githooks" / "pre-commit"
    if not hook_script.exists():
        # Not an ETHOS-admission repo (adopter without the hook script) — nothing to arm.
        return []
    gaps: list[str] = []
    if not (root / ".githooks" / "pre-push").exists():
        gaps.append("write_admission_not_armed:pre-push_script_missing")
    if not (root / ".githooks" / "reference-transaction").exists():
        gaps.append("write_admission_not_armed:reference-transaction_script_missing")
    completed = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    hooks_path = completed.stdout.strip() if completed.returncode == 0 else ""
    if hooks_path != ".githooks":
        gaps.append("write_admission_not_armed:core.hooksPath")
    return gaps


def repository_audit(
    root: Path,
    *,
    openspec_mode: str = "deep",
    openspec_reporter: OpenSpecReporter | None = None,
    current_head: str = "",
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
        schema
        for schema in REQUIRED_SCHEMAS
        if not (root / "system" / "schemas" / "kernel" / schema).exists()
    ]
    release_files = release_files_report(root)
    release_files_missing = list(cast("list[str]", release_files["missing"]))
    playbooks_missing = [path for path in REQUIRED_PLAYBOOK_FILES if not (root / path).exists()]
    openspec_capability_missing = [
        f"openspec/specs/{family}/spec.md"
        for family in REQUIRED_OPENSPEC_CAPABILITIES
        if not (root / "openspec" / "specs" / family / "spec.md").exists()
    ]
    command_report = command_registry_report(root)
    authority_graph = authority_graph_report(root)
    claim_report = claims_report(root, current_head=current_head)
    workspace_config = workspace_package_config_report(root)
    schema_report = schema_validation_report(root)
    evolution = evolution_report(root)
    coupling = coupling_audit_report(root)
    design_integrity = _design_integrity_report(root)
    if openspec_mode == "shape":
        openspec = _openspec_shape_report(root)
    elif openspec_reporter is None:
        openspec = _openspec_provider_missing_report(root)
    else:
        openspec = openspec_reporter(root)
    claim_gaps = [str(gap) for gap in cast("list[str]", claim_report["required_gaps"])]
    schema_gaps = [str(gap) for gap in cast("list[str]", schema_report["required_gaps"])]
    evolution_gaps = [str(gap) for gap in cast("list[str]", evolution["required_gaps"])]
    coupling_gaps = [str(gap) for gap in coupling["required_gaps"]]
    design_integrity_gaps = [
        str(gap) for gap in cast("list[str]", design_integrity["required_gaps"])
    ]
    openspec_gaps = [str(gap) for gap in cast("list[str]", openspec["required_gaps"])]
    command_gaps = [str(gap) for gap in cast("list[str]", command_report["required_gaps"])]
    authority_graph_gaps = [str(gap) for gap in cast("list[str]", authority_graph["required_gaps"])]
    workspace_config_gaps = [
        str(gap) for gap in cast("list[str]", workspace_config["required_gaps"])
    ]
    playbook_report = playbooks_report(root, mode="v2-strict")
    playbook_gaps = [str(gap) for gap in cast("list[str]", playbook_report["required_gaps"])]
    system_contracts = system_contracts_report(root)
    system_contract_gaps = [
        str(gap) for gap in cast("list[str]", system_contracts["required_gaps"])
    ]
    gaps = (
        package_missing
        + [f"distribution_adapter_missing:{adapter}" for adapter in distribution_missing]
        + docs_missing
        + docs_without_front_matter
        + schemas_missing
        + release_files_missing
        + [f"adoption_scaffold_missing:{path}" for path in playbooks_missing]
        + [f"openspec_capability_missing:{path}" for path in openspec_capability_missing]
        + claim_gaps
        + schema_gaps
        + evolution_gaps
        + coupling_gaps
        + design_integrity_gaps
        + openspec_gaps
        + command_gaps
        + authority_graph_gaps
        + workspace_config_gaps
        + playbook_gaps
        + system_contract_gaps
        + _write_admission_armed_gaps(root)
    )
    return {
        "ok": not gaps,
        "mode": "repository",
        "governance_context": governance_context(
            root,
            profile="product",
        ),
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
            "distribution_status": dict(
                cast("dict[str, dict[str, str]]", _PACKAGE_ONTOLOGY["migration_distributions"])
            ),
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
        "openspec_capabilities": {
            "ok": not openspec_capability_missing,
            "expected": list(REQUIRED_OPENSPEC_CAPABILITIES),
            "missing": openspec_capability_missing,
        },
        "command_registry": command_report,
        "authority_graph": authority_graph,
        "workspace_config": workspace_config,
        "claims": claim_report,
        "evolution": evolution,
        "coupling": coupling,
        "design_integrity": design_integrity,
        "openspec": openspec,
        "system_contracts": system_contracts,
        "required_gaps": gaps,
    }


def _openspec_shape_report(root: Path) -> dict[str, object]:
    _audit_openspec.subprocess = subprocess
    return _openspec_shape_report_impl(root)

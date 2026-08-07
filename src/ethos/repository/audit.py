from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

from ethos.assistants.playbooks import playbooks_report
from ethos.contracts.system.contracts import system_contracts_report
from ethos.contracts.verdict import observation_verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.repository.context import repository_context
from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.design.integrity import front_matter_ok
from ethos.repository.hooks import hook_runtime_binding
from ethos.repository.openspec.audit import openspec_provider_missing_report
from ethos.repository.openspec.audit import openspec_shape_report
from ethos.repository.policy.references.closure import repository_product_reference_gaps
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.release.configuration import REQUIRED_RELEASE_FILES as PRODUCT_RELEASE_FILES

OpenSpecReporter = Callable[[Path], dict[str, object]]

REQUIRED_DOCS = (
    "docs/README.md",
    "docs/reference/README.md",
    "docs/evidence/README.md",
    "docs/history/README.md",
    "docs/decisions/README.md",
    "docs/decisions/decision-index.md",
    "docs/decisions/decision-record-template.md",
    "docs/architecture/distribution.md",
    "docs/concepts/kernel-model.md",
    "docs/architecture/transition-plan.md",
    "docs/architecture/adoption-profiles.md",
    "docs/architecture/agent-projections.md",
    "docs/architecture/gate-runner.md",
    "docs/architecture/local-state.md",
    "docs/architecture/mcp-server.md",
    "docs/architecture/fleet-and-adopters.md",
    "docs/architecture/runner-and-mutation.md",
    "docs/architecture/schema-validation.md",
    "docs/governance/commit-signature-policy.md",
    "docs/governance/authority.md",
    "docs/governance/product-design-contract.md",
    "docs/governance/product-boundary-convergence.md",
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
    "commitment.schema.json",
    "attestation.schema.json",
    "facts.schema.json",
    "commit-policy.schema.json",
    "transition-plan.schema.json",
    "provenance.schema.json",
    "docs-registry.schema.json",
    "gate.schema.json",
    "assistant-projection.schema.json",
    "skill-activation.schema.json",
    "skill-registry.schema.json",
    "skill-package-manifest.schema.json",
    "lane-lease.schema.json",
    "handoff-package.schema.json",
    "handoff-acknowledgement.schema.json",
    "mutation-decision.schema.json",
    "workspace-status.schema.json",
    "quality-asset.schema.json",
    "quality-gate-plan.schema.json",
    "quality-profile.schema.json",
    "review-plan.schema.json",
    "review-result.schema.json",
    "host-capability.schema.json",
)

REQUIRED_RELEASE_FILES = PRODUCT_RELEASE_FILES

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
        "verdict": observation_verdict(ok=not release_files_missing),
        "missing": release_files_missing,
        "required_gaps": release_files_missing,
    }


def _write_admission_armed_gaps(root: Path) -> list[str]:
    """Gap when the write-admission moat is NOT armed for this checkout.

    The configured worktree-local launchers and their exact Python provenance must
    match the sole hook runtime owner. An unarmed checkout is a blocking gap,
    discoverable and repairable via ``ethos hook install``.
    """
    if not (root / ".ethos/profile.toml").is_file():
        return []
    return [str(gap) for gap in hook_runtime_binding(root)["required_gaps"]]


def repository_audit(
    root: Path,
    *,
    openspec_mode: str = "deep",
    openspec_reporter: OpenSpecReporter | None = None,
) -> dict[str, object]:
    docs_missing = [doc for doc in REQUIRED_DOCS if not (root / doc).exists()]
    docs_without_front_matter = [
        doc for doc in REQUIRED_DOCS if (root / doc).exists() and not front_matter_ok(root / doc)
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
    schema_report = schema_validation_report(root)
    reference_gaps = repository_product_reference_gaps(root)
    reference_ownership = {
        "verdict": observation_verdict(ok=not reference_gaps),
        "required_gaps": reference_gaps,
    }
    design_integrity = design_integrity_report(root)
    if openspec_mode == "shape":
        openspec = openspec_shape_report(root)
    elif openspec_reporter is None:
        openspec = openspec_provider_missing_report(root)
    else:
        openspec = openspec_reporter(root)
    schema_gaps = [str(gap) for gap in cast("list[str]", schema_report["required_gaps"])]
    design_integrity_gaps = [
        str(gap) for gap in cast("list[str]", design_integrity["required_gaps"])
    ]
    openspec_gaps = [str(gap) for gap in cast("list[str]", openspec["required_gaps"])]
    playbook_report = playbooks_report(root, mode="v2-strict")
    playbook_gaps = [str(gap) for gap in cast("list[str]", playbook_report["required_gaps"])]
    system_contracts = system_contracts_report(root)
    system_contract_gaps = [
        str(gap) for gap in cast("list[str]", system_contracts["required_gaps"])
    ]
    write_admission_gaps = _write_admission_armed_gaps(root)
    docs = {
        "verdict": observation_verdict(ok=not docs_missing and not docs_without_front_matter),
        "missing": docs_missing,
        "without_front_matter": docs_without_front_matter,
    }
    schemas = {
        "verdict": reduce_verdicts(
            observation_verdict(ok=not schemas_missing), report_verdict(schema_report)
        ),
        "missing": schemas_missing,
        "validation": schema_report,
    }
    playbooks = {
        "verdict": reduce_verdicts(
            observation_verdict(ok=not playbooks_missing), report_verdict(playbook_report)
        ),
        "missing": playbooks_missing,
        "validation": playbook_report,
    }
    openspec_capabilities = {
        "verdict": observation_verdict(ok=not openspec_capability_missing),
        "expected": list(REQUIRED_OPENSPEC_CAPABILITIES),
        "missing": openspec_capability_missing,
    }
    write_admission = {
        "verdict": observation_verdict(ok=not write_admission_gaps),
        "required_gaps": write_admission_gaps,
    }
    gaps = (
        docs_missing
        + docs_without_front_matter
        + schemas_missing
        + release_files_missing
        + [f"playbook_projection_missing:{path}" for path in playbooks_missing]
        + [f"openspec_capability_missing:{path}" for path in openspec_capability_missing]
        + schema_gaps
        + reference_gaps
        + design_integrity_gaps
        + openspec_gaps
        + playbook_gaps
        + system_contract_gaps
        + write_admission_gaps
    )
    return {
        "verdict": reduce_verdicts(
            report_verdict(docs),
            report_verdict(schemas),
            report_verdict(release_files),
            report_verdict(playbooks),
            report_verdict(openspec_capabilities),
            report_verdict(reference_ownership),
            report_verdict(design_integrity),
            report_verdict(openspec),
            report_verdict(system_contracts),
            report_verdict(write_admission),
        ),
        "mode": "repository",
        "governance_context": repository_context(root),
        "docs": docs,
        "schemas": schemas,
        "release_files": release_files,
        "playbooks": playbooks,
        "openspec_capabilities": openspec_capabilities,
        "reference_ownership": reference_ownership,
        "design_integrity": design_integrity,
        "openspec": openspec,
        "system_contracts": system_contracts,
        "write_admission": write_admission,
        "required_gaps": gaps,
    }

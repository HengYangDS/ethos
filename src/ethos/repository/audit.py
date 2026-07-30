from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from ethos.assistants.playbooks import playbooks_report
from ethos.contracts.system.contracts import system_contracts_report
from ethos.repository.context import repository_context
from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.design.integrity import front_matter_ok
from ethos.repository.openspec.audit import openspec_provider_missing_report
from ethos.repository.openspec.audit import openspec_shape_report
from ethos.repository.policy.coupling.audit import coupling_audit_report
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
    "docs/decisions/decision-dependency-map.md",
    "docs/decisions/decision-code-links.md",
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
    "docs/governance/conversation-ledger.md",
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
    "review-record.schema.json",
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
    coupling = coupling_audit_report(root)
    design_integrity = design_integrity_report(root)
    if openspec_mode == "shape":
        openspec = openspec_shape_report(root)
    elif openspec_reporter is None:
        openspec = openspec_provider_missing_report(root)
    else:
        openspec = openspec_reporter(root)
    schema_gaps = [str(gap) for gap in cast("list[str]", schema_report["required_gaps"])]
    coupling_gaps = [str(gap) for gap in coupling["required_gaps"]]
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
    gaps = (
        docs_missing
        + docs_without_front_matter
        + schemas_missing
        + release_files_missing
        + [f"playbook_projection_missing:{path}" for path in playbooks_missing]
        + [f"openspec_capability_missing:{path}" for path in openspec_capability_missing]
        + schema_gaps
        + coupling_gaps
        + design_integrity_gaps
        + openspec_gaps
        + playbook_gaps
        + system_contract_gaps
        + _write_admission_armed_gaps(root)
    )
    return {
        "ok": not gaps,
        "mode": "repository",
        "governance_context": repository_context(root),
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
        "coupling": coupling,
        "design_integrity": design_integrity,
        "openspec": openspec,
        "system_contracts": system_contracts,
        "required_gaps": gaps,
    }

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from ethos.assistants.playbooks import playbooks_report
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.context import governance_context
from ethos.repository.evidence.claims import claims_report
from ethos.repository.policy.coupling import coupling_audit_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.registry.authority import authority_graph_report
from ethos.repository.registry.commands import command_registry_report
from ethos.repository.release.core import REQUIRED_RELEASE_FILES as PRODUCT_RELEASE_FILES
from ethos_core.contracts.package_ontology import package_ontology_report
from ethos_core.contracts.package_ontology import workspace_package_config_report
from ethos_core.contracts.system_contracts import system_contracts_report

OpenSpecReporter = Callable[[Path], dict[str, object]]

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
    "docs/governance/judgment-source.md",
    "docs/governance/product-design-contract.md",
    "docs/governance/product-boundary-convergence.md",
    "docs/governance/capability-parity-ledger.md",
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
    "judgment-source.schema.json",
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
    "docs/governance/evolution-ledger.toml",
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
    "ethos-quality",
    "ethos-repository",
    "ethos-adapters",
    "ethos-test",
)


DESIGN_INTEGRITY_DOCS = (
    "docs/governance/product-design-contract.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/command-plane.md",
    "docs/architecture/runner-and-mutation.md",
)

DESIGN_INTEGRITY_REQUIRED_TERMS = {
    "docs/governance/product-design-contract.md": (
        "JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle",
        "not an external slogan",
        "single kernel",
        "truth boundary",
        "profile or adapter boundary",
        "Configuration follows separation of concerns, MECE, SSOT, and DRY",
        "OpenSpec remains mandatory governance, not a product substrate",
        "not a generic VCS abstraction",
        "status",
        "plan",
        "prove",
        "land",
        "publish",
    ),
    "docs/concepts/kernel-model.md": (
        "Root Philosophy Derivation",
        "truth and projection",
        "product semantics and adapter boundary",
        "which kernel object it projects",
    ),
    "docs/reference/command-plane.md": (
        "status",
        "plan",
        "prove",
        "land",
        "publish",
        "report",
        "adapter UI text is not product state",
    ),
    "docs/architecture/runner-and-mutation.md": (
        "target path",
        "repository root",
        "prewrite",
        "post-write audit",
        "ethos land --closeout",
        'remote_push = "not_performed"',
    ),
}

DESIGN_INTEGRITY_FORBIDDEN_TERMS = (
    "GitNexus",
    "product_self",
    "adopter_repository",
    "dual-posture",
)

DESIGN_INTEGRITY_FORBIDDEN_ROOT_PATHS = (
    "CLAUDE.md",
    ".claude",
    ".gitnexus",
)

DESIGN_INTEGRITY_VENDOR_TERMS = (
    "PyCharm",
    "Claude",
    "Codex",
    "OpenAI",
    "GPT",
    "IDE",
    "JetBrains",
    "Anthropic",
    "Gemini",
    "Copilot",
    "Cursor",
    "Windsurf",
)


def _design_integrity_report(root: Path) -> dict[str, object]:
    """Audit canonical design docs for kernel and boundary regressions.

    This is deliberately a projection over existing canonical docs, not a new
    source of product truth. It catches small design drifts where the transition
    loop, Tao/kernel constraint, configuration separation, or provider boundary
    silently disappears while lower-level tests still pass.
    """
    required_gaps: list[str] = []
    forbidden_paths = [
        f"design_integrity_forbidden_projection_path:{path}"
        for path in DESIGN_INTEGRITY_FORBIDDEN_ROOT_PATHS
        if (root / path).exists()
    ]
    required_gaps.extend(forbidden_paths)
    files: dict[str, dict[str, object]] = {}
    for doc in DESIGN_INTEGRITY_DOCS:
        path = root / doc
        if not path.exists():
            gap = f"design_integrity_doc_missing:{doc}"
            required_gaps.append(gap)
            files[doc] = {"ok": False, "missing": [gap], "forbidden": [], "vendor_terms": []}
            continue
        text = path.read_text(encoding="utf-8")
        missing = [
            f"design_integrity_anchor_missing:{doc}:{term}"
            for term in DESIGN_INTEGRITY_REQUIRED_TERMS.get(doc, ())
            if term not in text
        ]
        forbidden = [
            f"design_integrity_forbidden_term:{doc}:{term}"
            for term in DESIGN_INTEGRITY_FORBIDDEN_TERMS
            if term in text
        ]
        vendor_terms = [
            f"design_integrity_vendor_center_leak:{doc}:{term}"
            for term in DESIGN_INTEGRITY_VENDOR_TERMS
            if term in text
        ]
        doc_gaps = missing + forbidden + vendor_terms
        required_gaps.extend(doc_gaps)
        files[doc] = {
            "ok": not doc_gaps,
            "missing": missing,
            "forbidden": forbidden,
            "vendor_terms": vendor_terms,
        }
    return {
        "ok": not required_gaps,
        "scope": "canonical_product_design_docs",
        "source_of_truth": "docs plus product-design-contract anchors",
        "not_a_truth_store": True,
        "forbidden_projection_paths": forbidden_paths,
        "files": files,
        "required_gaps": required_gaps,
    }


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


def _completed_unarchived_changes(openspec_root: Path) -> list[str]:
    """Active OpenSpec changes whose tasks are all complete but which are not archived.

    Uses ETHOS's OWN signal (every task box in tasks.md checked) rather than the
    external openspec CLI, so the leak is caught on the always-run audit path — not
    only at `land --closeout` (which raw `git merge` bypasses). A completed change
    left in changes/ is a carrier masquerading as active.
    """
    changes_root = openspec_root / "changes"
    if not changes_root.exists():
        return []
    unarchived: list[str] = []
    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        tasks = change_dir / "tasks.md"
        if not tasks.exists():
            continue
        boxes = re.findall(r"- \[( |x|X)\]", tasks.read_text(encoding="utf-8"))
        if boxes and all(box.lower() == "x" for box in boxes):
            unarchived.append(f"openspec_completed_change_unarchived:{change_dir.name}")
    return unarchived


OPENSPEC_SPEC_OBLIGATION_PATTERN = re.compile(r"^\*\*(WHEN|THEN|AND)\*\*")


def _changed_openspec_spec_obligation_removal_gaps(root: Path) -> list[str]:
    """Detect accepted OpenSpec spec obligations removed in the current change.

    OpenSpec archives are projections until their deltas are fused into accepted
    specs. A tool-applied MODIFIED delta can accidentally replace a requirement
    and delete existing scenario obligations. The always-run shape audit treats
    removed WHEN/THEN/AND lines in accepted specs as a blocking small signal so
    humans/agents must either restore/fuse them or carry an explicit removal
    decision in a separate semantic change.
    """
    completed = subprocess.run(
        ["git", "diff", "--unified=0", "--", "openspec/specs/**/*.md"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        return ["openspec_spec_obligation_diff_unavailable"]
    gaps: list[str] = []
    current_file = ""
    for line in completed.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if not line.startswith("-") or line.startswith("---"):
            continue
        removed = line[1:].strip()
        if OPENSPEC_SPEC_OBLIGATION_PATTERN.match(removed):
            gaps.append(f"openspec_spec_obligation_removed:{current_file}:{removed}")
    return gaps


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


def _openspec_shape_report(root: Path) -> dict[str, object]:
    openspec_root = root / "openspec"
    required_gaps = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    if not (openspec_root / "config.yaml").exists():
        required_gaps.append("openspec_config_missing")
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")
    required_gaps.extend(_completed_unarchived_changes(openspec_root))
    required_gaps.extend(_changed_openspec_spec_obligation_removal_gaps(root))
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
    openspec_family_missing = [
        f"openspec/specs/{family}/spec.md"
        for family in REQUIRED_OPENSPEC_FAMILIES
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
        + [f"openspec_family_missing:{path}" for path in openspec_family_missing]
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
        "openspec_families": {
            "ok": not openspec_family_missing,
            "expected": list(REQUIRED_OPENSPEC_FAMILIES),
            "missing": openspec_family_missing,
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

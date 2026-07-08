"""Quality command group — determinism, gates, proof-policy, docs, and coupling.

The largest surface command group (29 commands). Binds args, calls domain/repository
reports, emits. Registers onto the shared quality_app from _base; cli.py imports this
module so the decorators run. Imports only what this group needs — so the heavy
quality/repository deps load only when this group is imported (lazy path).
"""

from __future__ import annotations

import tomllib
from typing import cast

import ethos.repository.audit as repository_audit_module
import ethos.surface.cli.results.tool as tool_results
from ethos.adapters.gates.signature import signature_policy_report
from ethos.adapters.gates.ty import ty_gate_report
from ethos.adapters.repo import git as _gitio
from ethos.assistants.projections import projection_drift_report
from ethos.domain import prove as _prove
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.evidence.freshness import evidence_freshness_report
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.coupling.core import coupling_audit_report
from ethos.repository.policy.coverage import coverage_quality_report
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos.repository.policy.docstrings.core import docstring_coverage_report
from ethos.repository.policy.gates import gate_registry
from ethos.repository.policy.layout.core import module_layout_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.registry.commands import command_registry_report
from ethos.repository.registry.docs.commands import command_examples_report
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.quality import docs_quality_report
from ethos.repository.registry.standards import standard_adapter_registry
from ethos.repository.release.attestation import release_attestation
from ethos.repository.release.attestation import sbom_projection
from ethos.repository.release.core import release_policy_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import quality_app
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.package_ontology import package_ontology_report
from ethos_core.contracts.package_ontology import workspace_package_config_report
from ethos_core.quality.docs_profile import docs_quality_profile
from ethos_core.quality.profiles import product_quality_profile
from ethos_core.quality.profiles import tool_profiles
from ethos_core.quality.proof_policy import proof_lattice
from ethos_core.result import EthosResult


@quality_app.command
def asset_policy(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report repository asset quality policy."""
    profile = product_quality_profile()
    result = EthosResult(
        command="quality asset-policy",
        ok=True,
        state="clean",
        summary={"asset_class_count": len(cast("list[object]", profile["asset_classes"]))},
        data=profile,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="types")
def quality_types(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Enforce the ty type-check policy tiers (zero-tolerance + ratchet baselines)."""
    repo = resolve_root(root)
    report = ty_gate_report(repo)
    result = EthosResult(
        command="quality types",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={"package_count": len(cast("dict[str, object]", report["packages"]))},
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command(name="docs")
def quality_docs(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report documentation quality profile, registry health, and topology."""
    repo = resolve_root(root)
    profile = docs_quality_profile()
    report = docs_quality_report(repo)
    topology = docs_topology_report(repo)
    required_gaps = tuple(cast("list[str]", report["required_gaps"])) + tuple(
        cast("list[str]", topology["required_gaps"])
    )
    ok = bool(report["ok"]) and bool(topology["ok"])
    result = EthosResult(
        command="quality docs",
        ok=ok,
        state="clean" if ok else "blocked",
        required_gaps=required_gaps,
        data={
            "profile": profile,
            "style_goals": profile["style_goals"],
            "health": report,
            "topology": topology,
        },
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="docs-topology")
def docs_topology(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit the minimal semantic documentation topology contract."""
    repo = resolve_root(root)
    report = docs_topology_report(repo)
    result = EthosResult(
        command="quality docs-topology",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(cast("dict[str, object]", report["summary"])),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=(
            (
                "restore minimal semantic docs kernel: README, decisions, evidence, "
                "history, and reference"
            )
            if report["required_gaps"]
            else (
                "ethos prove --execute --gate docs-topology --expect-head "
                "$(git rev-parse HEAD) --json"
            ),
        ),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command
def proof_policy(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report proof-state lattice and trust-bearing rules."""
    lattice = proof_lattice()
    result = EthosResult(
        command="quality proof-policy",
        ok=True,
        state="clean",
        summary={"state_count": len(cast("list[object]", lattice["states"]))},
        data=lattice,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="tool-profiles")
def tool_profiles_command(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report quality tool adapter profiles."""
    profiles = tool_profiles()
    result = EthosResult(
        command="quality tool-profiles",
        ok=True,
        state="clean",
        summary={"tool_adapter_count": len(cast("list[object]", profiles["tool_adapters"]))},
        data=profiles,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="markdown-links")
def markdown_links(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run markdown link checks through the configured adapter."""
    repo = resolve_root(root)
    files = [
        path
        for path in _gitio.git_files(repo, "*.md")
        if not path.startswith(("evidence/", "docs/archive/"))
    ]
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="markdown-links",
        tool="lychee",
        command=[
            "lychee",
            "--config",
            ".config/checks/lychee/lychee.toml",
            "--no-progress",
            *files,
        ],
        files=files,
        result_command="quality markdown-links",
        json_output=json_output,
    )


@quality_app.command(name="shell")
def shell_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run shell script lint checks through ShellCheck."""
    repo = resolve_root(root)
    files = _gitio.git_files(repo, "*.sh")
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="shell-lint",
        tool="bash",
        command=["bash", ".config/ci/scripts/run-shell-lint.sh", *files],
        files=files,
        result_command="quality shell",
        json_output=json_output,
    )


@quality_app.command(name="toml")
def toml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run TOML syntax and format checks through Taplo."""
    repo = resolve_root(root)
    files = _gitio.git_files(repo, "*.toml")
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="toml-config",
        tool="bash",
        command=["bash", ".config/ci/scripts/run-config-lint.sh", *files],
        files=files,
        result_command="quality toml",
        json_output=json_output,
    )


@quality_app.command(name="yaml")
def yaml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run YAML projection checks through yamllint."""
    repo = resolve_root(root)
    files = _gitio.git_files(repo, "*.yml", "*.yaml")
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="yaml-config",
        tool="bash",
        command=["bash", ".config/ci/scripts/run-config-lint.sh", *files],
        files=files,
        result_command="quality yaml",
        json_output=json_output,
    )


@quality_app.command(name="coverage")
def coverage(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report Python coverage policy and latest artifact state."""
    repo = resolve_root(root)
    report = coverage_quality_report(repo)
    result = EthosResult(
        command="quality coverage",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "current_hard_floor": cast("dict[str, object]", report["policy"]).get(
                "current_hard_floor"
            ),
            "latest_line_percent": cast("dict[str, object]", report["latest_artifact"]).get(
                "line_percent"
            ),
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command(name="docstrings")
def docstrings(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report public product-surface docstring coverage."""
    repo = resolve_root(root)
    report = docstring_coverage_report(repo)
    result = EthosResult(
        command="quality docstrings",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "coverage_percent": report["coverage_percent"],
            "documented_count": report["documented_count"],
            "public_count": report["public_count"],
            "style_issue_count": report.get("style_issue_count", 0),
            "advisory_missing_count": cast(
                "dict[str, object]",
                report.get("advisory_public_definition_inventory", {"missing_count": 0}),
            )["missing_count"],
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command(name="code-size")
def code_size(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check effective source-file size against ratchet limits."""
    repo = resolve_root(root)
    report = _prove.code_size_report(repo)
    result = EthosResult(
        command="quality code-size",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="module-layout")
def module_layout(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check semantic subpackage and import-layout discipline."""
    repo = resolve_root(root)
    report = module_layout_report(repo)
    result = EthosResult(
        command="quality module-layout",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=cast("dict[str, object]", report["summary"]),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command(name="npm")
def npm_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run npm distribution pack smoke checks without publishing."""
    repo = resolve_root(root)
    files = ["package.json"] if (repo / "package.json").exists() else []
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="npm-pack",
        tool="npm",
        command=["npm", "run", "test:npm"],
        files=files,
        result_command="quality npm",
        json_output=json_output,
    )


@quality_app.command(name="generated-artifacts")
def generated_artifacts(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit generated-artifact topology and path routing drift."""
    repo = resolve_root(root)
    report = generated_artifact_topology_report(repo)
    result = EthosResult(
        command="quality generated-artifacts",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(cast("dict[str, object]", report["summary"])),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=(
            (
                "move generated outputs under build/ethos or build/evidence; "
                "promote curated summaries into docs/evidence"
            )
            if report["required_gaps"]
            else "ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
        ),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command
def command_surface(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command surface vocabulary."""
    repo = resolve_root(root)
    report = command_registry_report(repo)
    result = EthosResult(
        command="quality command-surface",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def format_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report format-policy readiness."""
    repo = resolve_root(root)
    policy_path = repo / ".ethos" / "rules.toml"
    if policy_path.exists():
        policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
        gaps: tuple[str, ...] = ()
    else:
        policy = {}
        gaps = ("format_policy_missing:.ethos/rules.toml",)
    result = EthosResult(
        command="quality format-policy",
        ok=not gaps,
        state="clean" if not gaps else "blocked",
        required_gaps=gaps,
        data={
            "source": ".ethos/rules.toml",
            "formats": policy.get("formats", {}),
            "artifacts": policy.get("artifacts", {}),
            "determinism": policy.get("determinism", {}),
            "standards": policy.get("standards", {}),
        },
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def projection_drift(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report projection drift readiness."""
    repo = resolve_root(root)
    report = projection_drift_report(repo)
    result = EthosResult(
        command="quality projection-drift",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def standards(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report standards and framework adapter registry."""
    registry = standard_adapter_registry()
    result = EthosResult(
        command="quality standards",
        ok=True,
        state="clean",
        data={"adapters": registry},
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="package-ontology")
def package_ontology(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report target package ontology and migration-host state."""
    repo = resolve_root(root)
    contract = package_ontology_report()
    target_packages = cast("list[str]", contract["target_packages"])
    migration_hosts = cast("list[str]", contract["migration_hosts"])
    target_distributions = cast("list[str]", contract["target_distributions"])
    migration_distributions = cast("dict[str, object]", contract["migration_distributions"])
    target_missing = [
        f"packages/{package}"
        for package in target_packages
        if not (repo / "packages" / str(package)).exists()
    ]
    host_missing = [
        f"packages/{package}"
        for package in migration_hosts
        if not (repo / "packages" / str(package)).exists()
    ]
    distribution_missing = [
        distribution
        for distribution in target_distributions
        if not (repo / str(distribution)).exists()
    ]
    workspace_config = workspace_package_config_report(repo)
    workspace_config_gaps = [
        str(gap) for gap in cast("list[str]", workspace_config["required_gaps"])
    ]
    migration_complete = not migration_hosts and all(
        item.get("state") == "migrated"
        for item in migration_distributions.values()
        if isinstance(item, dict)
    )
    physical_missing = target_missing + host_missing + distribution_missing
    data = {
        **contract,
        "physical_target_homes_present": not target_missing and not distribution_missing,
        "migration_complete": migration_complete,
        "migration_status": "complete" if migration_complete else "in_progress",
        "missing": physical_missing + workspace_config_gaps,
        "distribution_status": migration_distributions,
        "workspace_config": workspace_config,
    }
    result = EthosResult(
        command="quality package-ontology",
        ok=not data["missing"],
        state="tracked" if not data["missing"] else "gapped",
        summary={
            "target_package_count": len(target_packages),
            "migration_host_count": len(migration_hosts),
            "migration_status": data["migration_status"],
        },
        required_gaps=tuple(
            [f"package_ontology_missing:{item}" for item in physical_missing]
            + workspace_config_gaps
        ),
        next_actions=("ethos repository audit",),
        data=data,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def schemas(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate ETHOS JSON Schemas."""
    repo = resolve_root(root)
    report = schema_validation_report(repo)
    result = EthosResult(
        command="quality schemas",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def gates(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report executable proof gate registry."""
    registry = gate_registry()
    result = EthosResult(
        command="quality gates",
        ok=True,
        state="ready",
        summary={"gate_count": len(registry)},
        data={
            "gates": {
                gate_id: {
                    "kind": gate.kind,
                    "command": list(gate.command),
                    "policy": gate.policy,
                    "profile": gate.profile,
                    "toolchain": gate.toolchain,
                    "asset_classes": list(gate.asset_classes),
                    "dimensions": list(gate.dimensions),
                    "execution_mode": gate.execution_mode,
                    "evidence_class": gate.evidence_class,
                    "trust_bearing": gate.trust_bearing,
                    "tool_adapter": gate.tool_adapter,
                    "writes_files": gate.writes_files,
                    "network_policy": gate.network_policy,
                    "version_source": gate.version_source,
                    "depends_on": list(gate.depends_on),
                }
                for gate_id, gate in registry.items()
            }
        },
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="coupling-audit")
def coupling_audit(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report product, profile, adapter, and product-toolchain coupling boundaries."""
    repo = resolve_root(root)
    report = coupling_audit_report(repo)
    validation = _prove.command_data_validation(
        repo,
        schema_name="coupling-audit.schema.json",
        payload=report,
    )
    validation_gaps = tuple(
        f"coupling_audit_schema:{gap}" for gap in cast("list[str]", validation["required_gaps"])
    )
    ok = bool(report["ok"]) and bool(validation["ok"])
    result = EthosResult(
        command="quality coupling-audit",
        ok=ok,
        state="clean" if ok else "blocked",
        diagnostics=(validation,),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])) + validation_gaps,
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def commits(
    *,
    enforce_head: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report commit naming and signature policy."""
    repo = resolve_root(root)
    report = signature_policy_report(repo)
    gaps = list(cast("list[str]", report["required_gaps"]))
    if enforce_head and not report["head_subject_ok"]:
        gaps.append("head_subject_not_conventional")
    if enforce_head and not report["head_signature_ok"]:
        gaps.append("head_signature_not_good")
    result = EthosResult(
        command="quality commits",
        ok=not gaps,
        state="clean" if not gaps else "blocked",
        required_gaps=tuple(gaps),
        data={**report, "enforce_head": enforce_head},
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def release(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report product release surface and host-profile readiness."""
    repo = resolve_root(root)
    release_files = repository_audit_module.release_files_report(repo)
    policy = release_policy_report(repo)
    result = EthosResult(
        command="quality release",
        ok=bool(release_files["ok"]),
        state="ready" if release_files["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", release_files["missing"])),
        next_actions=("uv build --all-packages",),
        data={
            "release_files": release_files,
            "host_profile": policy["host_profile"],
        },
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def release_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate release version, host profile, protection, and attestation policy."""
    repo = resolve_root(root)
    report = release_policy_report(repo)
    result = EthosResult(
        command="quality release-policy",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos quality release-attestation",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def sbom(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit an SPDX-lite SBOM projection from workspace metadata."""
    repo = resolve_root(root)
    projection = sbom_projection(repo)
    result = EthosResult(
        command="quality sbom",
        ok=True,
        state="ready",
        summary={"package_count": len(projection["packages"])},
        data={"sbom": projection},
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command(name="release-attestation")
def release_attestation_command(
    *,
    evidence_digest: str = "planned",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit release attestation envelope without publishing it."""
    repo = resolve_root(root)
    attestation = release_attestation(
        root=repo,
        head=_gitio.current_head(repo),
        evidence_digest=evidence_digest,
    )
    result = EthosResult(
        command="quality release-attestation",
        ok=True,
        state="ready",
        summary={"tag": attestation["predicate"]["tag"]},
        data={"attestation": attestation},
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def command_registry(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command registry."""
    repo = resolve_root(root)
    report = command_registry_report(repo)
    result = EthosResult(
        command="quality command-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos repository audit",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def evidence_freshness(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check declared evidence roots and claim digests."""
    repo = resolve_root(root)
    report = evidence_freshness_report(repo)
    result = EthosResult(
        command="quality evidence-freshness",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        summary=cast("dict[str, object]", report["summary"]),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos prove --json",),
        data=cast("dict[str, object]", report["data"]),
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def claims(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate claim evidence digests."""
    repo = resolve_root(root)
    report = claims_report(repo)
    result = EthosResult(
        command="quality claims",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos prove --json",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def docs_registry(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate documentation metadata registry."""
    repo = resolve_root(root)
    report = docs_health_report(repo)
    result = EthosResult(
        command="quality docs-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos docs",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def command_examples(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate documented command examples."""
    repo = resolve_root(root)
    report = command_examples_report(repo)
    result = EthosResult(
        command="quality command-examples",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@quality_app.command
def provenance(
    *,
    objective: str = "ethos provenance",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a provenance envelope for a planned ETHOS proof."""
    repo = resolve_root(root)
    run = ProofRun(
        action_id="planned-proof",
        command=("ethos", "prove", "--json"),
        exit_code=None,
        stdout="",
        stderr="",
        state="planned",
    )
    evidence = EvidenceSet.from_runs(
        id=f"ethos:{objective}",
        head=_gitio.current_head(repo),
        runs=(run,),
        durability="local",
    )
    result = EthosResult(
        command="quality provenance",
        ok=True,
        state="ready",
        summary={"evidence_digest": evidence.digest},
        next_actions=("ethos prove --json",),
        data={"evidence": evidence.to_dict(), "provenance": provenance_envelope(evidence)},
    )
    emit(result, json_output=json_output, enforce=False)
